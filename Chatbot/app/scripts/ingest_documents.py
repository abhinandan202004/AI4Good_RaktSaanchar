from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from app.services.embedding_service import get_embeddings


BASE_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "faiss_index"


def load_documents():

    documents = []

    print(f"Knowledge Base Path: {KNOWLEDGE_BASE_DIR}")

    for file_path in KNOWLEDGE_BASE_DIR.glob("*.md"):

        print(f"Loading: {file_path.name}")

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            content = f.read().strip()

        if content:
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": file_path.name
                    }
                )
            )

    print(f"Documents Loaded: {len(documents)}")

    return documents


def create_vectorstore():

    documents = load_documents()

    if not documents:
        raise ValueError(
            "No documents found in knowledge_base folder."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(documents)

    print(f"Chunks Created: {len(chunks)}")

    if not chunks:
        raise ValueError(
            "No chunks were created from documents."
        )

    embeddings = get_embeddings()

    VECTORSTORE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    vectorstore = FAISS.from_documents(
        chunks,
        embeddings
    )

    vectorstore.save_local(
        str(VECTORSTORE_DIR)
    )

    print(
        f"Indexed {len(chunks)} chunks successfully."
    )


if __name__ == "__main__":
    create_vectorstore()