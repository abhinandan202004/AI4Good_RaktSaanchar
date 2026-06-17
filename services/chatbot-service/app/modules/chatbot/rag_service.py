from pathlib import Path
from langchain_community.vectorstores import FAISS

from app.modules.chatbot.embedding_service import get_embeddings
from app.modules.chatbot.mistral_service import generate_response
import logging

logger = logging.getLogger(__name__)

# Vectorstore folder is inside modules/chatbot/vectorstore/faiss_index
_INDEX_DIR = Path(__file__).resolve().parent / "vectorstore" / "faiss_index"

_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore
    try:
        _vectorstore = FAISS.load_local(
            str(_INDEX_DIR),
            get_embeddings(),
            allow_dangerous_deserialization=True
        )
        logger.info("✅ FAISS Vector store loaded successfully from %s", _INDEX_DIR)
    except Exception as e:
        logger.error("❌ Failed to load FAISS Vector store: %s", e)
        _vectorstore = None
    return _vectorstore


class RAGService:

    def get_response(
        self,
        query: str
    ):
        vectorstore = _get_vectorstore()
        if not vectorstore:
            return generate_response(query)

        try:
            docs = vectorstore.similarity_search(
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
        except Exception as e:
            logger.error("RAG similarity search failed: %s", e)
            return generate_response(query)


rag_service = RAGService()
