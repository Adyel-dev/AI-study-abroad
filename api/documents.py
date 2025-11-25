"""
Documents API endpoints
Handles document upload, retrieval, and deletion
"""
from flask import Blueprint, request, jsonify, send_from_directory
from models.mongo import get_db
from utils.auth import get_user_id
from config import Config
from werkzeug.utils import secure_filename
from bson import ObjectId
from datetime import datetime
import os
import logging

bp = Blueprint('documents', __name__)
logger = logging.getLogger(__name__)

ALLOWED_DOCUMENT_TYPES = ['transcript', 'degree_certificate', 'language_certificate', 'CV', 'SOP', 'other']

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@bp.route('/documents', methods=['POST'])
def upload_document():
    """
    POST /api/documents
    Upload a document (multipart/form-data)
    
    Form fields:
    - file: the file to upload
    - document_type: type of document (transcript, degree_certificate, etc.)
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        # Check file in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided', 'code': 'NO_FILE'}), 400
        
        file = request.files['file']
        document_type = request.form.get('document_type', 'other')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected', 'code': 'NO_FILE'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': f'File type not allowed. Allowed: {", ".join(Config.ALLOWED_EXTENSIONS)}',
                'code': 'INVALID_FILE_TYPE'
            }), 400
        
        if document_type not in ALLOWED_DOCUMENT_TYPES:
            return jsonify({
                'error': f'Invalid document type. Allowed: {", ".join(ALLOWED_DOCUMENT_TYPES)}',
                'code': 'INVALID_DOCUMENT_TYPE'
            }), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > Config.MAX_CONTENT_LENGTH:
            return jsonify({
                'error': f'File too large. Maximum size: {Config.MAX_CONTENT_LENGTH / (1024*1024):.1f}MB',
                'code': 'FILE_TOO_LARGE'
            }), 400
        
        # Check user's document count
        db = get_db()
        existing_count = db.documents.count_documents({'user_id': user_id})
        max_documents = 10
        
        if existing_count >= max_documents:
            return jsonify({
                'error': f'Maximum {max_documents} documents allowed per user',
                'code': 'MAX_DOCUMENTS'
            }), 400
        
        # Create user upload directory
        user_upload_dir = os.path.join(Config.UPLOAD_FOLDER, user_id)
        os.makedirs(user_upload_dir, exist_ok=True)
        
        # Generate secure filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{user_id[:8]}.{file_ext}"
        file_path = os.path.join(user_upload_dir, stored_filename)
        
        # Save file
        file.save(file_path)
        
        # Extract text snippet (basic - can be enhanced with OCR/PDF parsing)
        extracted_text_snippet = None
        has_text_extracted = False
        
        try:
            if file_ext == 'pdf':
                # Placeholder for PDF text extraction
                extracted_text_snippet = "PDF text extraction not implemented yet"
                has_text_extracted = False
            elif file_ext in ['txt', 'docx']:
                # Basic text extraction for text files
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)  # First 500 chars
                    if content:
                        extracted_text_snippet = content[:200]  # First 200 chars
                        has_text_extracted = True
        except Exception as e:
            logger.warning(f"Could not extract text from file: {e}")
        
        # Save document metadata to database
        document_doc = {
            'user_id': user_id,
            'document_type': document_type,
            'original_filename': original_filename,
            'stored_filename': stored_filename,
            'content_type': file.content_type or f'application/{file_ext}',
            'size_bytes': file_size,
            'storage_path': file_path,
            'has_text_extracted': has_text_extracted,
            'extracted_text_snippet': extracted_text_snippet,
            'uploaded_at': datetime.utcnow()
        }
        
        result = db.documents.insert_one(document_doc)
        document_doc['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Document uploaded successfully',
            'document': document_doc
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/documents', methods=['GET'])
def list_documents():
    """
    GET /api/documents
    List all documents for current user
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        db = get_db()
        documents = list(db.documents.find(
            {'user_id': user_id}
        ).sort('uploaded_at', -1))
        
        # Convert ObjectId to string and remove storage_path for security
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            doc.pop('storage_path', None)  # Don't expose full path
        
        return jsonify({'documents': documents}), 200
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/documents/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """
    DELETE /api/documents/<id>
    Delete a document (only if owned by current user)
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        if not ObjectId.is_valid(document_id):
            return jsonify({'error': 'Invalid document ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        document = db.documents.find_one({
            '_id': ObjectId(document_id),
            'user_id': user_id
        })
        
        if not document:
            return jsonify({'error': 'Document not found', 'code': 'NOT_FOUND'}), 404
        
        # Delete file from disk
        try:
            if document.get('storage_path') and os.path.exists(document['storage_path']):
                os.remove(document['storage_path'])
        except Exception as e:
            logger.warning(f"Could not delete file {document.get('storage_path')}: {e}")
        
        # Delete from database
        db.documents.delete_one({'_id': ObjectId(document_id)})
        
        return jsonify({'message': 'Document deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

@bp.route('/documents/<document_id>/download', methods=['GET'])
def download_document(document_id):
    """
    GET /api/documents/<id>/download
    Download a document (only if owned by current user)
    """
    try:
        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'User not authenticated', 'code': 'AUTH_REQUIRED'}), 401
        
        if not ObjectId.is_valid(document_id):
            return jsonify({'error': 'Invalid document ID', 'code': 'INVALID_ID'}), 400
        
        db = get_db()
        document = db.documents.find_one({
            '_id': ObjectId(document_id),
            'user_id': user_id
        })
        
        if not document:
            return jsonify({'error': 'Document not found', 'code': 'NOT_FOUND'}), 404
        
        if not document.get('storage_path') or not os.path.exists(document['storage_path']):
            return jsonify({'error': 'File not found on disk', 'code': 'FILE_NOT_FOUND'}), 404
        
        # Send file
        directory = os.path.dirname(document['storage_path'])
        filename = os.path.basename(document['storage_path'])
        return send_from_directory(
            directory,
            filename,
            as_attachment=True,
            download_name=document['original_filename']
        )
        
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        return jsonify({'error': str(e), 'code': 'SERVER_ERROR'}), 500

