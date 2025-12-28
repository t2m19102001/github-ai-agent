#!/usr/bin/env python3
"""
Vector Store Module
Provides vector storage and retrieval for RAG system
"""

import os
import json
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not available. Using fallback storage.")

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Document:
    """Document structure for vector storage"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class SearchResult:
    """Search result from vector store"""
    document: Document
    score: float
    metadata: Dict[str, Any]


class VectorStore:
    """Vector storage and retrieval system"""
    
    def __init__(self, dimension: int = 768, storage_path: str = "data/vector_store"):
        self.dimension = dimension
        self.storage_path = storage_path
        self.documents = []
        self.metadata = {}
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
        
        # Initialize FAISS index if available
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(dimension)
            logger.info("Initialized FAISS vector store")
        else:
            self.index = None
            logger.warning("FAISS not available, using fallback storage")
        
        # Load existing data
        self._load_storage()
    
    def _load_storage(self):
        """Load existing vector store data"""
        try:
            # Load documents
            docs_file = os.path.join(self.storage_path, "documents.json")
            if os.path.exists(docs_file):
                with open(docs_file, 'r', encoding='utf-8') as f:
                    docs_data = json.load(f)
                
                for doc_data in docs_data:
                    doc = Document(
                        id=doc_data["id"],
                        content=doc_data["content"],
                        metadata=doc_data["metadata"],
                        created_at=datetime.fromisoformat(doc_data["created_at"])
                    )
                    self.documents.append(doc)
            
            # Load FAISS index
            if FAISS_AVAILABLE and self.index:
                index_file = os.path.join(self.storage_path, "faiss.index")
                if os.path.exists(index_file):
                    self.index = faiss.read_index(index_file)
                    logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            # Load metadata
            metadata_file = os.path.join(self.storage_path, "metadata.json")
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            logger.info(f"Loaded {len(self.documents)} documents from storage")
            
        except Exception as e:
            logger.error(f"Error loading vector storage: {e}")
            self.documents = []
            self.metadata = {}
    
    def _save_storage(self):
        """Save vector store data"""
        try:
            # Save documents
            docs_file = os.path.join(self.storage_path, "documents.json")
            docs_data = []
            for doc in self.documents:
                docs_data.append({
                    "id": doc.id,
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "created_at": doc.created_at.isoformat()
                })
            
            with open(docs_file, 'w', encoding='utf-8') as f:
                json.dump(docs_data, f, indent=2, ensure_ascii=False)
            
            # Save FAISS index
            if FAISS_AVAILABLE and self.index:
                index_file = os.path.join(self.storage_path, "faiss.index")
                faiss.write_index(self.index, index_file)
            
            # Save metadata
            metadata_file = os.path.join(self.storage_path, "metadata.json")
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
            
            logger.info(f"Saved {len(self.documents)} documents to storage")
            
        except Exception as e:
            logger.error(f"Error saving vector storage: {e}")
    
    def add_document(self, content: str, metadata: Dict[str, Any] = None, 
                   doc_id: str = None, embedding: np.ndarray = None) -> str:
        """Add document to vector store"""
        try:
            # Generate ID if not provided
            if doc_id is None:
                doc_id = f"doc_{len(self.documents)}_{int(datetime.now().timestamp())}"
            
            # Create document
            document = Document(
                id=doc_id,
                content=content,
                metadata=metadata or {},
                embedding=embedding
            )
            
            self.documents.append(document)
            
            # Add to FAISS index if embedding provided
            if FAISS_AVAILABLE and self.index and embedding is not None:
                embedding_vector = np.array([embedding]).astype('float32')
                self.index.add(embedding_vector)
            
            logger.info(f"Added document {doc_id} to vector store")
            return doc_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise
    
    def add_documents_batch(self, documents: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
        """Add multiple documents to vector store"""
        doc_ids = []
        for content, metadata in documents:
            doc_id = self.add_document(content, metadata)
            doc_ids.append(doc_id)
        
        # Save after batch
        self._save_storage()
        return doc_ids
    
    def search(self, query_embedding: np.ndarray, k: int = 5, 
              filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search for similar documents"""
        try:
            if not self.documents:
                return []
            
            # Use FAISS if available
            if FAISS_AVAILABLE and self.index:
                return self._search_faiss(query_embedding, k, filter_metadata)
            else:
                return self._search_fallback(query_embedding, k, filter_metadata)
                
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []
    
    def _search_faiss(self, query_embedding: np.ndarray, k: int, 
                     filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Search using FAISS index"""
        try:
            # Perform search
            query_vector = np.array([query_embedding]).astype('float32')
            scores, indices = self.index.search(query_vector, min(k, len(self.documents)))
            
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx >= 0 and idx < len(self.documents):
                    doc = self.documents[idx]
                    
                    # Apply metadata filter if provided
                    if filter_metadata:
                        if not self._matches_filter(doc.metadata, filter_metadata):
                            continue
                    
                    result = SearchResult(
                        document=doc,
                        score=float(1 / (1 + score)),  # Convert distance to similarity
                        metadata={"search_rank": i + 1}
                    )
                    results.append(result)
                
                if len(results) >= k:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Error in FAISS search: {e}")
            return []
    
    def _search_fallback(self, query_embedding: np.ndarray, k: int, 
                       filter_metadata: Dict[str, Any] = None) -> List[SearchResult]:
        """Fallback search without FAISS"""
        try:
            # Simple similarity search using numpy
            results = []
            
            for doc in self.documents:
                if doc.embedding is None:
                    continue
                
                # Apply metadata filter if provided
                if filter_metadata:
                    if not self._matches_filter(doc.metadata, filter_metadata):
                        continue
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, doc.embedding)
                
                result = SearchResult(
                    document=doc,
                    score=similarity,
                    metadata={"search_method": "fallback"}
                )
                results.append(result)
            
            # Sort by similarity and return top k
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
            
        except Exception:
            return 0.0
    
    def _matches_filter(self, metadata: Dict[str, Any], 
                     filter_criteria: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_criteria.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
        
        return True
    
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None
    
    def update_document(self, doc_id: str, content: str = None, 
                     metadata: Dict[str, Any] = None) -> bool:
        """Update existing document"""
        try:
            for i, doc in enumerate(self.documents):
                if doc.id == doc_id:
                    if content is not None:
                        doc.content = content
                    if metadata is not None:
                        doc.metadata.update(metadata)
                    
                    # Rebuild index if FAISS is available
                    if FAISS_AVAILABLE:
                        self._rebuild_index()
                    
                    self._save_storage()
                    logger.info(f"Updated document {doc_id}")
                    return True
            
            logger.warning(f"Document {doc_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document from vector store"""
        try:
            for i, doc in enumerate(self.documents):
                if doc.id == doc_id:
                    del self.documents[i]
                    
                    # Rebuild index if FAISS is available
                    if FAISS_AVAILABLE:
                        self._rebuild_index()
                    
                    self._save_storage()
                    logger.info(f"Deleted document {doc_id}")
                    return True
            
            logger.warning(f"Document {doc_id} not found")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def _rebuild_index(self):
        """Rebuild FAISS index from documents"""
        if not FAISS_AVAILABLE or not self.index:
            return
        
        try:
            # Create new index
            self.index = faiss.IndexFlatL2(self.dimension)
            
            # Add all documents with embeddings
            embeddings = []
            for doc in self.documents:
                if doc.embedding is not None:
                    embeddings.append(doc.embedding)
            
            if embeddings:
                embedding_matrix = np.vstack(embeddings).astype('float32')
                self.index.add(embedding_matrix)
            
            logger.info(f"Rebuilt FAISS index with {len(embeddings)} vectors")
            
        except Exception as e:
            logger.error(f"Error rebuilding index: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            "total_documents": len(self.documents),
            "dimension": self.dimension,
            "storage_path": self.storage_path,
            "faiss_available": FAISS_AVAILABLE,
            "index_size": self.index.ntotal if FAISS_AVAILABLE and self.index else 0,
            "last_updated": self.metadata.get("last_updated"),
            "document_types": self._get_document_types()
        }
    
    def _get_document_types(self) -> Dict[str, int]:
        """Get count of documents by type"""
        types = {}
        for doc in self.documents:
            doc_type = doc.metadata.get("type", "unknown")
            types[doc_type] = types.get(doc_type, 0) + 1
        return types
    
    def save(self):
        """Save vector store to disk"""
        self._save_storage()
        self.metadata["last_updated"] = datetime.now().isoformat()
    
    def clear(self):
        """Clear all documents from vector store"""
        self.documents.clear()
        
        if FAISS_AVAILABLE and self.index:
            self.index = faiss.IndexFlatL2(self.dimension)
        
        self._save_storage()
        logger.info("Cleared vector store")


# Global instance
_vector_store: Optional[VectorStore] = None


def get_vector_store(dimension: int = 768, storage_path: str = "data/vector_store") -> VectorStore:
    """Get global vector store instance"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore(dimension, storage_path)
    return _vector_store


# Test function
def test_vector_store():
    """Test vector store functionality"""
    try:
        # Create vector store
        store = VectorStore(dimension=3, storage_path="test_vector_store")
        
        # Add test documents
        docs = [
            ("This is about Python programming", {"type": "code", "language": "python"}),
            ("This is about machine learning", {"type": "ml", "topic": "ai"}),
            ("This is about web development", {"type": "web", "framework": "react"})
        ]
        
        # Create fake embeddings for testing
        import random
        embeddings = [np.random.rand(3) for _ in docs]
        
        doc_ids = []
        for (content, metadata), embedding in zip(docs, embeddings):
            doc_id = store.add_document(content, metadata, embedding=embedding)
            doc_ids.append(doc_id)
        
        print(f"Added {len(doc_ids)} documents")
        
        # Test search
        query_embedding = np.random.rand(3)
        results = store.search(query_embedding, k=2)
        
        print(f"Search results:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result.document.content[:50]}... (score: {result.score:.3f})")
        
        # Test stats
        stats = store.get_stats()
        print(f"Stats: {json.dumps(stats, indent=2, default=str)}")
        
        # Cleanup
        store.clear()
        
    except Exception as e:
        print(f"Error testing vector store: {e}")


if __name__ == "__main__":
    test_vector_store()
