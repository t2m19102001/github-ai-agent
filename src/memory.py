#!/usr/bin/env python3
import os
import shutil
import uuid

from src.utils.logger import get_logger
from src.config.settings import PROVIDER, MODELS

logger = get_logger(__name__)

try:
    from langchain_chroma import Chroma
except Exception:
    Chroma = None

class SimpleMemory:
    def __init__(self):
        self.items = []
    def add_texts(self, texts, metadatas, ids):
        for t, m, i in zip(texts, metadatas, ids):
            self.items.append({"text": t, "metadata": m, "id": i})
    def similarity_search(self, query, k=20):
        scored = []
        for it in self.items:
            score = sum(1 for w in query.lower().split() if w and w in it["text"].lower())
            scored.append((it, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        result = []
        for it, _ in scored[:k]:
            class Doc:
                page_content = it["text"]
                metadata = it["metadata"]
            result.append(Doc)
        return result

MEMORY_PATH = ".memory"

enable_vector = os.getenv("ENABLE_VECTOR_DB", "0") == "1"

if enable_vector and Chroma:
    try:
        if PROVIDER == "ollama":
            from langchain_ollama import OllamaEmbeddings
            embedder = OllamaEmbeddings(model=MODELS["ollama"])
        else:
            from langchain_huggingface import HuggingFaceEmbeddings
            embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        conversation_db = Chroma(persist_directory=MEMORY_PATH, embedding_function=embedder)
    except Exception:
        conversation_db = SimpleMemory()
else:
    conversation_db = SimpleMemory()

def save_memory(session_id: str, user_msg: str, ai_msg: str):
    try:
        conversation_db.add_texts(
            texts=[user_msg, ai_msg],
            metadatas=[
                {"session_id": session_id, "role": "user"},
                {"session_id": session_id, "role": "assistant"}
            ],
            ids=[str(uuid.uuid4()), str(uuid.uuid4())]
        )
    except Exception:
        pass

def get_memory(session_id: str, k=20):
    try:
        results = conversation_db.similarity_search(query="history", k=k)
        filtered = [doc for doc in results if doc.metadata.get("session_id") == session_id]
        lines = []
        for doc in filtered[:10]:
            role = "Bạn" if doc.metadata.get("role") == "user" else "AI"
            lines.append(f"{role}: {doc.page_content}")
        history = "\n".join(lines) if lines else "Chưa có lịch sử."
        return history
    except Exception:
        return "Lịch sử tạm thời không khả dụng."
