from langchain_community.vectorstores import FAISS

from app.services.embedding_service import get_embeddings
from app.services.mistral_service import generate_response


class RAGService:

    def __init__(self):

        self.vectorstore = FAISS.load_local(
            "app/vectorstore/faiss_index",
            get_embeddings(),
            allow_dangerous_deserialization=True
        )

    def get_response(
        self,
        query: str
    ):

        docs = self.vectorstore.similarity_search(
            query,
            k=3
        )

        context = "\n\n".join(
            [doc.page_content for doc in docs]
        )

        prompt = f"""
Context:
{context}

Question:
{query}

Answer:
"""

        return generate_response(prompt)


rag_service = RAGService()