import os
from typing import List, Dict, Any
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from ollama_utils import get_best_ollama_model, get_embedding_model
from langchain_chroma import Chroma
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

class RAGSystem:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        
        # Chat model (cloud models are OK)
        self.chat_model_name = get_best_ollama_model()
        if not self.chat_model_name:
            raise RuntimeError("Could not find a valid Ollama chat model. Ensure Ollama is running.")
        
        # Embedding model (must be LOCAL, cloud models can't embed)
        self.embed_model_name = get_embedding_model()
        if not self.embed_model_name:
            raise RuntimeError(
                "Could not find a local Ollama model for embeddings.\n"
                "Cloud models (e.g. minimax-m2.5:cloud) cannot generate embeddings.\n"
                "Please pull a local model:  ollama pull nomic-embed-text"
            )

        print(f"[RAG] Chat model: {self.chat_model_name}")
        print(f"[RAG] Embedding model: {self.embed_model_name}")
        self.embeddings = OllamaEmbeddings(model=self.embed_model_name)
        self.llm = ChatOllama(model=self.chat_model_name, temperature=0)

        # Initialize an empty vector store or load existing one
        self.vectorstore = Chroma(
            collection_name="docs_collection",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def chunk_and_ingest(self, scraped_data: List[Dict[str, Any]]):
        """
        Takes scraped markdown data, chunks it intelligently based on markdown headers,
        and ingests it into ChromaDB.
        """
        if not scraped_data:
            print("No data to ingest.")
            return

        print(f"Ingesting {len(scraped_data)} markdown documents...")

        # We want to split heavily on headers so that structure is preserved
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )

        # mxbai-embed-large supports ~512 tokens; all-minilm only ~256
        # Larger chunks = better context preservation for code documentation
        chunk_size = 512
        chunk_overlap = 50
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        all_splits = []
        for item in scraped_data:
            url = item.get("url", "unknown_url")
            markdown_content = item.get("markdown", "")

            if not markdown_content:
                continue

            # 1. Split by Markdown headers
            md_header_splits = markdown_splitter.split_text(markdown_content)

            # 2. Add source URL to metadata
            for split in md_header_splits:
                split.metadata["source"] = url

            # 3. Apply secondary text splitting to ensure chunks aren't too large for the embedder
            final_splits = text_splitter.split_documents(md_header_splits)
            all_splits.extend(final_splits)

        print(f"Created {len(all_splits)} chunks. Adding to ChromaDB...")

        # Add to ChromaDB in small batches to avoid overwhelming the embedder
        if all_splits:
            batch_size = 10
            for i in range(0, len(all_splits), batch_size):
                batch = all_splits[i:i + batch_size]
                self.vectorstore.add_documents(documents=batch)
                print(f"  Ingested batch {i // batch_size + 1}/{(len(all_splits) + batch_size - 1) // batch_size}")
            print("Ingestion complete.")

    def query(self, user_query: str) -> str:
        """
        Retrieves relevant chunks from ChromaDB and generates an answer using an LLM.
        """
        print(f"Querying vector database for: '{user_query}'")

        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5} # Retrieve top 5 chunks
        )

        # Define the system prompt for generation
        system_prompt = (
            "You are an expert software engineer assistant. "
            "Use the following pieces of retrieved documentation context to answer the user's coding question. "
            "The context contains up-to-date documentation scraped directly from the source. "
            "If the answer is not contained within the context, say that you don't know based on the provided docs, "
            "but you can try to answer based on your general knowledge. "
            "Always include code examples if relevant and cite the source URL if available in the context metadata."
            "\n\nContext:\n{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])

        # Create RAG chain
        question_answer_chain = create_stuff_documents_chain(self.llm, prompt)
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        # Execute chain
        response = rag_chain.invoke({"input": user_query})

        return response["answer"]

if __name__ == "__main__":
    pass
