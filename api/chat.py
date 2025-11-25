"""
Chat API endpoint
Simple Q&A interface with RAG
"""
from flask import Blueprint, request, jsonify
from services.embeddings import search_similar
from services.ai_client import chat_completion
from config import Config
import logging

bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

@bp.route('/chat', methods=['POST'])
def chat():
    """
    POST /api/chat
    Simple Q&A chat with RAG
    
    Request body:
    - message: user's question
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message required', 'code': 'MISSING_MESSAGE'}), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty', 'code': 'EMPTY_MESSAGE'}), 400
        
        # Search for relevant context using RAG
        context_docs = []
        sources = []
        
        # Search across different collections
        for collection_name in ['universities', 'programmes', 'immigration_rules']:
            similar_docs = search_similar(user_message, collection_name, limit=3)
            context_docs.extend(similar_docs)
            
            # Collect sources
            for doc in similar_docs:
                if collection_name == 'universities':
                    source = {
                        'title': doc.get('name', 'University'),
                        'url': doc.get('web_pages', [None])[0]
                    }
                elif collection_name == 'programmes':
                    source = {
                        'title': doc.get('title', 'Programme'),
                        'url': doc.get('source_url')
                    }
                elif collection_name == 'immigration_rules':
                    source = {
                        'title': doc.get('visa_type', 'Immigration Rule'),
                        'url': doc.get('source_urls', [None])[0]
                    }
                
                if source and source not in sources:
                    sources.append(source)
        
        # Build context from retrieved documents
        context_parts = []
        if context_docs:
            context_parts.append("Relevant information:")
            for doc in context_docs[:5]:  # Limit to top 5
                if 'universities' in str(doc.get('_id', '')) or doc.get('name'):
                    context_parts.append(f"University: {doc.get('name')} - {doc.get('state-province', '')}")
                elif doc.get('title'):
                    context_parts.append(f"Programme: {doc.get('title')} at {doc.get('university_name', '')}")
                elif doc.get('visa_type'):
                    context_parts.append(f"Visa: {doc.get('visa_type')}")
        
        context = "\n".join(context_parts)
        
        # Build system prompt
        system_prompt = """You are a helpful assistant for students who want to study in Germany. 
Answer questions based on the provided context. If the question is about immigration or visas, 
always add a disclaimer: "This is informational only and not legal advice. Always confirm with official embassies/authorities."
If you don't know the answer based on the context, say so. Be helpful and concise."""
        
        # Prepare messages for OpenAI
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {user_message}"
            })
        else:
            messages.append({"role": "user", "content": user_message})
        
        # Call AI API (OpenRouter primary, OpenAI fallback)
        try:
            ai_response = chat_completion(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            answer = ai_response['content']
            logger.debug(f"Chat response from {ai_response['provider']} using {ai_response['model']}")
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            answer = "I apologize, but I'm having trouble processing your request right now. Please try again later."
            raise
        
        return jsonify({
            'answer': answer,
            'sources': sources
        }), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

