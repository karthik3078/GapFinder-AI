"""Bounded PDF/TXT extraction with stable source provenance. No LLM calls."""
import hashlib
import re
from pathlib import Path

import pymupdf
from sqlalchemy import select

from .database import Chunk, Document, uid
from .security import suspicious


def extract_pages(data: bytes, filename: str):
    suffix = Path(filename).suffix.lower()
    if suffix == '.txt':
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('Text files must use UTF-8 encoding.') from exc
        if '\x00' in text:
            raise ValueError('This does not look like a text file.')
        pages = text.split('\f')
    elif suffix == '.pdf':
        try:
            with pymupdf.open(stream=data, filetype='pdf') as doc:
                if doc.needs_pass:
                    raise ValueError('Password-protected PDFs are not supported.')
                if len(doc) > 100:
                    raise ValueError('Use a PDF with at most 100 pages.')
                pages = [page.get_text('text', sort=True) for page in doc]
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('The PDF could not be read.') from exc
    else:
        raise ValueError('Upload a .pdf or .txt file.')
    if len(pages) > 100 or sum(map(len, pages)) > 400_000:
        raise ValueError('Use at most 100 pages and 400,000 extracted characters.')
    if not any(p.strip() for p in pages):
        raise ValueError('No readable text found. Scanned PDFs need OCR before upload.')
    return pages


def chunk_pages(pages):
    chunks = []
    for page, text in enumerate(pages, 1):
        # Split on explicit headings to avoid mixing adjacent syllabus topics.
        blocks = re.split(r'(?m)(?=^#{1,4}\s+)', text.replace('\r\n', '\n'))
        section = 'Page ' + str(page)
        for block in blocks:
            if not block.strip():
                continue
            lines = block.strip().splitlines()
            if lines[0].startswith('#'):
                section = lines[0].lstrip('#').strip()[:160]
            for start in range(0, len(block), 600):
                part = block[start:start + 700].strip()
                if part:
                    chunks.append({'page': page, 'section': section, 'text': part, 'quarantined': suspicious(part)})
                if start + 700 >= len(block):
                    break
    return chunks


def citation(chunk, quote=None):
    return {'chunk_id': chunk.id, 'document_id': chunk.document_id, 'filename': chunk.filename,
            'page': chunk.page, 'section': chunk.section, 'quote': quote or chunk.text[:300]}


def ingest(db, vectors, settings, user_id, course_id, filename, kind, data):
    # Client filenames are labels only. Stored files always use a generated ID.
    filename = Path(filename.replace('\\', '/')).name[:160]
    if kind not in ('syllabus', 'material', 'past_paper'):
        raise ValueError('Choose syllabus, material, or past_paper.')
    if not data or len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f'Files must be nonempty and no larger than {settings.max_upload_mb} MB.')
    digest = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.course_id == course_id, Document.kind == kind, Document.sha256 == digest))
    if existing:
        return existing, True
    pages = extract_pages(data, filename)
    pieces = chunk_pages(pages)
    doc = Document(id=uid(), user_id=user_id, course_id=course_id, filename=filename, kind=kind,
                   sha256=digest, pages=len(pages), warnings=[])
    quarantined = sum(p['quarantined'] for p in pieces)
    warnings = []
    if quarantined:
        warnings.append(f'{quarantined} suspicious chunks quarantined and excluded from AI context.')
    if any(not p.strip() for p in pages):
        warnings.append('Some pages contain no text; scanned content was not OCR processed.')
    doc.warnings = warnings
    chunks = [Chunk(id=uid(), document_id=doc.id, user_id=user_id, course_id=course_id,
                    kind=kind, filename=filename, ordinal=i, **p) for i, p in enumerate(pieces)]
    raw_path = settings.storage_dir / 'uploads' / (doc.id + Path(filename).suffix.lower())
    try:
        db.add(doc)
        db.flush()
        db.add_all(chunks)
        db.flush()
        vectors.index_chunks(user_id, course_id, chunks)
        raw_path.write_bytes(data)
        db.commit()
    except Exception:
        db.rollback()
        vectors.remove(user_id, course_id, [c.id for c in chunks])
        raw_path.unlink(missing_ok=True)
        raise
    return doc, False
