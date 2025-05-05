import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging
import requests
import time
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        self.chroma_host = os.getenv("CHROMA_HOST")
        self.chroma_port = os.getenv("CHROMA_PORT")
        self.collection_name = os.getenv("CHROMA_COLLECTION")
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.tenant = os.getenv("CHROMA_TENANT", "default_tenant")
        self.database = os.getenv("CHROMA_DATABASE", "default_database")
        self.use_local = os.getenv("CHROMA_USE_LOCAL", "false").lower() == "true"
        
        self.client = self._connect()
        self.collection = self._get_or_create_collection()
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None
        
    def _connect(self):
        """Connect to ChromaDB."""
        try:
            # Kiểm tra cấu hình
            if self.use_local:
                logger.info("Using local ChromaDB client as configured in .env")
                # Cấu hình client cục bộ
                persist_dir = "/app/chroma_db"
                os.makedirs(persist_dir, exist_ok=True)
                
                client = chromadb.Client(Settings(
                    allow_reset=True,
                    anonymized_telemetry=False,
                    is_persistent=True,
                    persist_directory=persist_dir
                ))
                logger.info("Successfully created local ChromaDB client")
                return client
            else:
                # Kết nối qua HTTP
                logger.info(f"Attempting to connect to ChromaDB at {self.chroma_host}:{self.chroma_port}")
                
                # Thử ping trước để kiểm tra kết nối
                max_retries = 5
                retry_delay = 5  # giây
                
                for attempt in range(max_retries):
                    try:
                        # Thử cả API v1 và v2
                        v1_url = f"http://{self.chroma_host}:{self.chroma_port}/api/v1/heartbeat"
                        v2_url = f"http://{self.chroma_host}:{self.chroma_port}/api/v2/heartbeat"
                        
                        try:
                            response = requests.get(v1_url, timeout=5)
                            logger.info(f"ChromaDB v1 heartbeat response: {response.status_code}")
                            if response.status_code == 200:
                                break
                        except Exception as e_v1:
                            logger.warning(f"V1 API check failed: {e_v1}")
                            
                        try:
                            response = requests.get(v2_url, timeout=5)
                            logger.info(f"ChromaDB v2 heartbeat response: {response.status_code}")
                            if response.status_code == 200:
                                break
                        except Exception as e_v2:
                            logger.warning(f"V2 API check failed: {e_v2}")
                    
                    except Exception as e:
                        logger.warning(f"Attempt {attempt+1}/{max_retries}: Could not reach ChromaDB: {e}")
                        
                    if attempt < max_retries - 1:
                        logger.info(f"Waiting {retry_delay} seconds before retrying...")
                        time.sleep(retry_delay)
                
                # Sau khi thử kết nối, tạo client HTTP
                try:
                    # Tạo settings cơ bản (không có tenant/database)
                    settings = Settings(
                        allow_reset=True,
                        anonymized_telemetry=False
                    )
                    
                    # Thử tạo client với tenant/database nếu HTTP client hỗ trợ
                    try:
                        client = chromadb.HttpClient(
                            host=self.chroma_host,
                            port=int(self.chroma_port),
                            settings=settings,
                            tenant=self.tenant,
                            database=self.database
                        )
                        # Kiểm tra kết nối
                        collections = client.list_collections()
                        logger.info(f"Successfully connected to ChromaDB v2 with tenant/database. Found {len(collections)} collections.")
                        return client
                    except TypeError as te:
                        # Nếu không hỗ trợ tenant/database trong constructor
                        if "unexpected keyword argument" in str(te):
                            logger.warning("ChromaDB client doesn't support tenant/database parameters in constructor")
                            client = chromadb.HttpClient(
                                host=self.chroma_host,
                                port=int(self.chroma_port),
                                settings=settings
                            )
                            # Kiểm tra kết nối
                            collections = client.list_collections()
                            logger.info(f"Successfully connected to ChromaDB without tenant/database. Found {len(collections)} collections.")
                            return client
                        else:
                            raise
                    except Exception as client_error:
                        logger.error(f"Error creating ChromaDB client: {client_error}")
                        # Thử phiên bản đơn giản nhất
                        logger.info("Attempting to create simple HTTP client")
                        client = chromadb.HttpClient(
                            host=self.chroma_host,
                            port=int(self.chroma_port)
                        )
                        # Kiểm tra kết nối
                        collections = client.list_collections()
                        logger.info(f"Successfully connected to ChromaDB with simple config. Found {len(collections)} collections.")
                        return client
                        
                except Exception as http_error:
                    logger.error(f"Error creating ChromaDB HTTP client: {http_error}")
                    
                    # Fallback sang local client nếu HTTP thất bại
                    logger.info("Falling back to local ChromaDB client due to HTTP connection failure")
                    persist_dir = "/app/chroma_db"
                    os.makedirs(persist_dir, exist_ok=True)
                    
                    client = chromadb.Client(Settings(
                        allow_reset=True,
                        anonymized_telemetry=False,
                        is_persistent=True,
                        persist_directory=persist_dir
                    ))
                    logger.info("Created local ChromaDB client as fallback")
                    return client
                    
        except Exception as e:
            logger.error(f"Error connecting to ChromaDB: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            # Cuối cùng, thử tạo local client
            try:
                logger.info("Attempting to create local ChromaDB client as final fallback")
                persist_dir = "/app/chroma_db"
                os.makedirs(persist_dir, exist_ok=True)
                
                client = chromadb.Client(Settings(
                    allow_reset=True,
                    anonymized_telemetry=False,
                    is_persistent=True,
                    persist_directory=persist_dir
                ))
                logger.info("Created local ChromaDB client as final fallback")
                return client
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback local client: {fallback_error}")
                return None
    
    def _get_or_create_collection(self):
        """Get or create a collection in ChromaDB."""
        if not self.client:
            logger.error("ChromaDB client not connected")
            return None
        
        try:
            try:
                collections = self.client.list_collections()
                collection_names = [c.name for c in collections]
                
                if self.collection_name in collection_names:
                    collection = self.client.get_collection(self.collection_name)
                    logger.info(f"Using existing collection: {self.collection_name}")
                    return collection
            except Exception as e:
                logger.warning(f"Error listing collections: {e}, trying to create new collection")
            
            # Tạo collection mới
            try:
                # Phiên bản cơ bản nhất
                collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Logs collection for RAG"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
                return collection
            except TypeError as te:
                if "missing 1 required positional argument: 'embedding_function'" in str(te):
                    logger.info("Creating collection with default embedding function")
                    
                    # Tạo một hàm embedding đơn giản nếu cần
                    def dummy_embedding_function(texts):
                        return [[0.0] * 768 for _ in texts]
                    
                    collection = self.client.create_collection(
                        name=self.collection_name,
                        embedding_function=dummy_embedding_function,
                        metadata={"description": "Logs collection for RAG"}
                    )
                    logger.info(f"Created new collection with dummy embedding function: {self.collection_name}")
                    return collection
                else:
                    raise
        except Exception as e:
            logger.error(f"Error getting or creating collection: {e}")
            return None
    
    def generate_embedding(self, text):
        """Generate embedding for a text."""
        if self.embedding_model is None:
            logger.error("Embedding model not initialized")
            return [0.0] * 384  # Return zero vector as fallback
        
        try:
            return self.embedding_model.encode(text).tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * 384  # Return zero vector as fallback
    
    def add_logs(self, logs):
        """Add logs to the vector store."""
        if not self.collection:
            logger.error("ChromaDB collection not available")
            return
        
        if not logs:
            logger.warning("No logs to add to vector store")
            return
        
        try:
            ids = []
            documents = []
            metadatas = []
            
            for log in logs:
                try:
                    # Create a unique ID
                    log_id = str(hash(frozenset([(k, str(v)) for k, v in log.items() if v is not None])))
                    ids.append(log_id)
                    
                    # Create a text representation of the log
                    log_text = self._log_to_text(log)
                    documents.append(log_text)
                    
                    # Store original log as metadata
                    # Convert non-supported types to strings
                    metadata = {}
                    for k, v in log.items():
                        if v is None:
                            metadata[k] = ""
                        elif isinstance(v, (str, int, float, bool)):
                            metadata[k] = v
                        elif isinstance(v, list) and all(isinstance(i, (str, int, float, bool, type(None))) for i in v):
                            metadata[k] = str(v)
                        elif isinstance(v, dict):
                            metadata[k] = str(v)
                        else:
                            metadata[k] = str(v)
                    
                    metadatas.append(metadata)
                except Exception as e:
                    logger.error(f"Error processing log: {e}")
                    logger.debug(f"Problematic log: {log}")
                    continue
            
            if not ids:
                logger.warning("No valid logs to add after processing")
                return
            
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"Added {len(ids)} logs to vector store")
        except Exception as e:
            logger.error(f"Error adding logs to vector store: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _log_to_text(self, log):
        """Convert a log dict to a text representation."""
        try:
            text_parts = []
            
            # Priority fields that should come first
            priority_fields = ["@timestamp", "message", "log", "details", "transid", "level", "service"]
            
            # Add priority fields first
            for field in priority_fields:
                if field in log and log[field]:
                    text_parts.append(f"{field}: {log[field]}")
            
            # Add remaining fields
            for key, value in log.items():
                if key not in priority_fields and value:
                    text_parts.append(f"{key}: {value}")
            
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error converting log to text: {e}")
            return str(log)  # Fallback to string representation
    
    def query_similar(self, query_text, n_results=5):
        """Query for similar logs."""
        if not self.collection:
            logger.error("ChromaDB collection not available")
            return []
        
        try:
            # Kiểm tra xem collection có dữ liệu không
            count = self.collection.count()
            if count == 0:
                logger.warning("Collection is empty, no results to return")
                return []
            
            # Đảm bảo n_results không lớn hơn số lượng tài liệu trong collection
            n_results = min(n_results, count)
            
            # Thực hiện truy vấn
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            # Kiểm tra và xử lý kết quả
            if not results or "metadatas" not in results or not results["metadatas"]:
                logger.warning(f"No results found for query: {query_text}")
                return []
            
            return results.get("metadatas", [[]])[0]
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            logger.error(f"Query: {query_text}")
            import traceback
            logger.error(traceback.format_exc())
            return []
