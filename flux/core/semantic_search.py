"""Semantic Search Engine for Flux-CLI.

This module provides intelligent code search using embeddings and vector databases,
enabling Flux to understand code semantically rather than just text matching.
"""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass, asdict
import pickle
import logging

logger = logging.getLogger(__name__)


@dataclass
class CodeChunk:
    """Represents a chunk of code for embedding."""
    file_path: str
    content: str
    start_line: int
    end_line: int
    chunk_type: str  # 'function', 'class', 'module', 'block'
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        data = asdict(self)
        if self.embedding is not None:
            data['embedding'] = self.embedding.tolist()
        return data


class EmbeddingGenerator:
    """Generate embeddings for code chunks."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding generator.
        
        Args:
            model_name: Name of the sentence transformer model
        """
        self.model_name = model_name
        self.model = None
        self.use_lightweight = True  # Use lightweight TF-IDF by default
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model lazily."""
        # Skip heavy model loading entirely - use lightweight approach
        logger.info("Using lightweight TF-IDF based embeddings (no heavy dependencies)")
        self.model = None
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text using lightweight approach.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Use a simple but effective TF-IDF-like approach
        # Create a deterministic embedding based on text features
        import re
        
        # Extract features
        words = re.findall(r'\w+', text.lower())
        
        # Create a fixed-size embedding (384 dimensions to match MiniLM)
        embedding = np.zeros(384)
        
        # Use hash-based feature mapping (similar to HashingVectorizer)
        for i, word in enumerate(words[:100]):  # Limit to first 100 words
            # Hash word to get indices
            hash_val = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
            
            # Map to multiple dimensions for robustness
            for j in range(3):  # Each word affects 3 dimensions
                idx = (hash_val + j * 1000) % 384
                # TF-IDF-like weighting
                weight = 1.0 / (1.0 + np.log(1 + i))  # Position-based decay
                embedding[idx] += weight
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        # Always use lightweight approach
        return [self.generate_embedding(text) for text in texts]


class VectorStore:
    """Vector storage and retrieval using ChromaDB or in-memory fallback."""
    
    def __init__(self, collection_name: str = "flux_code", persist_dir: Optional[Path] = None):
        """Initialize vector store.
        
        Args:
            collection_name: Name of the collection
            persist_dir: Directory for persistence
        """
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self.client = None
        self.collection = None
        self.in_memory = {}  # Fallback storage
        self._init_store()
    
    def _init_store(self):
        """Initialize the vector store."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            if self.persist_dir:
                self.client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=Settings(anonymized_telemetry=False)
                )
            else:
                self.client = chromadb.Client(
                    Settings(anonymized_telemetry=False)
                )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Initialized ChromaDB collection: {self.collection_name}")
            
        except ImportError:
            logger.warning("ChromaDB not available, using in-memory storage")
            self.client = None
    
    async def add_chunks(self, chunks: List[CodeChunk]) -> None:
        """Add code chunks to the vector store.
        
        Args:
            chunks: List of code chunks with embeddings
        """
        if not chunks:
            return
        
        if self.collection is not None:
            # Use ChromaDB
            ids = [f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}" for chunk in chunks]
            embeddings = [chunk.embedding.tolist() for chunk in chunks]
            metadatas = [
                {
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    **chunk.metadata
                }
                for chunk in chunks
            ]
            documents = [chunk.content for chunk in chunks]
            
            # Add to ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
        else:
            # Use in-memory storage
            for chunk in chunks:
                chunk_id = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
                self.in_memory[chunk_id] = chunk
    
    async def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Tuple[CodeChunk, float]]:
        """Search for similar code chunks.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of (chunk, similarity_score) tuples
        """
        if self.collection is not None:
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=k,
                where=filter_dict if filter_dict else None
            )
            
            chunks_with_scores = []
            if results['ids'][0]:  # Check if we have results
                for i, chunk_id in enumerate(results['ids'][0]):
                    # Reconstruct chunk from results
                    metadata = results['metadatas'][0][i]
                    chunk = CodeChunk(
                        file_path=metadata['file_path'],
                        content=results['documents'][0][i],
                        start_line=metadata['start_line'],
                        end_line=metadata['end_line'],
                        chunk_type=metadata['chunk_type'],
                        metadata={k: v for k, v in metadata.items() 
                                 if k not in ['file_path', 'start_line', 'end_line', 'chunk_type']}
                    )
                    # Distance to similarity (1 - distance for cosine)
                    similarity = 1 - results['distances'][0][i]
                    chunks_with_scores.append((chunk, similarity))
            
            return chunks_with_scores
        
        else:
            # Search in memory using cosine similarity
            if not self.in_memory:
                return []
            
            similarities = []
            for chunk_id, chunk in self.in_memory.items():
                if filter_dict:
                    # Apply filters
                    if not all(
                        getattr(chunk, key, None) == value
                        for key, value in filter_dict.items()
                    ):
                        continue
                
                # Calculate cosine similarity
                similarity = np.dot(query_embedding, chunk.embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk.embedding)
                )
                similarities.append((chunk, float(similarity)))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:k]
    
    def clear(self) -> None:
        """Clear all stored vectors."""
        if self.collection is not None:
            # Clear ChromaDB collection
            ids = self.collection.get()['ids']
            if ids:
                self.collection.delete(ids=ids)
        else:
            self.in_memory.clear()


