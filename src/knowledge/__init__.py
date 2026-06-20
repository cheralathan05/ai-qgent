"""
Knowledge Intelligence Layer - Phase 3
Document ingestion, embedding, search, and retrieval
"""

from .source_connectors import (
    KnowledgeSourceConnector, LocalFileConnector, GitHubConnector,
    GoogleDriveConnector, NotionConnector, SlackConnector,
    get_source_connector, get_all_connectors,
)
from .parsers import (
    DocumentParser, PDFParser, DOCXParser, TXTParser, MDParser,
    CSVParser, XLSXParser, PPTXParser, JSONParser, XMLParser,
    HTMLParser, CodeParser, get_parser_for_file,
)
from .document_ingestion import (
    DocumentIngestionPipeline, IngestionResult,
    get_ingestion_pipeline,
)
from .embedding_engine import (
    EmbeddingEngine, BGEEmbedding, NomicEmbedding, E5Embedding,
    SentenceTransformerEmbedding, OllamaEmbedding,
    get_embedding_engine,
)
from .vector_store import (
    VectorStore, ChromaStore, FAISSStore, QdrantStore, PgvectorStore,
    get_vector_store,
)
from .search_engine import (
    SearchEngine, HybridSearch, VectorSearch, KeywordSearch,
    FuzzySearch, BM25Search, MetadataSearch,
    SearchResult, SearchResponse,
    get_search_engine,
)
from .retriever import DocumentRetriever, get_document_retriever
from .indexer import IndexManager, get_index_manager
