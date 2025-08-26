import os
import re
import sys
import chromadb
from chromadb.utils import embedding_functions


# Ingest a markdown policy file into Chroma
# Usage: python storage/chroma_ingest.py path/to/airlines_policy.md

def ingest_markdown(md_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    # naive chunking by H2 sections; adjust as needed
    chunks = re.split(r"(?=\n##\s)", text)
    docs = [c.strip() for c in chunks if c.strip()]

    client = chromadb.PersistentClient(path=os.getenv("CHROMA_DIR", ".chroma"))
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    col = client.get_or_create_collection("policy", embedding_function=emb)

    try:
        col.delete(where={"source": "airlines_policy"})
    except Exception:
        # first run or nothing to delete
        pass

    col.add(
        documents=docs,
        metadatas=[{"source": "airlines_policy"}] * len(docs),
        ids=[f"policy-{i}" for i in range(len(docs))]
    )

    print(f"Ingested {len(docs)} chunks into Chroma.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "airlines_policy.md"
    ingest_markdown(path)
