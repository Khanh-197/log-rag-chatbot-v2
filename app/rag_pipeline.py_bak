import logging
import os
from dotenv import load_dotenv
from elasticsearch_connector import ElasticsearchConnector
from vector_store import VectorStore
from llm_interface import LLMInterface
import json
import re

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.es_connector = ElasticsearchConnector()
        self.vector_store = VectorStore()
        self.llm = LLMInterface()
        
    def refresh_logs(self, hours_back=24):
        """Refresh logs in the vector store."""
        from datetime import datetime, timedelta
        
        end_time = datetime.now().isoformat()
        start_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        logs = self.es_connector.get_logs_by_time_range(start_time, end_time, size=1000)
        self.vector_store.add_logs(logs)
        
        return len(logs)
    
    def _extract_special_queries(self, query):
        """Extract special queries like transaction IDs."""
        # Check for transaction ID pattern
        transid_match = re.search(r'trans(?:action)?[\s-]?id[:\s]+([a-zA-Z0-9-_]+)', query, re.IGNORECASE)
        if transid_match:
            return {
                "type": "transaction_id",
                "value": transid_match.group(1)
            }
        
        # Check for error logs request
        if re.search(r'error|failed|exception|warning', query, re.IGNORECASE):
            return {
                "type": "error_logs",
                "value": None
            }
        
        # Default to semantic search
        return {
            "type": "semantic",
            "value": query
        }
    
    def process_query(self, query):
        """Process a natural language query and return relevant logs and analysis."""
        # Extract special query types
        special_query = self._extract_special_queries(query)
        
        # Get relevant logs based on query type
        if special_query["type"] == "transaction_id":
            logs = self.es_connector.get_logs_by_transaction_id(special_query["value"])
            if not logs:
                # Fall back to keyword search if exact match fails
                logs = self.es_connector.get_logs_by_keyword(special_query["value"])
        elif special_query["type"] == "error_logs":
            logs = self.es_connector.get_error_logs()
        else:
            # Use vector search for semantic queries
            logs = self.vector_store.query_similar(query)
            
            # Fall back to keyword search if vector search returns no results
            if not logs:
                keywords = query.split()
                for keyword in keywords:
                    if len(keyword) > 3:  # Skip short words
                        logs = self.es_connector.get_logs_by_keyword(keyword)
                        if logs:
                            break
        
        # Generate response using LLM
        if logs:
            response = self.llm.generate_response(query, logs[:10])  # Limit to 10 most relevant logs
        else:
            response = "I couldn't find any relevant logs for your query."
        
        return {
            "query": query,
            "query_type": special_query["type"],
            "logs": logs[:10],  # Return only the top 10 logs
            "analysis": response
        }
