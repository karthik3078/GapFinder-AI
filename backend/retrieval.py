"""Stage A: embeddings, tenant-scoped search, SQL revalidation. No generation."""
import hashlib
import json
import math
import re

import chromadb
from chromadb.config import Settings as ChromaSettings
from google import genai
from google.genai import types
from sqlalchemy import select

from .database import Chunk
from .ingestion import citation

STOP = set('the a an of to for in on is are and or with what how why explain describe does from this that only according notes'.split())


def words(text):
    return [w for w in re.findall(r'[a-z0-9]+', text.lower()) if len(w) > 2 and w not in STOP]


def local_embedding(text, dimensions):
    # Transparent lexical hashing baseline, NOT a semantic embedding model.
    vec = [0.0] * dimensions
    tokens = words(text)
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], 'big') % dimensions
        vec[index] += 1 if digest[4] % 2 else -1
    norm = math.sqrt(sum(v * v for v in vec)) or 1
    return [v / norm for v in vec]


class VectorStore:
    def __init__(self, settings):
        self.settings = settings
        config = {'provider': settings.embedding_provider, 'model': settings.embedding_model if settings.embedding_provider == 'google' else 'lexical-sha256-v1',
                  'dimensions': settings.embedding_dimensions}
        manifest = settings.storage_dir / 'embedding-config.json'
        if manifest.exists() and json.loads(manifest.read_text()) != config:
            raise RuntimeError('Embedding settings changed. Run python -m backend.reindex before starting the app.')
        manifest.write_text(json.dumps(config, indent=2))
        self.client = chromadb.PersistentClient(path=str(settings.storage_dir / 'chroma_db'), settings=ChromaSettings(anonymized_telemetry=False))
        self.google = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=settings.model_timeout_seconds * 1000)) if settings.embedding_provider == 'google' else None

    def embed(self, texts, query=False):
        if not self.google:
            return [local_embedding(t, self.settings.embedding_dimensions) for t in texts]
        output = []
        for offset in range(0, len(texts), 32):
            response = self.google.models.embed_content(model=self.settings.embedding_model, contents=texts[offset:offset + 32],
                config=types.EmbedContentConfig(task_type='RETRIEVAL_QUERY' if query else 'RETRIEVAL_DOCUMENT', output_dimensionality=self.settings.embedding_dimensions))
            for embedding in response.embeddings or []:
                values = embedding.values
                if values is None or len(values) != self.settings.embedding_dimensions or not all(math.isfinite(v) for v in values):
                    raise ValueError('Embedding response has invalid dimensions or values.')
                norm = math.sqrt(sum(v * v for v in values)) or 1
                output.append([v / norm for v in values])
        if len(output) != len(texts):
            raise ValueError('Incomplete embedding response.')
        return output

    def collection(self, user_id, course_id):
        name = 'gf-' + hashlib.sha256(f'{user_id}:{course_id}'.encode()).hexdigest()[:40]
        return self.client.get_or_create_collection(name, embedding_function=None, configuration={'hnsw': {'space': 'cosine'}})

    def index_chunks(self, user_id, course_id, chunks):
        rows = [c for c in chunks if not c.quarantined]
        col = self.collection(user_id, course_id)
        for offset in range(0, len(rows), 64):
            batch = rows[offset:offset + 64]
            texts = [c.section + '\n' + c.text for c in batch]
            col.upsert(ids=[c.id for c in batch], embeddings=self.embed(texts), documents=[c.text for c in batch],
                metadatas=[{'user_id': user_id, 'course_id': course_id, 'kind': c.kind, 'document_id': c.document_id} for c in batch])

    def index_topics(self, user_id, course_id, topics):
        col = self.collection(user_id, course_id)
        col.delete(where={'kind': 'topic'})
        if topics:
            col.upsert(ids=['topic-' + t.id for t in topics], embeddings=self.embed([t.path for t in topics]), documents=[t.path for t in topics],
                metadatas=[{'user_id': user_id, 'course_id': course_id, 'kind': 'topic', 'topic_id': t.id} for t in topics])

    def remove(self, user_id, course_id, ids):
        if ids:
            self.collection(user_id, course_id).delete(ids=ids)

    def search(self, user_id, course_id, query, kind='material', limit=5):
        col = self.collection(user_id, course_id)
        if not col.count():
            return []
        result = col.query(query_embeddings=self.embed([query], query=True), n_results=min(limit, col.count()),
            where={'$and': [{'user_id': user_id}, {'course_id': course_id}, {'kind': kind}]}, include=['distances', 'metadatas'])
        return [(i, max(0, min(1, 1 - float(d))), m) for i, d, m in zip(result['ids'][0], result['distances'][0], result['metadatas'][0])]

    def retrieve(self, db, user_id, course_id, query, limit=5):
        blocks = []
        for chunk_id, similarity, _ in self.search(user_id, course_id, query, limit=limit):
            if similarity < self.settings.retrieval_min_similarity:
                continue
            # Never trust vector metadata alone; fail closed against the relational owner.
            chunk = db.scalar(select(Chunk).where(Chunk.id == chunk_id, Chunk.user_id == user_id,
                Chunk.course_id == course_id, Chunk.kind == 'material', Chunk.quarantined.is_(False)))
            if chunk:
                blocks.append({**citation(chunk), 'text': chunk.text, 'similarity': round(similarity, 4)})
        return blocks

    def close(self):
        if self.google:
            self.google.close()
