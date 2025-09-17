"""
Simple retriever using sentence-transformers + FAISS for local RAG prototype.

Features:
- index_csv(path, nsplits=..., id_field=None) -> builds index from CSV and saves index and metadata
- load_index() -> loads index and metadata
- search(query, k=5) -> returns top-k (score, text, meta)

Index files (in repo working dir): .data/faiss_index.bin, .data/embeddings.npy, .data/metadata.json
"""
from pathlib import Path
import json
import os
import numpy as np
import pandas as pd

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE.parent / '.data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL_NAME = os.environ.get('SENTENCE_MODEL', 'all-MiniLM-L6-v2')
EMBED_DIM = 384  # default for all-MiniLM-L6-v2

INDEX_PATH = DATA_DIR / 'faiss_index.bin'
META_PATH = DATA_DIR / 'metadata.json'
EMB_PATH = DATA_DIR / 'embeddings.npy'

_model = None
_index = None
_metadata = None
_embeddings = None


def _ensure_model():
    global _model
    if _model is None:
        if SentenceTransformer is None:
            raise RuntimeError('sentence-transformers not installed')
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def _save_index(index, embeddings, metadata):
    if faiss is None:
        raise RuntimeError('faiss not available')
    faiss.write_index(index, str(INDEX_PATH))
    np.save(str(EMB_PATH), embeddings)
    with open(META_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False)


def _load_index():
    global _index, _metadata, _embeddings
    if _index is not None:
        return _index, _embeddings, _metadata
    if not INDEX_PATH.exists() or not META_PATH.exists() or not EMB_PATH.exists():
        return None, None, None
    if faiss is None:
        raise RuntimeError('faiss not available')
    _index = faiss.read_index(str(INDEX_PATH))
    _embeddings = np.load(str(EMB_PATH))
    with open(META_PATH, 'r', encoding='utf-8') as f:
        _metadata = json.load(f)
    return _index, _embeddings, _metadata


def _text_from_row(row, id_field=None):
    # Convert a pandas Series to a single string; prefer id_field as label
    pieces = []
    for k, v in row.items():
        pieces.append(f"{k}: {v}")
    return "\n".join(pieces)


def index_csv(path: str, text_fields=None, chunk_size=500, overlap=50, id_field=None):
    """
    Index a CSV file. `text_fields` is a list of column names to pull text from (defaults to all).
    The function will create text chunks from the chosen fields and build a FAISS index.
    Returns number of chunks indexed.
    """
    model = _ensure_model()
    df = pd.read_csv(path)
    records = []
    for idx, row in df.iterrows():
        if text_fields:
            texts = [str(row.get(f, '')) for f in text_fields]
        else:
            # use all string-cast fields
            texts = [str(v) for v in row.values]
        joined = " \n ".join([t for t in texts if t and t.strip()])
        if not joined:
            continue
        # naive chunking by characters
        L = len(joined)
        start = 0
        while start < L:
            end = start + chunk_size
            chunk = joined[start:end]
            records.append({'text': chunk, 'source_row': int(idx) if id_field is None else row.get(id_field)})
            start = end - overlap
    if not records:
        return 0
    texts = [r['text'] for r in records]
    embeddings = model.encode(texts, show_progress_bar=True)
    embeddings = np.array(embeddings).astype('float32')
    dim = embeddings.shape[1]
    if faiss is None:
        raise RuntimeError('faiss not installed')
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)
    metadata = records
    _save_index(index, embeddings, metadata)
    return len(records)


def search(query: str, k: int = 5):
    """Search the saved index for the query and return list of (score, text, meta)
    """
    model = _ensure_model()
    index, embeddings, metadata = _load_index()
    if index is None:
        return []
    q_emb = model.encode([query]).astype('float32')
    D, I = index.search(q_emb, k)
    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < 0:
            continue
        meta = metadata[idx]
        results.append({'score': float(dist), 'text': meta['text'], 'meta': meta})
    return results


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('csv')
    p.add_argument('--fields', nargs='*')
    args = p.parse_args()
    n = index_csv(args.csv, text_fields=args.fields)
    print('Indexed', n, 'chunks')
