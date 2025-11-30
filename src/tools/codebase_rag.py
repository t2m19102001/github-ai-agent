#!/usr/bin/env python3
"""
RAG for entire codebase using Chroma + Configurable Embeddings
Provides semantic search across the repository
Supports: Ollama (local), OpenAI (cloud), Groq (cloud with local fallback)
"""

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import glob

# Import config
from src.config.settings import PROVIDER, MODELS, LLMProvider

# Global vector store
vectordb = None

# Initialize embedder based on provider
def get_embedder():
    """Get embeddings model based on configured provider"""
    if PROVIDER == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(model=MODELS[PROVIDER])
        except Exception as e:
            print(f"⚠️ Ollama failed: {e}, using HuggingFace")
    
    # Fallback to free HuggingFace embeddings (for Groq/OpenAI/errors)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except ImportError:
        raise ImportError("Install: pip install langchain-huggingface")

embedder = get_embedder()


def index_repo(path="."):
    """
    Index the entire repository for RAG retrieval
    
    Args:
        path: Root path of the repository (default: current directory)
    """
    global vectordb
    
    print("Đang index toàn bộ repo... (chỉ chạy lần đầu)")
    
    # Collect all Python files recursively
    files = [f for f in glob.glob("**/*.py", recursive=True) if not f.startswith(".chroma") and os.path.getsize(f) < 1_000_000]
    
    texts, metadatas = [], []
    
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                texts.append(file.read())
                metadatas.append({"source": f})
        except:
            pass
    
    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    docs = splitter.create_documents(texts, metadatas)
    
    # Create or update vector store
    vectordb = Chroma.from_documents(docs, embedder, persist_directory=".chroma")
    vectordb.persist()
    print("Index xong!")


def retrieve(query, k=15):
    """
    Retrieve relevant code snippets from the indexed repository
    
    Args:
        query: Search query
        k: Number of results to return (default: 15)
    
    Returns:
        String with retrieved file paths and content snippets
    """
    global vectordb
    
    if vectordb is None:
        # Try to load existing index
        if os.path.exists(".chroma"):
            vectordb = Chroma(persist_directory=".chroma", embedding_function=embedder)
        else:
            # Index the repository if no index exists
            index_repo()
    
    # Perform similarity search
    results = vectordb.similarity_search(query, k=k)
    
    # Format results for context
    return "\n\n".join([f"File {r.metadata['source']}:\n{r.page_content}" for r in results])


def get_context(question, k=15):
    """
    Get context from codebase for a question
    Wrapper around retrieve() for better naming
    
    Args:
        question: User's question
        k: Number of results (default: 15)
    
    Returns:
        Formatted context string
    """
    global vectordb
    
    if vectordb is None:
        if os.path.exists(".chroma"):
            vectordb = Chroma(persist_directory=".chroma", embedding_function=embedder)
        else:
            index_repo()
    
    results = vectordb.similarity_search(question, k=k)
    return "\n\n".join([f"File: {r.metadata['source']}:\n{r.page_content}" for r in results])
