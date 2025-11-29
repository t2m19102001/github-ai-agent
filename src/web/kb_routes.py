#!/usr/bin/env python3
"""
Knowledge Management API Endpoints
Cho phép thêm, cập nhật, tìm kiếm kiến thức
"""

from flask import Blueprint, request, jsonify
from src.agents.knowledge_base import get_knowledge_base
from src.utils.logger import get_logger

logger = get_logger(__name__)

kb_bp = Blueprint('knowledge', __name__, url_prefix='/api/knowledge')


@kb_bp.route('/stats', methods=['GET'])
def get_kb_stats():
    """Get knowledge base statistics"""
    kb = get_knowledge_base()
    stats = kb.get_stats()
    return jsonify({
        "status": "success",
        "data": stats
    })


@kb_bp.route('/search', methods=['GET'])
def search_knowledge():
    """Search knowledge base"""
    query = request.args.get('q', '')
    category = request.args.get('category')
    top_k = int(request.args.get('top_k', 5))
    
    if not query:
        return jsonify({"status": "error", "message": "Query required"}), 400
    
    kb = get_knowledge_base()
    results = kb.search(query, category=category, top_k=top_k)
    
    return jsonify({
        "status": "success",
        "query": query,
        "results": [
            {
                "id": item.id,
                "title": item.title,
                "category": item.category,
                "topic": item.topic,
                "tags": item.tags,
                "score": score,
                "usage_count": item.usage_count,
                "preview": item.content[:200] + "..." if len(item.content) > 200 else item.content
            }
            for item, score in results
        ]
    })


@kb_bp.route('/get/<item_id>', methods=['GET'])
def get_knowledge_item(item_id):
    """Get full knowledge item"""
    kb = get_knowledge_base()
    
    if item_id not in kb.knowledge_items:
        return jsonify({"status": "error", "message": "Item not found"}), 404
    
    item = kb.knowledge_items[item_id]
    kb.increment_usage(item_id)
    
    return jsonify({
        "status": "success",
        "item": item.to_dict()
    })


@kb_bp.route('/add', methods=['POST'])
def add_knowledge():
    """Add new knowledge item"""
    data = request.get_json()
    
    # Validate input
    required_fields = ['category', 'topic', 'title', 'content', 'tags', 'source']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({
                "status": "error",
                "message": f"Missing required field: {field}"
            }), 400
    
    try:
        kb = get_knowledge_base()
        item_id = kb.add_item(
            category=data['category'],
            topic=data['topic'],
            title=data['title'],
            content=data['content'],
            tags=data['tags'] if isinstance(data['tags'], list) else [data['tags']],
            source=data.get('source', 'user_input')
        )
        kb.save()
        
        return jsonify({
            "status": "success",
            "message": "Knowledge item added",
            "item_id": item_id
        }), 201
    
    except Exception as e:
        logger.error(f"Error adding knowledge: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@kb_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all knowledge categories"""
    kb = get_knowledge_base()
    
    categories = {}
    for category, items in kb.category_index.items():
        categories[category] = {
            "count": len(items),
            "items": [
                {
                    "id": kb.knowledge_items[item_id].id,
                    "title": kb.knowledge_items[item_id].title,
                    "topic": kb.knowledge_items[item_id].topic
                }
                for item_id in items
            ]
        }
    
    return jsonify({
        "status": "success",
        "categories": categories
    })


@kb_bp.route('/category/<category>', methods=['GET'])
def get_category_items(category):
    """Get all items in a category"""
    kb = get_knowledge_base()
    items = kb.get_by_category(category)
    
    return jsonify({
        "status": "success",
        "category": category,
        "items": [item.to_dict() for item in items]
    })


@kb_bp.route('/tags', methods=['GET'])
def get_tags():
    """Get all tags"""
    kb = get_knowledge_base()
    
    tags = {}
    for tag, items in kb.tag_index.items():
        tags[tag] = len(items)
    
    return jsonify({
        "status": "success",
        "tags": tags,
        "total_tags": len(tags)
    })
