import os
import chromadb
from chromadb.utils import embedding_functions


_client = chromadb.PersistentClient(path=os.getenv("CHROMA_DIR", ".chroma"))
_emb = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
_col = _client.get_or_create_collection("policy", embedding_function=_emb)


def retrieve(query: str, k: int = 4):
    res = _col.query(query_texts=[query], n_results=k)
    docs = res.get("documents", [[]])[0]
    return docs
