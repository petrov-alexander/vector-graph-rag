import os
import logging
import nest_asyncio
from llama_index.core import SimpleDirectoryReader, PropertyGraphIndex
from llama_index.core.node_parser import CodeSplitter, SentenceSplitter, MarkdownNodeParser
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from llama_index.vector_stores.qdrant import QdrantVectorStore
import qdrant_client

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "gemma4:31b-cloud")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL_NAME = os.getenv("OLLAMA_EMBED_MODEL_NAME", "nomic-embed-text")
OLLAMA_EMBED_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "supersecretpassword")

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "codebase_vectors")

# Mapping of file extensions to CodeSplitter language identifiers
LANGUAGE_MAP = {
    ".py": "python",
    ".go": "go",
    ".js": "javascript",
    ".ts": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
    ".swift": "swift",
    ".kt": "kotlin",
}

# Mapping of file extensions to non-code splitter categories
MARKUP_MAP = {
    ".md": "markdown",
    ".txt": "text",
    ".json": "structured",
    ".yaml": "structured",
    ".yml": "structured",
    ".html": "web",
    ".htm": "web",
    ".css": "web",
    ".scss": "web",
    ".sass": "web",
    ".less": "web",
    ".svg": "text",
}

# Files that should be completely ignored to avoid noise and block explosion
EXCLUDE_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "go.sum",
}

# Directories to ignore
EXCLUDE_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "dist",
    "build",
}


llm = Ollama(
    model=OLLAMA_MODEL_NAME,
    base_url=OLLAMA_BASE_URL,
    request_timeout=300.0,
    is_function_calling_model=True
)

embed_model = OllamaEmbedding(
    model_name=OLLAMA_EMBED_MODEL_NAME,
    base_url=OLLAMA_EMBED_BASE_URL
)

graph_store = Neo4jPropertyGraphStore(
    username=NEO4J_USERNAME,
    password=NEO4J_PASSWORD,
    url=NEO4J_URI,
)

client = qdrant_client.QdrantClient(url=QDRANT_URL)
vector_store = QdrantVectorStore(
    client=client,
    collection_name=QDRANT_COLLECTION
)

logger.info("Reading source code and documentation from /codebase ...")
documents = SimpleDirectoryReader(
    input_dir="/codebase",
    required_exts=list(LANGUAGE_MAP.keys()) + list(MARKUP_MAP.keys()),
    recursive=True,
    exclude=[f"**/{dir_name}/**" for dir_name in EXCLUDE_DIRS]
).load_data()

# Cache for initialized splitters to avoid redundant object creation
splitters_cache = {}

nodes = []
for doc in documents:
    file_name = os.path.basename(doc.metadata["file_name"])
    full_path = doc.metadata["file_name"]

    if file_name in EXCLUDE_FILES:
        continue

    # 1. Try CodeSplitter
    ext = next((e for e in LANGUAGE_MAP if full_path.endswith(e)), None)
    if ext:
        lang = LANGUAGE_MAP[ext]
        if lang not in splitters_cache:
            splitters_cache[lang] = CodeSplitter(language=lang, chunk_lines=100)
        nodes.extend(splitters_cache[lang].get_nodes_from_documents([doc]))
        continue

    # 2. Try Markup/Text Splitter
    ext = next((e for e in MARKUP_MAP if full_path.endswith(e)), None)
    if ext:
        category = MARKUP_MAP[ext]
        if category not in splitters_cache:
            if category == "markdown":
                splitters_cache[category] = MarkdownNodeParser()
            elif category == "web":
                # Use larger chunks for HTML/CSS to reduce block count and keep context
                splitters_cache[category] = SentenceSplitter(chunk_size=4096, chunk_overlap=100)
            elif category == "structured":
                # Structured files can be huge, use larger chunks
                splitters_cache[category] = SentenceSplitter(chunk_size=2048, chunk_overlap=50)
            else: # text
                splitters_cache[category] = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
        nodes.extend(splitters_cache[category].get_nodes_from_documents([doc]))
        continue

    logger.warning(f"No splitter configured for file: {full_path}")

logger.info(f"Extracted {len(nodes)} structural blocks. Starting vector and graph index construction...")

index = PropertyGraphIndex(
    nodes=nodes,
    property_graph_store=graph_store,
    vector_store=vector_store,
    llm=llm,
    embed_model=embed_model,
    show_progress=True,
)
logger.info("Indexing completed successfully!")
