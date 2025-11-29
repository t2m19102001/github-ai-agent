"""
Interactive Web Dashboard for testing GitHub AI Agent features
Provides UI for Code Completion, Test Generation, and PR Analysis
"""

from flask import Blueprint, render_template, jsonify

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/')
def index():
    """Display the interactive dashboard."""
    return render_template('dashboard.html')


@dashboard_bp.route('/stats')
def stats():
    """Get system statistics."""
    return jsonify({
        'status': 'operational',
        'agents': 4,
        'endpoints': 10,
        'test_pass_rate': 0.96,
        'components': {
            'pr_analysis': 'active',
            'code_completion': 'active',
            'test_generation': 'active',
            'base_framework': 'active'
        }
    })


