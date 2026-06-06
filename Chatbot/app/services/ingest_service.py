from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from app.services.embedding_service import get_embeddings


class IngestService:

    @staticmethod
    def create_vectorstore(
        knowledge_base_dir,
        vectorstore_dir
    ):

        documents = []

        for file_path in Path(knowledge_base_dir).glob("*.md"):

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as f:

                content = f.read()

            if content.strip():

                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file_path.name
                        }
                    )
                )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )

        chunks = splitter.split_documents(
            documents
        )

        embeddings = get_embeddings()

        vectorstore = FAISS.from_documents(
            chunks,
            embeddings
        )

        vectorstore.save_local(
            vectorstore_dir
        )

        return len(chunks)