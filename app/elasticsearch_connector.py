import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import logging
import requests
from requests.auth import HTTPBasicAuth
import json

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class ElasticsearchConnector:
    def __init__(self):
        self.es_host = os.getenv("ES_HOST")
        self.es_port = os.getenv("ES_PORT")
        self.es_username = os.getenv("ES_USERNAME")
        self.es_password = os.getenv("ES_PASSWORD")
        self.es_index = os.getenv("ES_INDEX")
        
        self.client = self._connect()
        
    def _connect(self):
        """Establish connection to Elasticsearch."""
        try:
            # Loại bỏ protocol nếu có
            es_host = self.es_host
            if es_host.startswith('http://'):
                es_host = es_host[7:]
            elif es_host.startswith('https://'):
                es_host = es_host[8:]
            
            logger.info(f"Attempting to connect to Elasticsearch at {es_host}:{self.es_port}")
            
            # Thử kiểm tra kết nối trực tiếp với requests trước
            try:
                response = requests.get(
                    f"http://{es_host}:{self.es_port}",
                    auth=HTTPBasicAuth(self.es_username, self.es_password),
                    timeout=10
                )
                logger.info(f"Direct request to Elasticsearch: status={response.status_code}, response={response.text[:100]}")
            except Exception as req_error:
                logger.error(f"Direct request to Elasticsearch failed: {req_error}")
            
            # Tạo client Elasticsearch với nhiều tùy chọn khác nhau
            client = Elasticsearch(
                f"http://{es_host}:{self.es_port}",
                basic_auth=(self.es_username, self.es_password),
                verify_certs=False,
                request_timeout=30,
                retry_on_timeout=True,
                max_retries=3
            )
            
            # Kiểm tra kết nối
            logger.info("Attempting to ping Elasticsearch")
            is_connected = client.ping()
            logger.info(f"Elasticsearch ping result: {is_connected}")
            
            if is_connected:
                logger.info("Successfully connected to Elasticsearch")
                
                # Kiểm tra index
                try:
                    index_exists = client.indices.exists(index=self.es_index)
                    logger.info(f"Index '{self.es_index}' exists: {index_exists}")
                except Exception as idx_error:
                    logger.warning(f"Could not check if index exists: {idx_error}")
                
                return client
            else:
                logger.error("Elasticsearch ping failed")
                return None
        except Exception as e:
            logger.error(f"Error connecting to Elasticsearch: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return None
    
    def query_logs(self, query_dict, size=100):
        """Query logs from Elasticsearch using a query dictionary."""
        if not self.client:
            logger.error("Elasticsearch client not connected")
            return []
        
        try:
            logger.info(f"Querying Elasticsearch with: {json.dumps(query_dict)[:200]}...")
            
            response = self.client.search(
                index=self.es_index,
                body=query_dict,
                size=size,
                request_timeout=30
            )
            
            hits = response.get('hits', {}).get('hits', [])
            logger.info(f"Retrieved {len(hits)} logs from Elasticsearch")
            return [hit['_source'] for hit in hits]
        except Exception as e:
            logger.error(f"Error querying Elasticsearch: {e}")
            return []
    
    def get_logs_by_time_range(self, start_time, end_time, size=100):
        """Get logs within a specific time range."""
        query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": start_time,
                        "lte": end_time
                    }
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        return self.query_logs(query, size)
    
    def get_logs_by_transaction_id(self, transaction_id):
        """Get logs for a specific transaction ID."""
        query = {
            "query": {
                "match": {
                    "transid": transaction_id
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        return self.query_logs(query)
    
    def get_logs_by_keyword(self, keyword, size=100):
        """Get logs containing a specific keyword."""
        query = {
            "query": {
                "multi_match": {
                    "query": keyword,
                    "fields": ["message", "log", "details"]
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        return self.query_logs(query, size)
    
    def get_error_logs(self, size=100):
        """Get error logs."""
        query = {
            "query": {
                "bool": {
                    "should": [
                        {"match": {"level": "ERROR"}},
                        {"match": {"severity": "ERROR"}},
                        {"match": {"message": "error"}}
                    ]
                }
            },
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        return self.query_logs(query, size)
