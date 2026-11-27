"""Offline maintenance command. Stop the server before changing embeddings."""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from .config import Settings
from .database import Chunk, Course, open_database
from .retrieval import VectorStore
from .topics import leaf_topics


def rebuild(stage):
    settings = Settings()
    engine, sessions = open_database(settings.storage_dir / 'gapfinder.db')
    vectors = VectorStore(settings.model_copy(update={'storage_dir': stage}))
    with sessions() as db:
        for course in db.scalars(select(Course)):
            chunks = list(db.scalars(select(Chunk).where(Chunk.course_id == course.id, Chunk.user_id == course.user_id)))
            vectors.index_chunks(course.user_id, course.id, chunks)
            vectors.index_topics(course.user_id, course.id, leaf_topics(db, course.id))
    vectors.close()
    engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-stage', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    settings = Settings()
    root = settings.storage_dir.resolve()
    if args.build_stage:
        stage = args.build_stage.resolve()
        if stage.parent != root or not stage.name.startswith('reindex-'):
            raise SystemExit('Reindex stage must be inside the configured storage directory.')
        rebuild(stage)
        return
    if not (root / 'gapfinder.db').exists():
        raise SystemExit('Start the app once before reindexing.')
    stage = root / ('reindex-' + uuid4().hex)
    stage.mkdir()
    # Child process releases all Chroma file handles before the directory swap.
    subprocess.run([sys.executable, '-m', 'backend.reindex', '--build-stage', str(stage)], check=True)
    backup = root / ('index-backup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:6])
    backup.mkdir()
    for name in ('chroma_db', 'embedding-config.json'):
        old = root / name
        if old.exists():
            old.rename(backup / name)
        (stage / name).rename(root / name)
    stage.rmdir()
    print(f'Rebuilt the index. Previous index retained at {backup}. Restart the server.')


if __name__ == '__main__':
    main()
