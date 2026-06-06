# test_embedding.py

from app.services.embedding_service import get_embeddings

embeddings = get_embeddings()

vector = embeddings.embed_query(
    "What is blood donation?"
)

print(len(vector))
print(vector[:5])