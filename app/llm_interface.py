import os
import requests
import json
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class LLMInterface:
    def __init__(self):
        self.llm_host = os.getenv("LLM_HOST")
        self.llm_port = os.getenv("LLM_PORT")
        self.model = os.getenv("LLM_MODEL")
        self.api_base = f"http://{self.llm_host}:{self.llm_port}"
        
    def generate_response(self, prompt, context, temperature=0.7):
        """Generate a response from the LLM."""
        try:
            logger.info("Generating response from LLM")
            
            # Format the prompt with context
            full_prompt = self._format_prompt(prompt, context)
            
            # Make API call to Ollama
            response = requests.post(
                f"{self.api_base}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "temperature": temperature,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Sorry, I couldn't generate a response.")
            else:
                logger.error(f"Error from LLM API: {response.text}")
                return "Sorry, there was an error generating a response."
        except Exception as e:
            logger.error(f"Error calling LLM API: {e}")
            return "Sorry, there was an error communicating with the LLM."
    
    def _format_prompt(self, prompt, context):
        """Format the prompt with context for the LLM."""
        return f"""You are an expert system logs analyzer. Your task is to analyze log data from a topup application and provide clear, accurate answers.

Context (relevant log entries):
{json.dumps(context, indent=2)}

User Question: {prompt}

Based on the logs provided in the context, please answer the user's question. 
If you cannot find the information needed in the logs, say so clearly.
Focus on being precise and factual, citing specific information from the logs.
"""
