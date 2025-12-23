#!/usr/bin/env python3
"""
LlamaIndex RAG Adapter for GitHub AI Agent
Implements vector indexing and retrieval with performance tracking
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Try to import LlamaIndex, fallback to simple implementation
try:
    from llama_index import VectorStoreIndex, SimpleDirectoryReader, ServiceContext
    from llama_index.retrievers import VectorIndexRetriever
    from llama_index.query_engine import RetrieverQueryEngine
    from llama_index.node_parser import SimpleNodeParser
    from llama_index.embeddings import OpenAIEmbedding
    from llama_index.storage.storage_context import StorageContext
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    LLAMAINDEX_AVAILABLE = False

from src.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleVectorDB:
    """Simple fallback vector database when LlamaIndex is not available"""
    
    def __init__(self):
        self.documents = []
        self.embeddings = []
    
    def add_documents(self, documents: List[str]):
        """Add documents to vector store"""
        self.documents.extend(documents)
        # Simple text-based similarity for fallback
        self.embeddings = [doc.lower().split() for doc in self.documents]
    
    def query(self, query: str, top_k: int = 5) -> List[str]:
        """Simple text-based retrieval"""
        query_words = query.lower().split()
        scores = []
        
        for doc_words in self.embeddings:
            # Simple word overlap scoring
            overlap = len(set(query_words) & set(doc_words))
            scores.append(overlap)
        
        # Get top results
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.documents[i] for i in top_indices]


class LlamaIndexRAG:
    """RAG implementation with LlamaIndex or fallback"""
    
    def __init__(self, index_path: str = ".llamaindex"):
        self.index_path = Path(index_path)
        self.index = None
        self.query_engine = None
        self.query_times = []
        self.index_times = []
        
        # Performance metrics
        self.total_queries = 0
        self.relevant_results = 0
        
        # Initialize based on availability
        if LLAMAINDEX_AVAILABLE:
            self.backend = "llamaindex"
            logger.info("Using LlamaIndex backend")
        else:
            self.backend = "simple"
            self.simple_db = SimpleVectorDB()
            logger.warning("LlamaIndex not available, using simple fallback")
    
    def build_index(self, source_dirs: List[str]) -> Dict[str, Any]:
        """Build vector index from source code"""
        start_time = time.time()
        
        try:
            if self.backend == "llamaindex":
                return self._build_llamaindex_index(source_dirs)
            else:
                return self._build_simple_index(source_dirs)
                
        except Exception as e:
            logger.error(f"Index building failed: {e}")
            return {"error": str(e), "build_time": time.time() - start_time}
    
    def _build_llamaindex_index(self, source_dirs: List[str]) -> Dict[str, Any]:
        """Build index using LlamaIndex"""
        documents = []
        
        # Load documents from source directories
        for directory in source_dirs:
            if not os.path.exists(directory):
                logger.warning(f"Directory {directory} does not exist")
                continue
                
            reader = SimpleDirectoryReader(
                input_dir=directory,
                required_exts=[".py", ".md", ".yaml", ".json", ".txt"],
                recursive=True,
                exclude=[".git", "__pycache__", "node_modules", ".venv"]
            )
            
            try:
                docs = reader.load_data()
                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} documents from {directory}")
            except Exception as e:
                logger.error(f"Failed to load documents from {directory}: {e}")
        
        if not documents:
            raise Exception("No documents found to index")
        
        # Create service context
        embed_model = OpenAIEmbedding(api_key=os.getenv("OPENAI_API_KEY", ""))
        node_parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=20)
        
        service_context = ServiceContext.from_defaults(
            embed_model=embed_model,
            node_parser=node_parser
        )
        
        # Create index
        self.index = VectorStoreIndex.from_documents(
            documents,
            service_context=service_context
        )
        
        # Create query engine
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=8
        )
        
        self.query_engine = RetrieverQueryEngine.from_args(retriever)
        
        # Persist index
        self.index.storage_context.persist(persist_dir=str(self.index_path))
        
        build_time = time.time() - time.time()
        self.index_times.append(build_time)
        
        return {
            "backend": "llamaindex",
            "documents_count": len(documents),
            "build_time": build_time,
            "index_path": str(self.index_path)
        }
    
    def _build_simple_index(self, source_dirs: List[str]) -> Dict[str, Any]:
        """Build simple index when LlamaIndex is not available"""
        documents = []
        
        # Load documents manually
        for directory in source_dirs:
            if not os.path.exists(directory):
                continue
                
            for file_path in Path(directory).rglob("*"):
                if file_path.is_file() and file_path.suffix in [".py", ".md", ".yaml", ".json", ".txt"]:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if len(content.strip()) > 50:  # Skip very short files
                                documents.append(f"File: {file_path.relative_to(directory)}\n\n{content}")
                    except Exception as e:
                        logger.warning(f"Could not read {file_path}: {e}")
        
        # Add to simple DB
        self.simple_db.add_documents(documents)
        
        build_time = time.time() - time.time()
        self.index_times.append(build_time)
        
        return {
            "backend": "simple",
            "documents_count": len(documents),
            "build_time": build_time
        }
    
    def query(self, question: str, top_k: int = 8) -> str:
        """Query RAG with performance tracking"""
        if not question.strip():
            return "Empty query provided"
        
        query_start = time.time()
        self.total_queries += 1
        
        try:
            if self.backend == "llamaindex":
                response = self._query_llamaindex(question, top_k)
            else:
                response = self._query_simple(question, top_k)
            
            query_time = time.time() - query_start
            self.query_times.append(query_time)
            
            # Success metric: <0.8s retrieval time
            if query_time > 0.8:
                logger.warning(f"RAG query took {query_time:.2f}s, expected <0.8s")
            
            # Simple relevance check (placeholder)
            if response and len(response) > 100:
                self.relevant_results += 1
            
            return response
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return f"Query failed: {str(e)}"
    
    def _query_llamaindex(self, question: str, top_k: int) -> str:
        """Query using LlamaIndex"""
        if not self.query_engine:
            # Try to load existing index
            self._load_existing_index()
        
        if not self.query_engine:
            raise Exception("No query engine available")
        
        response = self.query_engine.query(question)
        return str(response)
    
    def _query_simple(self, question: str, top_k: int) -> str:
        """Query using simple fallback"""
        if not hasattr(self, 'simple_db') or not self.simple_db.documents:
            raise Exception("No documents available for querying")
        
        results = self.simple_db.query(question, top_k)
        
        if not results:
            return "No relevant information found"
        
        # Combine results
        combined = "\n\n".join(results[:3])  # Top 3 results
        return f"Relevant information:\n\n{combined}"
    
    def _load_existing_index(self):
        """Load existing index if available"""
        try:
            if self.index_path.exists() and LLAMAINDEX_AVAILABLE:
                storage_context = StorageContext.from_defaults(persist_dir=str(self.index_path))
                self.index = load_index_from_storage(storage_context)
                
                retriever = VectorIndexRetriever(
                    index=self.index,
                    similarity_top_k=8
                )
                
                self.query_engine = RetrieverQueryEngine.from_args(retriever)
                logger.info("Loaded existing LlamaIndex")
        except Exception as e:
            logger.warning(f"Could not load existing index: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get RAG performance metrics"""
        if not self.query_times:
            return {
                "avg_query_time": 0,
                "total_queries": 0,
                "relevance_rate": 0,
                "meets_time_target": True,
                "meets_relevance_target": False
            }
        
        avg_query_time = sum(self.query_times) / len(self.query_times)
        relevance_rate = self.relevant_results / self.total_queries if self.total_queries > 0 else 0
        
        return {
            "backend": self.backend,
            "avg_query_time": avg_query_time,
            "total_queries": self.total_queries,
            "relevance_rate": relevance_rate,
            "meets_time_target": avg_query_time < 0.8,  # Success metric: <0.8s retrieval
            "meets_relevance_target": relevance_rate >= 0.8,  # Success metric: ≥80% relevance
            "index_stats": {
                "avg_build_time": sum(self.index_times) / len(self.index_times) if self.index_times else 0,
                "index_count": len(self.index_times)
            }
        }
    
    def clear_cache(self):
        """Clear cached data"""
        self.query_times.clear()
        self.total_queries = 0
        self.relevant_results = 0
        
        if self.backend == "simple" and hasattr(self, 'simple_db'):
            self.simple_db = SimpleVectorDB()
        
        logger.info("RAG cache cleared")


# Global RAG instance
rag_instance: Optional[LlamaIndexRAG] = None


def initialize_rag(index_path: str = ".llamaindex") -> LlamaIndexRAG:
    """Initialize global RAG instance"""
    global rag_instance
    rag_instance = LlamaIndexRAG(index_path)
    return rag_instance


def get_rag_instance() -> Optional[LlamaIndexRAG]:
    """Get global RAG instance"""
    return rag_instance


# Convenience function for quick queries
def query_rag(question: str, top_k: int = 8) -> str:
    """Quick query function"""
    rag = get_rag_instance()
    if not rag:
        return "RAG not initialized"
    
    return rag.query(question, top_k)
