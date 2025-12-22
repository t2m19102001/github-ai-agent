#!/usr/bin/env python3
"""
Flask Web Interface for Code Chat Assistant
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from code_chat import CodeChatAssistant
import logging

load_dotenv()

app = Flask(__name__)
CORS(app)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize assistant
assistant = CodeChatAssistant()

@app.route('/')
def index():
    """Serve chat interface"""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        include_context = data.get('include_context', True)
        
        if not message:
            return jsonify({'error': 'Message required'}), 400
        
        response = assistant.chat(message, include_context)
        
        return jsonify({
            'response': response,
            'status': 'success'
        })
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    """Get list of project files"""
    try:
        files = assistant.get_file_list()
        return jsonify({
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/read', methods=['POST'])
def read_file():
    """Read a specific file"""
    try:
        data = request.json
        file_path = data.get('file', '').strip()
        
        if not file_path:
            return jsonify({'error': 'File path required'}), 400
        
        content = assistant.read_file(file_path)
        
        if content is None:
            return jsonify({'error': 'File not found'}), 404
        
        return jsonify({
            'file': file_path,
            'content': content,
            'lines': len(content.split('\n'))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/context', methods=['GET'])
def get_context():
    """Get code context"""
    try:
        context = assistant.build_context()
        return jsonify({
            'context': context,
            'files_included': len(assistant.project_files[:5])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get conversation history"""
    try:
        return jsonify({
            'history': assistant.conversation_history,
            'count': len(assistant.conversation_history)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    try:
        assistant.conversation_history = []
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('CHAT_PORT', 5000))
    print(f"\n🚀 Code Chat Server running on http://localhost:{port}")
    print("="*70)
    app.run(debug=True, port=port, host='0.0.0.0')
