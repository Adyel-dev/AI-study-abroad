"""
Unified AI Client Service
Primary: OpenRouter (meta-llama/llama-3.3-70b-instruct:free)
Fallback: OpenAI (gpt-4o-mini)
"""
import openai
import requests
import logging
from typing import List, Dict, Any, Optional
from config import Config
import httpx

logger = logging.getLogger(__name__)

# Cache for clients
_openrouter_client = None
_openai_client = None

def get_openrouter_client():
    """Get OpenRouter client instance"""
    global _openrouter_client
    if _openrouter_client is None:
        # Create httpx client without proxies to avoid compatibility issues
        http_client = httpx.Client(timeout=60.0)
        _openrouter_client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.OPENROUTER_API_KEY,
            http_client=http_client
        )
    return _openrouter_client

def get_openai_client():
    """Get OpenAI client instance (fallback)"""
    global _openai_client
    if _openai_client is None:
        # Create httpx client without proxies to avoid compatibility issues
        http_client = httpx.Client(timeout=60.0)
        _openai_client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            http_client=http_client
        )
    return _openai_client

def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    **kwargs
) -> Dict[str, Any]:
    """
    Unified chat completion function
    Tries OpenRouter first, falls back to OpenAI if it fails
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model to use (None = use default from config)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        **kwargs: Additional arguments to pass to the API
    
    Returns:
        Dict with 'content' (response text) and 'provider' (openrouter/openai)
    
    Raises:
        Exception: If both providers fail
    """
    # Use OpenRouter model if not specified
    if model is None:
        model = Config.OPENROUTER_MODEL
    
    # Try OpenRouter first (primary)
    if Config.OPENROUTER_API_KEY:
        try:
            logger.debug(f"Attempting chat completion with OpenRouter (model: {model})")
            client = get_openrouter_client()
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            logger.debug("Successfully got response from OpenRouter")
            
            return {
                'content': content,
                'provider': 'openrouter',
                'model': model,
                'full_response': response
            }
        
        except Exception as e:
            logger.warning(f"OpenRouter request failed: {e}. Falling back to OpenAI.")
            # Fall through to OpenAI fallback
    
    # Fallback to OpenAI
    if Config.OPENAI_API_KEY:
        try:
            # Use OpenAI model for fallback
            openai_model = kwargs.pop('fallback_model', Config.OPENAI_MODEL)
            
            logger.debug(f"Attempting chat completion with OpenAI (model: {openai_model})")
            client = get_openai_client()
            
            response = client.chat.completions.create(
                model=openai_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            logger.debug("Successfully got response from OpenAI")
            
            return {
                'content': content,
                'provider': 'openai',
                'model': openai_model,
                'full_response': response
            }
        
        except Exception as e:
            logger.error(f"OpenAI fallback also failed: {e}")
            raise Exception(f"Both OpenRouter and OpenAI failed. Last error: {e}")
    
    raise Exception("No AI provider configured. Set OPENROUTER_API_KEY or OPENAI_API_KEY in environment variables.")

def embed_text_openai(text: str) -> List[float]:
    """
    Generate embeddings using OpenAI (OpenRouter doesn't support embeddings)
    This is kept separate since embeddings must use OpenAI
    
    Args:
        text: Text to embed
    
    Returns:
        List of float values representing the embedding
    """
    if not Config.OPENAI_API_KEY:
        raise Exception("OpenAI API key required for embeddings. OpenRouter does not support embeddings.")
    
    try:
        client = get_openai_client()
        response = client.embeddings.create(
            model=Config.OPENAI_EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise

