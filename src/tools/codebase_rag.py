#!/usr/bin/env python3
import os
import glob
import math

try:
    from langchain_chroma import Chroma
except Exception:
    Chroma = None
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except Exception:
    RecursiveCharacterTextSplitter = None

from src.config.settings import PROVIDER, MODELS, LLMProvider

vectordb = None

def _simple_split(text, chunk_size=2000, chunk_overlap=200):
    if not text:
        return [""]
    chunks = []
    i = 0
    n = len(text)
    while i < n:
        chunks.append(text[i:i+chunk_size])
        i += max(1, chunk_size - chunk_overlap)
    return chunks

def _keyword_score(a, b):
    aw = set([w for w in a.lower().split() if len(w) > 2])
    bw = set([w for w in b.lower().split() if len(w) > 2])
    inter = aw.intersection(bw)
    return len(inter)

class SimpleDoc:
    def __init__(self, content, metadata):
        self.page_content = content
        self.metadata = metadata

class SimpleVectorDB:
    def __init__(self, docs):
        self.docs = docs
    def similarity_search(self, query, k=15):
        scored = [(d, _keyword_score(query, d.page_content)) for d in self.docs]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [s[0] for s in scored[:k]]
        return top

def _build_docs(texts, metadatas, chunk_size=2000, chunk_overlap=200):
    docs = []
    if RecursiveCharacterTextSplitter:
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = splitter.create_documents(texts, metadatas)
    else:
        for text, meta in zip(texts, metadatas):
            for chunk in _simple_split(text, chunk_size, chunk_overlap):
                docs.append(SimpleDoc(chunk, meta))
    return docs

def index_repo(path="."):
    global vectordb
    files = [f for f in glob.glob("**/*.py", recursive=True) if not f.startswith(".chroma") and os.path.getsize(f) < 1_000_000]
    texts, metadatas = [], []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                texts.append(file.read())
                metadatas.append({"source": f})
        except Exception:
            pass
    docs = _build_docs(texts, metadatas, 2000, 200)
    if Chroma:
        try:
            from src.config.settings import PROVIDER, MODELS
            if PROVIDER == "ollama":
                from langchain_ollama import OllamaEmbeddings
                embedder = OllamaEmbeddings(model=MODELS["ollama"])
            else:
                from langchain_huggingface import HuggingFaceEmbeddings
                embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectordb = Chroma.from_documents(docs, embedder, persist_directory=".chroma")
            return
        except Exception:
            pass
    vectordb = SimpleVectorDB([SimpleDoc(d.page_content if hasattr(d, "page_content") else d, getattr(d, "metadata", {})) for d in docs])

def retrieve(query, k=15):
    global vectordb
    if vectordb is None:
        if os.path.exists(".chroma") and Chroma:
            try:
                if PROVIDER == "ollama":
                    from langchain_ollama import OllamaEmbeddings
                    embedder = OllamaEmbeddings(model=MODELS["ollama"])
                else:
                    from langchain_huggingface import HuggingFaceEmbeddings
                    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                vectordb = Chroma(persist_directory=".chroma", embedding_function=embedder)
            except Exception:
                index_repo()
        else:
            index_repo()
    results = vectordb.similarity_search(query, k=k)
    return "\n\n".join([f"File {r.metadata.get('source', '')}:\n{r.page_content}" for r in results])

def get_context(question, k=15):
    global vectordb
    if vectordb is None:
        index_repo()
    try:
        results = vectordb.similarity_search(question, k=k)
        return "\n\n".join([f"File: {r.metadata.get('source', '')}:\n{r.page_content}" for r in results])
    except Exception:
        return "(RAG unavailable)"
