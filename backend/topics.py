"""Syllabus hierarchy and retrieval-based, reviewable exam weightage."""
import re

from sqlalchemy import delete, select

from .database import Chunk, PaperQuestion, Topic, uid
from .generation import EvidenceError, validate_citations
from .ingestion import citation


def source_blocks(db, user_id, course_id, kind):
    return [{**citation(c), 'text': c.text} for c in db.scalars(select(Chunk).where(
        Chunk.user_id == user_id, Chunk.course_id == course_id, Chunk.kind == kind,
        Chunk.quarantined.is_(False)).order_by(Chunk.document_id, Chunk.ordinal))]


def leaf_topics(db, course_id):
    topics = list(db.scalars(select(Topic).where(Topic.course_id == course_id).order_by(Topic.path)))
    parents = {t.parent_id for t in topics if t.parent_id}
    return [t for t in topics if t.id not in parents]


def build_topics(db, generator, vectors, user_id, course_id):
    blocks = source_blocks(db, user_id, course_id, 'syllabus')
    if not blocks:
        raise EvidenceError('Upload a readable syllabus first.')
    if len(blocks) > 80:
        raise EvidenceError('Use a concise syllabus (at most 80 chunks) for topic extraction.')
    nodes = []
    if generator.client:
        for start in range(0, len(blocks), 15):
            subset = blocks[start:start + 15]
            batch = generator.topics(subset)
            for node in batch.topics:
                nodes.append({'name': node.name, 'parent': node.parent, 'citations': validate_citations(node.citations, subset)})
    else:
        # Markdown headings / numbered outline. Ordinary lines become roots.
        stack = {}
        seen = set()
        for block in blocks:
            for line in block['text'].splitlines():
                line = line.strip()
                if not line:
                    continue
                heading = re.match(r'^(#{1,4})\s+(.+)$', line)
                numbered = re.match(r'^(\d+(?:\.\d+)*)(?:[.)])?\s+(.+)$', line)
                if heading:
                    level, name = len(heading[1]), heading[2]
                elif numbered:
                    level, name = numbered[1].count('.') + 1, numbered[2]
                elif not any(b['text'].lstrip().startswith('#') for b in blocks):
                    level, name = 1, line.lstrip('-* ').split(':')[0][:160]
                else:
                    continue
                parent = stack.get(level - 1)
                stack = {k: v for k, v in stack.items() if k < level}
                stack[level] = name
                if (parent, name) in seen or len(name) < 2:
                    continue
                seen.add((parent, name))
                # Short headings use their whole block to satisfy quote length.
                quote = line if len(line) >= 8 else block['text'][:200]
                nodes.append({'name': name, 'parent': parent, 'citations': validate_citations([{'chunk_id': block['chunk_id'], 'quote': quote}], [block])})
    if not nodes:
        raise EvidenceError('No topics found. In offline mode use # Unit and ## Topic headings or a numbered outline.')
    if len(nodes) > 100:
        raise EvidenceError('Use a syllabus with at most 100 topics.')
    existing = list(db.scalars(select(Topic).where(Topic.course_id == course_id)))
    by_path = {t.path: t for t in existing}
    by_name = {t.name: t for t in existing}
    # Append/update, preserving IDs and historical assessments on refresh.
    for node in nodes:
        parent = by_name.get(node['parent']) if node['parent'] else None
        if node['parent'] and not parent:
            raise EvidenceError('A generated topic references a missing parent. Please clarify the syllabus hierarchy.')
        path = parent.path + ' / ' + node['name'] if parent else node['name']
        topic = by_path.get(path)
        if not topic:
            topic = Topic(id=uid(), course_id=course_id, parent_id=parent.id if parent else None, name=node['name'], path=path)
            db.add(topic)
            db.flush()
            by_path[path] = topic
        topic.citations = node['citations']
        by_name[node['name']] = topic
    db.flush()
    vectors.index_topics(user_id, course_id, leaf_topics(db, course_id))
    recalculate_weights(db, course_id)
    db.commit()
    return list(by_path.values())


def extract_papers(generator, blocks):
    questions = []
    if generator.client:
        for start in range(0, len(blocks), 10):
            subset = blocks[start:start + 10]
            batch = generator.paper(subset)
            for q in batch.questions:
                questions.append({'text': q.text, 'marks': q.marks, 'citation': validate_citations([q.citation], subset)[0]})
    else:
        for block in blocks:
            for match in re.finditer(r'(?m)^\s*(?:Q\s*)?\d+[.)]\s+(.+?)(?=\n\s*(?:Q\s*)?\d+[.)]\s|\Z)', block['text'], re.S):
                text = match[1].strip()
                marks = re.search(r'\[(\d+(?:\.\d+)?)\s*marks?\]', text, re.I)
                questions.append({'text': text, 'marks': float(marks[1]) if marks else 1,
                    'citation': validate_citations([{'chunk_id': block['chunk_id'], 'quote': match[0].strip()[:650]}], [block])[0]})
    seen = set()
    unique = []
    for item in questions:
        key = (item['citation']['document_id'], re.sub(r'\s+', ' ', item['text']).casefold())
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def map_papers(db, generator, vectors, user_id, course_id):
    topics = leaf_topics(db, course_id)
    if not topics:
        raise EvidenceError('Build a topic map first.')
    blocks = source_blocks(db, user_id, course_id, 'past_paper')
    if len(blocks) > 150:
        raise EvidenceError('Map a smaller paper set (at most 150 chunks).')
    extracted = extract_papers(generator, blocks)
    if not extracted:
        raise EvidenceError('No exam questions found. In offline mode use numbered questions and optional [5 marks].')
    allowed = {t.id for t in topics}
    records = []
    for question in extracted:
        hits = vectors.search(user_id, course_id, question['text'], kind='topic', limit=2)
        confidence = hits[0][1] if hits else 0
        topic_id = hits[0][2].get('topic_id') if hits else None
        margin = confidence - hits[1][1] if len(hits) > 1 else confidence
        needs_review = confidence < vectors.settings.mapping_min_confidence or margin < 0.04 or topic_id not in allowed
        records.append(PaperQuestion(course_id=course_id, text=question['text'], marks=question['marks'],
            citation=question['citation'], topic_id=topic_id if topic_id in allowed else None,
            confidence=round(confidence, 4), review_needed=needs_review))
    db.execute(delete(PaperQuestion).where(PaperQuestion.course_id == course_id))
    db.add_all(records)
    db.flush()
    recalculate_weights(db, course_id)
    db.commit()
    return records


def recalculate_weights(db, course_id):
    leaves = leaf_topics(db, course_id)
    topics = list(db.scalars(select(Topic).where(Topic.course_id == course_id)))
    papers = list(db.scalars(select(PaperQuestion).where(PaperQuestion.course_id == course_id, PaperQuestion.review_needed.is_(False))))
    total = sum(p.marks for p in papers) + len(leaves)  # Laplace smoothing.
    for topic in topics:
        relevant = [p for p in papers if p.topic_id == topic.id]
        topic.frequency = len(relevant)
        topic.marks = sum(p.marks for p in relevant)
        topic.weight = (topic.marks + 1) / max(1, total) if topic in leaves else 0
    # Parent displays are roll-ups; only leaves are assessed/planned.
    for topic in sorted(topics, key=lambda t: t.path.count('/'), reverse=True):
        if topic.parent_id:
            parent = next(t for t in topics if t.id == topic.parent_id)
            parent.frequency += topic.frequency
            parent.marks += topic.marks
            parent.weight += topic.weight