class SemanticSearchEngine:
    """Main semantic search engine for Flux."""
    
    def __init__(self, project_path: str, cache_dir: Optional[Path] = None):
        """Initialize semantic search engine.
        
        Args:
            project_path: Path to the project root (can be string or Path)
            cache_dir: Optional cache directory for embeddings
        """
        self.project_path = Path(project_path) if isinstance(project_path, str) else project_path
        self.cache_dir = cache_dir or self.project_path / ".flux" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_gen = EmbeddingGenerator()
        # Create valid collection name
        project_name = self.project_path.name if self.project_path.name else "default"
        # Ensure collection name is valid (alphanumeric, dots, underscores, hyphens)
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', project_name)
        if not safe_name or safe_name[0] not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789':
            safe_name = 'default'
        collection_name = f"flux_{safe_name}"
        
        self.vector_store = VectorStore(
            collection_name=collection_name,
            persist_dir=self.cache_dir
        )
        
        self.indexed_files = set()
        self.index_metadata_path = self.cache_dir / "index_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load index metadata."""
        if self.index_metadata_path.exists():
            with open(self.index_metadata_path, 'r') as f:
                data = json.load(f)
                self.indexed_files = set(data.get('indexed_files', []))
    
    def _save_metadata(self):
        """Save index metadata."""
        with open(self.index_metadata_path, 'w') as f:
            json.dump({
                'indexed_files': list(self.indexed_files)
            }, f)
    
    async def index_file(self, file_path: Path) -> int:
        """Index a single file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Number of chunks indexed
        """
        if not file_path.exists() or not file_path.is_file():
            return 0
        
        # Check if already indexed
        if str(file_path) in self.indexed_files:
            return 0
        
        # Parse file into chunks
        chunks = self._parse_file_to_chunks(file_path)
        if not chunks:
            return 0
        
        # Generate embeddings
        texts = [self._prepare_chunk_text(chunk) for chunk in chunks]
        embeddings = await self.embedding_gen.generate_embeddings_batch(texts)
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Store in vector database
        await self.vector_store.add_chunks(chunks)
        
        # Update metadata
        self.indexed_files.add(str(file_path))
        self._save_metadata()
        
        return len(chunks)
    
    def _parse_file_to_chunks(self, file_path: Path) -> List[CodeChunk]:
        """Parse a file into semantic chunks.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of code chunks
        """
        chunks = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            # For now, use simple chunking by size
            # TODO: Use AST parsing for better semantic chunking
            chunk_size = 50  # lines per chunk
            overlap = 10  # lines of overlap
            
            for i in range(0, len(lines), chunk_size - overlap):
                chunk_lines = lines[i:i + chunk_size]
                if chunk_lines:
                    chunk = CodeChunk(
                        file_path=str(file_path.relative_to(self.project_path)),
                        content='\n'.join(chunk_lines),
                        start_line=i + 1,
                        end_line=min(i + chunk_size, len(lines)),
                        chunk_type='block',
                        metadata={
                            'language': file_path.suffix[1:] if file_path.suffix else 'text',
                            'file_size': len(content)
                        }
                    )
                    chunks.append(chunk)
        
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
        
        return chunks
    
    def _prepare_chunk_text(self, chunk: CodeChunk) -> str:
        """Prepare chunk text for embedding.
        
        Args:
            chunk: Code chunk
            
        Returns:
            Text prepared for embedding
        """
        # Add context to improve embedding quality
        context = f"File: {chunk.file_path}\n"
        context += f"Lines: {chunk.start_line}-{chunk.end_line}\n"
        context += f"Type: {chunk.chunk_type}\n"
        context += f"Language: {chunk.metadata.get('language', 'unknown')}\n\n"
        context += chunk.content
        
        return context
    
    async def search(
        self,
        query: str,
        k: int = 5,
        file_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for code similar to the query.
        
        Args:
            query: Natural language query
            k: Number of results to return
            file_filter: Optional file path pattern to filter results
            
        Returns:
            List of search results
        """
        # Generate query embedding
        query_embedding = self.embedding_gen.generate_embedding(query)
        
        # Prepare filters
        filters = {}
        if file_filter:
            filters['file_path'] = file_filter
        
        # Search vector store
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            k=k,
            filter_dict=filters if filters else None
        )
        
        # Format results
        formatted_results = []
        for chunk, score in results:
            formatted_results.append({
                'file_path': chunk.file_path,
                'start_line': chunk.start_line,
                'end_line': chunk.end_line,
                'content': chunk.content,
                'score': score,
                'type': chunk.chunk_type,
                'metadata': chunk.metadata
            })
        
        return formatted_results
    
    async def index_project(self, max_files: int = 1000) -> Dict[str, Any]:
        """Index entire project for semantic search.
        
        Args:
            max_files: Maximum number of files to index
            
        Returns:
            Indexing statistics
        """
        logger.info(f"Starting project indexing for {self.project_path}")
        
        # Find all code files
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c'}
        files_to_index = []
        
        for ext in code_extensions:
            files_to_index.extend(self.project_path.rglob(f'*{ext}'))
            if len(files_to_index) >= max_files:
                break
        
        # Limit files
        files_to_index = files_to_index[:max_files]
        
        # Index files in parallel
        total_chunks = 0
        indexed_files = 0
        
        # Batch process for efficiency
        batch_size = 10
        for i in range(0, len(files_to_index), batch_size):
            batch = files_to_index[i:i + batch_size]
            tasks = [self.index_file(file_path) for file_path in batch]
            results = await asyncio.gather(*tasks)
            
            for chunks_count in results:
                if chunks_count > 0:
                    indexed_files += 1
                    total_chunks += chunks_count
        
        stats = {
            'indexed_files': indexed_files,
            'total_chunks': total_chunks,
            'total_files_scanned': len(files_to_index),
            'index_location': str(self.cache_dir)
        }
        
        logger.info(f"Indexing complete: {stats}")
        return stats


class CodeSearchTool:
    """High-level tool for semantic code search."""
    
    def __init__(self, project_path: Path):
        """Initialize code search tool.
        
        Args:
            project_path: Path to project root
        """
        self.engine = SemanticSearchEngine(project_path)
        self.initialized = False
    
    async def initialize(self, auto_index: bool = True) -> None:
        """Initialize the search tool.
        
        Args:
            auto_index: Whether to automatically index the project
        """
        if auto_index and not self.initialized:
            await self.engine.index_project(max_files=500)
            self.initialized = True
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for code.
        
        Args:
            query: Natural language search query
            max_results: Maximum number of results
            
        Returns:
            Search results with relevance scores
        """
        # Ensure initialized
        if not self.initialized:
            await self.initialize()
        
        # Perform search
        results = await self.engine.search(query, k=max_results)
        
        # Enhance results with context
        for result in results:
            result['relevance'] = 'high' if result['score'] > 0.7 else 'medium' if result['score'] > 0.5 else 'low'
            result['preview'] = result['content'][:200] + '...' if len(result['content']) > 200 else result['content']
        
        return results


# Example usage
async def demo_semantic_search():
    """Demonstrate semantic search capabilities."""
    print("🔍 Semantic Search Demo")
    print("=" * 60)
    
    # Initialize search engine
    project_path = Path.cwd()
    search_tool = CodeSearchTool(project_path)
    
    print(f"\nIndexing project: {project_path}")
    await search_tool.initialize()
    
    # Example searches
    queries = [
        "error handling and exception management",
        "parallel execution and concurrency",
        "configuration and settings",
        "file operations and I/O"
    ]
    
    for query in queries:
        print(f"\n📝 Query: '{query}'")
        results = await search_tool.search(query, max_results=3)
        
        for i, result in enumerate(results, 1):
            print(f"\n  Result {i}:")
            print(f"    File: {result['file_path']}")
            print(f"    Lines: {result['start_line']}-{result['end_line']}")
            print(f"    Relevance: {result['relevance']} (score: {result['score']:.3f})")
            print(f"    Preview: {result['preview'][:100]}...")
    
    print("\n✅ Semantic search ready for use!")


if __name__ == "__main__":
    asyncio.run(demo_semantic_search())