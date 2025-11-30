#!/usr/bin/env python3
"""
Long-term Memory System using Chroma Vector Store
Stores and retrieves conversation history for context-aware responses
Supports: Ollama (local), Groq (cloud), OpenAI (cloud) - Auto fallback
"""

from langchain_chroma import Chroma
from src.utils.logger import get_logger
from src.config.settings import PROVIDER, MODELS
import os
import shutil
import uuid

logger = get_logger(__name__)

# Initialize embedder based on provider
def get_embedder():
    """Get embeddings model based on configured provider"""
    if PROVIDER == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(model=MODELS["ollama"])
        except Exception as e:
            logger.warning(f"⚠️ Ollama failed: {e}, using HuggingFace")
    
    # Fallback to free HuggingFace embeddings (for Groq/OpenAI/errors)
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except ImportError:
        logger.error("❌ Install: pip install langchain-huggingface")
        raise

embedder = get_embedder()

# Global conversation database with error recovery
MEMORY_PATH = ".memory"

try:
    conversation_db = Chroma(persist_directory=MEMORY_PATH, embedding_function=embedder)
    logger.info(f"✅ Memory loaded from {MEMORY_PATH}")
except Exception as e:
    logger.warning(f"⚠️ Memory corrupted, recreating: {e}")
    if os.path.exists(MEMORY_PATH):
        shutil.rmtree(MEMORY_PATH)
    conversation_db = Chroma(persist_directory=MEMORY_PATH, embedding_function=embedder)
    logger.info(f"✅ Fresh memory created at {MEMORY_PATH}")


def save_memory(session_id: str, user_msg: str, ai_msg: str):
    """
    Save a conversation turn to memory
    
    Args:
        session_id: Unique session identifier
        user_msg: User's message
        ai_msg: AI's response
    """
    try:
        # Store both messages with metadata
        conversation_db.add_texts(
            texts=[user_msg, ai_msg],
            metadatas=[
                {"session_id": session_id, "role": "user"},
                {"session_id": session_id, "role": "assistant"}
            ],
            ids=[str(uuid.uuid4()), str(uuid.uuid4())]
        )
        conversation_db.persist()
        logger.info(f"💾 Saved memory for session: {session_id}")
    except Exception as e:
        logger.error(f"❌ Failed to save memory: {e}")


def get_memory(session_id: str, k=20):
    """
    Retrieve conversation history for a session
    
    Args:
        session_id: Unique session identifier
        k: Number of messages to retrieve (default: 20)
    
    Returns:
        String with formatted conversation history
    """
    try:
        # Search for messages from this session
        results = conversation_db.similarity_search(
            query="history", 
            k=k
        )
        
        # Filter by session_id (Chroma filter doesn't work reliably)
        filtered_results = [
            doc for doc in results 
            if doc.metadata.get("session_id") == session_id
        ]
        
        # Format conversation history
        lines = []
        for doc in filtered_results[:10]:  # Limit to most recent 10
            role = "Bạn" if doc.metadata.get("role") == "user" else "AI"
            lines.append(f"{role}: {doc.page_content}")
        
        history = "\n".join(lines) if lines else "Chưa có lịch sử."
        logger.info(f"🔍 Retrieved {len(lines)} memories for session: {session_id}")
        return history
    except Exception as e:
        logger.error(f"❌ Failed to retrieve memory: {e}")
        return "Lịch sử tạm thời không khả dụng."
