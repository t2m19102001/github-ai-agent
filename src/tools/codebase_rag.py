#!/usr/bin/env python3
"""
RAG for entire codebase using Chroma + OllamaEmbeddings
Provides semantic search across the repository
"""

from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import glob

# Global vector store
vectordb = None

# Initialize embedder with deepseek-coder model
embedder = OllamaEmbeddings(model="deepseek-coder-v2:16b-instruct-qat")


def index_repo(path="."):
    """
    Index the entire repository for RAG retrieval
    
    Args:
        path: Root path of the repository (default: current directory)
    """
    global vectordb
    
    # Collect all Python files recursively
    files = glob.glob("**/*.py", recursive=True)
    texts, metadatas = [], []
    
    for f in files:
        # Skip files larger than 1MB
        if os.path.getsize(f) > 1_000_000:
            continue
        
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                source = file.read()
                # Store metadata about the source file
                metadatas.append({"source": f})
        except Exception:
            continue
    
    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    docs = splitter.create_documents(texts, metadatas)
    
    # Create or update vector store
    vectordb = Chroma.from_documents(docs, embedder, persist_directory=".chroma")
    vectordb.persist()


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
