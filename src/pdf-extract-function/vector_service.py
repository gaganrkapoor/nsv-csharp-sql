"""
Vector Database Service for ChromaDB Integration
Handles document embeddings, storage, and semantic search
"""

import chromadb
from chromadb.config import Settings
import os
import json
from typing import List, Dict, Any, Optional
import logging
import uuid
from datetime import datetime
import hashlib

# Try to import OpenAI embeddings (will install in requirements.txt)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available. Please install: pip install openai")

class VectorService:
    """ChromaDB Vector Database Service"""
    
    def __init__(self):
        """Initialize ChromaDB client and configuration"""
        self.chroma_host = os.getenv('CHROMA_HOST', 'localhost')
        self.chroma_port = int(os.getenv('CHROMA_PORT', '8000'))
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Initialize ChromaDB client
        try:
            self.client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logging.info(f"Connected to ChromaDB at {self.chroma_host}:{self.chroma_port}")
        except Exception as e:
            logging.error(f"Failed to connect to ChromaDB: {str(e)}")
            raise
        
        # Initialize OpenAI client
        self.openai_client = None
        if OPENAI_AVAILABLE and self.openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=self.openai_api_key)
                logging.info("OpenAI client initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {str(e)}")
        
        # Text processing configuration
        self.chunk_size = 1000
        self.chunk_overlap = 200

    def create_or_get_collection(self, pdf_type: str) -> chromadb.Collection:
        """Create or get a collection for a specific PDF type"""
        # Sanitize collection name
        collection_name = f"pdf_{self._sanitize_collection_name(pdf_type)}"
        
        try:
            collection = self.client.get_collection(collection_name)
            logging.info(f"Retrieved existing collection: {collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            try:
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "pdf_type": pdf_type,
                        "created_at": datetime.now().isoformat(),
                        "description": f"Collection for {pdf_type} documents"
                    }
                )
                logging.info(f"Created new collection: {collection_name}")
            except Exception as e:
                logging.error(f"Failed to create collection {collection_name}: {str(e)}")
                raise
        
        return collection

    def store_document_vector(self, 
                            pdf_filename: str, 
                            extracted_json: Dict[str, Any], 
                            pdf_type: str) -> str:
        """Store document in vector database with embeddings"""
        try:
            # Get or create collection for this PDF type
            collection = self.create_or_get_collection(pdf_type)
            
            # Convert JSON to searchable text
            text_content = self._json_to_searchable_text(extracted_json)
            
            # Split into chunks
            chunks = self._split_text_into_chunks(text_content)
            
            # Generate document ID
            document_id = str(uuid.uuid4())
            
            # Store each chunk
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                
                # Generate embedding if OpenAI is available
                embedding = None
                if self.openai_client:
                    embedding = self._generate_embedding(chunk)
                
                # Prepare metadata
                metadata = {
                    "filename": pdf_filename,
                    "pdf_type": pdf_type,
                    "chunk_index": i,
                    "document_id": document_id,
                    "timestamp": datetime.now().isoformat(),
                    "total_chunks": len(chunks),
                    "original_json_hash": self._hash_json(extracted_json)
                }
                
                # Add to collection
                if embedding:
                    collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        documents=[chunk],
                        metadatas=[metadata]
                    )
                else:
                    # Add without embedding (ChromaDB will use default embedding)
                    collection.add(
                        ids=[chunk_id],
                        documents=[chunk],
                        metadatas=[metadata]
                    )
            
            logging.info(f"Stored document {pdf_filename} with {len(chunks)} chunks in collection {pdf_type}")
            return document_id
            
        except Exception as e:
            logging.error(f"Error storing document in vector DB: {str(e)}")
            raise

    def search_similar_documents(self, 
                                query: str, 
                                pdf_type: Optional[str] = None, 
                                top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents using vector similarity"""
        try:
            results = []
            
            if pdf_type:
                # Search in specific collection
                collection = self.create_or_get_collection(pdf_type)
                collection_results = self._search_collection(collection, query, top_k)
                results.extend(collection_results)
            else:
                # Search across all collections
                collections = self.client.list_collections()
                
                for collection_info in collections:
                    try:
                        collection = self.client.get_collection(collection_info.name)
                        collection_results = self._search_collection(collection, query, top_k)
                        results.extend(collection_results)
                    except Exception as e:
                        logging.warning(f"Error searching collection {collection_info.name}: {str(e)}")
            
            # Sort by similarity score and limit results
            results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logging.error(f"Error searching vector DB: {str(e)}")
            return []

    def _search_collection(self, collection: chromadb.Collection, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Search within a specific collection"""
        try:
            # Generate query embedding if OpenAI is available
            if self.openai_client:
                query_embedding = self._generate_embedding(query)
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, 10)  # Limit per collection
                )
            else:
                # Use text-based search if no embeddings available
                results = collection.query(
                    query_texts=[query],
                    n_results=min(top_k, 10)
                )
            
            return self._format_search_results(results)
            
        except Exception as e:
            logging.error(f"Error searching collection: {str(e)}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about all collections"""
        try:
            collections = self.client.list_collections()
            stats = {
                "total_collections": len(collections),
                "collections": {}
            }
            
            for collection_info in collections:
                try:
                    collection = self.client.get_collection(collection_info.name)
                    count = collection.count()
                    stats["collections"][collection_info.name] = {
                        "document_count": count,
                        "metadata": collection_info.metadata or {}
                    }
                except Exception as e:
                    logging.warning(f"Error getting stats for {collection_info.name}: {str(e)}")
                    stats["collections"][collection_info.name] = {
                        "document_count": 0,
                        "error": str(e)
                    }
            
            return stats
        except Exception as e:
            logging.error(f"Error getting collection stats: {str(e)}")
            return {"error": str(e)}

    def delete_document(self, document_id: str, pdf_type: Optional[str] = None) -> bool:
        """Delete a document and all its chunks"""
        try:
            collections_to_search = []
            
            if pdf_type:
                collections_to_search.append(self.create_or_get_collection(pdf_type))
            else:
                # Search all collections
                for collection_info in self.client.list_collections():
                    collections_to_search.append(self.client.get_collection(collection_info.name))
            
            deleted_chunks = 0
            for collection in collections_to_search:
                try:
                    # Find all chunks for this document
                    results = collection.get(
                        where={"document_id": document_id}
                    )
                    
                    if results['ids']:
                        collection.delete(ids=results['ids'])
                        deleted_chunks += len(results['ids'])
                        logging.info(f"Deleted {len(results['ids'])} chunks from document {document_id}")
                
                except Exception as e:
                    logging.warning(f"Error deleting from collection: {str(e)}")
            
            return deleted_chunks > 0
            
        except Exception as e:
            logging.error(f"Error deleting document: {str(e)}")
            return False

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            if not self.openai_client:
                return None
                
            embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002')
            response = self.openai_client.embeddings.create(
                model=embedding_model,
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            logging.error(f"Error generating embedding: {str(e)}")
            return None

    def _json_to_searchable_text(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON data to searchable text"""
        def extract_text_recursive(obj, path=""):
            texts = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if isinstance(value, (str, int, float)) and value:
                        texts.append(f"{key}: {value}")
                    elif isinstance(value, (list, dict)):
                        texts.extend(extract_text_recursive(value, current_path))
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]" if path else f"[{i}]"
                    texts.extend(extract_text_recursive(item, current_path))
            
            elif obj is not None:
                texts.append(str(obj))
            
            return texts
        
        extracted_texts = extract_text_recursive(json_data)
        return " ".join(extracted_texts)

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at word boundary
            if end < len(text):
                last_space = text.rfind(' ', start, end)
                if last_space > start:
                    end = last_space
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start < 0:
                start = end
        
        return chunks

    def _format_search_results(self, results) -> List[Dict[str, Any]]:
        """Format ChromaDB search results"""
        formatted_results = []
        
        if not results or not results.get('documents'):
            return formatted_results
        
        documents = results['documents'][0] if results['documents'] else []
        metadatas = results['metadatas'][0] if results.get('metadatas') else []
        distances = results['distances'][0] if results.get('distances') else []
        
        for i, document in enumerate(documents):
            metadata = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            
            # Convert distance to similarity score (0 to 1, higher is better)
            similarity_score = max(0, 1 - distance)
            
            formatted_results.append({
                "document": document,
                "metadata": metadata,
                "similarity_score": similarity_score,
                "filename": metadata.get("filename", "unknown"),
                "pdf_type": metadata.get("pdf_type", "unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "document_id": metadata.get("document_id", "unknown")
            })
        
        return formatted_results

    def _sanitize_collection_name(self, name: str) -> str:
        """Sanitize collection name for ChromaDB"""
        # Replace invalid characters with underscores
        sanitized = "".join(c if c.isalnum() else "_" for c in name.lower())
        # Remove consecutive underscores and trim
        sanitized = "_".join(filter(None, sanitized.split("_")))
        return sanitized or "unknown"

    def _hash_json(self, json_data: Dict[str, Any]) -> str:
        """Create hash of JSON data for integrity checking"""
        json_string = json.dumps(json_data, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(json_string.encode()).hexdigest()

    def health_check(self) -> Dict[str, Any]:
        """Check health of vector service"""
        try:
            # Test ChromaDB connection
            collections = self.client.list_collections()
            chroma_status = "healthy"
        except Exception as e:
            chroma_status = f"error: {str(e)}"
        
        # Test OpenAI connection
        openai_status = "not_configured"
        if self.openai_client:
            try:
                # Simple test embedding
                test_embedding = self._generate_embedding("test")
                openai_status = "healthy" if test_embedding else "error"
            except Exception as e:
                openai_status = f"error: {str(e)}"
        
        return {
            "chromadb": {
                "status": chroma_status,
                "host": self.chroma_host,
                "port": self.chroma_port
            },
            "openai": {
                "status": openai_status,
                "configured": bool(self.openai_client)
            },
            "overall_status": "healthy" if chroma_status == "healthy" else "degraded"
        }