from pathlib import Path
import logging

from app.modules.chatbot.mistral_service import generate_response

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge_base"
_cached_context = None


def _load_knowledge_base() -> str:
    global _cached_context
    if _cached_context is not None:
        return _cached_context

    context_parts = []
    try:
        if _KNOWLEDGE_DIR.exists():
            for file_path in sorted(_KNOWLEDGE_DIR.glob("*.md")):
                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as f:
                    content = f.read().strip()
                if content:
                    doc_title = file_path.stem.replace("_", " ").title()
                    context_parts.append(
                        f"=== {doc_title} ===\n{content}"
                    )
        _cached_context = "\n\n".join(context_parts)
        logger.info(
            "Loaded chatbot knowledge base (%d chars)",
            len(_cached_context)
        )
    except Exception as e:
        logger.error("Failed to load knowledge base: %s", e)
        _cached_context = ""
    return _cached_context


class RAGService:

    def get_response(
        self,
        query: str
    ):
        context = _load_knowledge_base()
        if not context:
            return generate_response(query)

        prompt = f"""
You are the RaktaSanchaar AI Assistant. Use the following official Knowledge Base context to answer the user's question.

[KNOWLEDGE BASE CONTEXT]
{context}

[USER QUESTION]
{query}

Answer the user's question concisely, professionally, and friendly based ONLY on the context provided above. If the context does not contain the answer, answer generally or ask them to consult their coordinator.
"""
        return generate_response(prompt)


rag_service = RAGService()

