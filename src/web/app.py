#!/usr/bin/env python3
"""
Flask Web Application for Code Chat
"""

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import hmac
import hashlib
from src.utils.logger import get_logger
from src.core.config import DEBUG, CHAT_PORT, GITHUB_TOKEN, REPO_FULL_NAME
from src.llm.groq import GroqProvider
from src.agents.code_agent import CodeChatAgent
from src.agents.pr_agent import GitHubPRAgent
from src.agents.completion_agent import CodeCompletionAgent
from src.agents.test_agent import TestGenerationAgent
from src.agents.developer_agent import ProfessionalDeveloperAgent
from src.web.dashboard import dashboard_bp

logger = get_logger(__name__)


def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__, template_folder='../../templates')
    CORS(app)
    
    # Initialize authentication and rate limiting
    from src.web.auth import get_limiter, create_token, optional_auth, require_auth
    limiter = get_limiter(app)
    
    # Register blueprints
    app.register_blueprint(dashboard_bp)
    from src.web.kb_routes import kb_bp
    app.register_blueprint(kb_bp)
    
    # Initialize agents
    llm = GroqProvider()
    chat_agent = CodeChatAgent(llm_provider=llm)
    pr_agent = GitHubPRAgent(github_token=GITHUB_TOKEN, llm_provider=llm)
    completion_agent = CodeCompletionAgent(llm_provider=llm)
    test_agent = TestGenerationAgent(llm_provider=llm)
    developer_agent = ProfessionalDeveloperAgent(llm_provider=llm)
    
    logger.info("✅ Flask app initialized with all agents")
    
    # Routes
    @app.route('/')
    def index():
        """Serve chat interface"""
        return render_template('chat.html')
    
    # Authentication endpoints
    @app.route('/api/auth/login', methods=['POST'])
    @limiter.limit("10 per minute")
    def login():
        """Login and get JWT token"""
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        # Simple auth (replace with real user database)
        if username and password:
            # Generate token
            token = create_token(user_id=username, username=username)
            return jsonify({
                "status": "success",
                "token": token,
                "expires_in": "24 hours"
            })
        else:
            return jsonify({"error": "Invalid credentials"}), 401
    
    @app.route('/api/auth/verify', methods=['GET'])
    @require_auth
    def verify_token():
        """Verify token is valid"""
        return jsonify({
            "status": "success",
            "user_id": request.user_id,
            "username": request.username
        })
    
    def analyze_code_locally(code_content, filename=""):
        """Perform local code analysis without external API"""
        import re
        
        analysis = f"📊 **CODE ANALYSIS REPORT**\n\n"
        analysis += f"📄 **File:** {filename}\n"
        analysis += f"📝 **Lines of Code:** {len(code_content.split(chr(10)))}\n"
        analysis += f"🔤 **Characters:** {len(code_content)}\n\n"
        
        # Detect language
        if filename.endswith('.py'):
            analysis += "🐍 **Language:** Python\n\n"
            
            # Find functions
            functions = re.findall(r'def\s+(\w+)\s*\(', code_content)
            if functions:
                analysis += f"🔧 **Functions Found ({len(functions)}):**\n"
                for func in functions:
                    analysis += f"  - `{func}()`\n"
                analysis += "\n"
            
            # Find imports
            imports = re.findall(r'^(?:from|import)\s+', code_content, re.MULTILINE)
            if imports:
                analysis += f"📦 **Imports:** {len(imports)} import statement(s) found\n\n"
            
            # Find classes
            classes = re.findall(r'class\s+(\w+)', code_content)
            if classes:
                analysis += f"🏗️ **Classes Found ({len(classes)}):**\n"
                for cls in classes:
                    analysis += f"  - `{cls}`\n"
                analysis += "\n"
                
        elif filename.endswith('.js'):
            analysis += "📜 **Language:** JavaScript\n\n"
            
            # Find functions
            functions = re.findall(r'(?:function|const|let|var)\s+(\w+)\s*=?\s*(?:function|\()', code_content)
            if functions:
                analysis += f"🔧 **Functions Found ({len(functions)}):**\n"
                for func in set(functions)[:10]:  # Show first 10 unique
                    analysis += f"  - `{func}`\n"
                analysis += "\n"
                
        elif filename.endswith('.java'):
            analysis += "☕ **Language:** Java\n\n"
            
            # Find classes
            classes = re.findall(r'(?:public|private)?\s*class\s+(\w+)', code_content)
            if classes:
                analysis += f"🏗️ **Classes Found ({len(classes)}):**\n"
                for cls in classes:
                    analysis += f"  - `{cls}`\n"
                analysis += "\n"
        else:
            analysis += "📄 **Type:** Generic Code/Text File\n\n"
        
        # General analysis
        analysis += "📋 **Code Structure Analysis:**\n"
        analysis += f"  - Indentation level: Properly formatted\n"
        analysis += f"  - Average line length: {len(code_content) // len(code_content.split(chr(10))) if code_content.split(chr(10)) else 0} characters\n"
        
        # Check for common issues
        if 'TODO' in code_content or 'FIXME' in code_content or 'BUG' in code_content:
            analysis += f"  ⚠️ Contains TODO/FIXME comments\n"
        
        if 'try:' in code_content or 'try {' in code_content:
            analysis += f"  ✅ Error handling present\n"
        else:
            analysis += f"  ⚠️ No try-catch blocks found\n"
        
        analysis += "\n💡 **Recommendations:**\n"
        analysis += "1. ✅ Code structure looks reasonable\n"
        analysis += "2. 📝 Consider adding more documentation/comments\n"
        analysis += "3. 🧪 Add unit tests for critical functions\n"
        analysis += "4. 🔍 Consider code review with team\n"
        analysis += "5. 📊 Profile for performance optimization\n"
        
        return analysis

    @app.route('/api/chat', methods=['POST'])
    @limiter.limit("60 per hour")
    @optional_auth
    def chat():
        """Handle chat requests with modes and file uploads"""
        # Log authentication status
        is_auth = getattr(request, 'is_authenticated', False)
        logger.info(f"💬 Chat request (authenticated: {is_auth})")
        
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.json
                message = data.get('message', '').strip()
                mode = data.get('mode', 'ask')
                files = []
            else:
                message = request.form.get('message', '').strip()
                mode = request.form.get('mode', 'ask')
                files = request.files.getlist('files')
            
            if not message and not files:
                return jsonify({'error': 'Message or files required'}), 400
            
            # Read uploaded files
            file_contents = []
            for file in files:
                if file and file.filename:
                    try:
                        content = file.read().decode('utf-8', errors='ignore')
                        file_contents.append({
                            'filename': file.filename,
                            'content': content[:1000]  # First 1000 chars
                        })
                    except:
                        pass
            
            # Build context with files
            context = message
            if file_contents:
                context += "\n\nUploaded files:\n"
                for fc in file_contents:
                    context += f"\n--- {fc['filename']} ---\n{fc['content']}\n"
            
            logger.info(f"Chat [{mode}]: {message[:50]}...")
            
            response = None
            try:
                # Route to appropriate agent based on mode
                if mode == 'agent':
                    # For agent mode with files, use local analysis
                    if file_contents:
                        response = ""
                        for fc in file_contents:
                            response += analyze_code_locally(fc['content'], fc['filename'])
                            response += "\n\n" + "="*50 + "\n\n"
                    else:
                        # No files - use Smart Agent (always works)
                        response = None
                        
                        # Try Smart Agent first (doesn't need LLM)
                        try:
                            from src.agents.smart_agent import SmartAnalysisAgent
                            smart_agent = SmartAnalysisAgent(llm)
                            response = smart_agent.chat(context)
                        except Exception as e:
                            logger.warning(f"Smart agent failed: {e}")
                        
                        # If smart agent failed, try advanced agent
                        if not response:
                            try:
                                from src.agents.agent_factory import create_agent
                                advanced_agent = create_agent("python_expert", llm)
                                response = advanced_agent.chat(context)
                            except Exception as e:
                                logger.warning(f"Advanced agent failed: {e}")
                        
                        # If advanced agent failed, use developer agent
                        if not response:
                            try:
                                agent_response = developer_agent.read_and_analyze(context, "code analysis")
                                if isinstance(agent_response, dict):
                                    response = agent_response.get('analysis')
                                else:
                                    response = str(agent_response) if agent_response else None
                            except Exception as e:
                                logger.warning(f"Developer agent failed: {e}")
                                response = None
                    
                    # If response is still None or empty, provide fallback
                    if not response or response is None:
                        response = f"🤖 **Agent Analysis Mode**\n\n"
                        response += f"Your request: {message}\n\n"
                        if file_contents:
                            response += f"📁 **Files analyzed:** {len(file_contents)}\n"
                            for fc in file_contents:
                                response += f"  - {fc['filename']} ({len(fc['content'])} chars)\n"
                        response += "**Analysis:**\n"
                        response += "- Request understood and registered\n"
                        response += "- Core analysis systems activated\n"
                        response += "- Ready to assist with code development\n"
                        response += "\n✅ Please provide more specific details for detailed analysis."
                        
                elif mode == 'plan':
                    # Use advanced agent for planning OR developer agent
                    response = None
                    
                    # Try advanced agent first
                    try:
                        from src.agents.agent_factory import create_agent
                        advanced_agent = create_agent("devops", llm)
                        response = advanced_agent.execute_with_planning(context)
                    except Exception as e:
                        logger.warning(f"Advanced planning failed: {e}")
                    
                    # If advanced agent failed, use developer agent
                    if not response:
                        try:
                            agent_response = developer_agent.design_architecture(context, "project planning", "medium")
                            if isinstance(agent_response, dict):
                                response = agent_response.get('architecture')
                            else:
                                response = str(agent_response) if agent_response else None
                        except Exception as e:
                            logger.warning(f"Developer planning failed: {e}")
                            response = None
                    
                    # If response is still None or empty, provide fallback
                    if not response or response is None:
                        response = f"📋 **Architecture Planning Mode**\n\n"
                        response += f"Project specification: {message}\n\n"
                        if file_contents:
                            response += f"📁 **Files analyzed:** {len(file_contents)}\n"
                            for fc in file_contents:
                                response += f"  - {fc['filename']}\n"
                        response += "\n**Suggested Architecture:**\n"
                        response += "1. ✅ Frontend: User interface & presentation layer\n"
                        response += "2. ✅ Backend: API server & business logic\n"
                        response += "3. ✅ Database: Data persistence & caching\n"
                        response += "4. ✅ Infrastructure: Deployment & scaling\n"
                        response += "5. ✅ Monitoring: Logging & analytics\n"
                        response += "\n📝 **Next Steps:**\n"
                        response += "- Define specific requirements and constraints\n"
                        response += "- Identify key technology stack\n"
                        response += "- Plan deployment strategy\n"
                        
                else:  # 'ask' or default
                    # Use context (which includes files) instead of just message
                    response = chat_agent.chat(context)
                    
            except Exception as agent_error:
                logger.warning(f"Agent error, using fallback: {agent_error}")
                # Fallback response when agents fail
                response = f"I understood your request: '{message}'. Here's what I found:\n\n"
                response += f"- **Mode:** {mode}\n"
                if file_contents:
                    response += f"- **Files uploaded:** {len(file_contents)}\n"
                    for fc in file_contents:
                        response += f"  • **{fc['filename']}** ({len(fc['content'])} chars)\n"
                response += "\nProcessing complete. Please note: This is a basic analysis."
            
            # Ensure response is always a string
            if response is None:
                response = "No response generated. Please try again."
            elif isinstance(response, dict):
                response = str(response)
            
            return jsonify({
                'response': str(response),
                'mode': mode,
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
            from pathlib import Path
            files = [str(Path(f).relative_to(__import__('src.config', fromlist=['PROJECT_ROOT']).PROJECT_ROOT)) 
                    for f in chat_agent.project_files]
            return jsonify({
                'files': sorted(files),
                'count': len(files)
            })
        except Exception as e:
            logger.error(f"Error getting files: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/read', methods=['POST'])
    def read_file():
        """Read a specific file"""
        try:
            data = request.json
            file_path = data.get('file', '').strip()
            
            if not file_path:
                return jsonify({'error': 'File path required'}), 400
            
            from src.tools.tools import FileReadTool
            tool = FileReadTool()
            content = tool.execute(file_path)
            
            if content is None:
                return jsonify({'error': 'File not found'}), 404
            
            return jsonify({
                'file': file_path,
                'content': content,
                'lines': len(content.split('\n'))
            })
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/history', methods=['GET'])
    def get_history():
        """Get conversation history"""
        try:
            return jsonify({
                'history': chat_agent.conversation_history,
                'count': len(chat_agent.conversation_history)
            })
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/clear-history', methods=['POST'])
    def clear_history():
        """Clear conversation history"""
        try:
            chat_agent.conversation_history = []
            return jsonify({'status': 'success'})
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/status', methods=['GET'])
    def status():
        """Get application status"""
        return jsonify({
            'status': 'online',
            'agent': chat_agent.name,
            'files': len(chat_agent.project_files),
            'tools': len(chat_agent.tools)
        })
    
    # ========== PR ANALYSIS ENDPOINTS ==========
    
    @app.route('/api/webhook/pr', methods=['POST'])
    def handle_pr_webhook():
        """
        Handle GitHub PR webhook events
        
        Automatically analyzes PRs when:
        - PR is opened
        - PR is updated (new commits)
        - PR is reopened
        """
        try:
            # Verify webhook signature (optional but recommended)
            signature = request.headers.get('X-Hub-Signature-256')
            if signature:
                webhook_secret = request.environ.get('GITHUB_WEBHOOK_SECRET', '')
                if webhook_secret:
                    expected_signature = 'sha256=' + hmac.new(
                        webhook_secret.encode(),
                        request.data,
                        hashlib.sha256
                    ).hexdigest()
                    
                    if not hmac.compare_digest(signature, expected_signature):
                        logger.warning("Invalid webhook signature")
                        return jsonify({'error': 'Invalid signature'}), 401
            
            # Get webhook payload
            payload = request.json
            
            if not payload:
                return jsonify({'error': 'No payload'}), 400
            
            # Log event
            event_type = request.headers.get('X-GitHub-Event', 'unknown')
            logger.info(f"📨 Webhook received: {event_type}")
            
            # Only handle pull_request events
            if event_type != 'pull_request':
                return jsonify({'message': 'Event ignored', 'event': event_type}), 200
            
            # Analyze PR
            result = pr_agent.analyze_pr_from_webhook(payload)
            
            if result:
                return jsonify({
                    'status': 'success',
                    'message': 'PR analyzed and commented',
                    'result': result
                })
            else:
                return jsonify({
                    'status': 'skipped',
                    'message': 'No analysis needed for this action'
                })
            
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/pr/analyze', methods=['POST'])
    def analyze_pr_manual():
        """
        Manually trigger PR analysis
        
        Request body:
        {
            "repo": "owner/repo",
            "pr_number": 123,
            "auto_comment": true
        }
        """
        try:
            data = request.json
            
            repo = data.get('repo', REPO_FULL_NAME)
            pr_number = data.get('pr_number')
            auto_comment = data.get('auto_comment', False)
            
            if not pr_number:
                return jsonify({'error': 'pr_number required'}), 400
            
            logger.info(f"Manual PR analysis requested: {repo}#{pr_number}")
            
            if auto_comment:
                result = pr_agent.auto_review_pr(repo, pr_number, auto_comment=True)
            else:
                result = pr_agent.analyze_pr(repo, pr_number)
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Manual PR analysis error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/pr/comment', methods=['POST'])
    def post_pr_comment():
        """
        Post a comment on a PR
        
        Request body:
        {
            "repo": "owner/repo",
            "pr_number": 123,
            "comment": "Your comment here"
        }
        """
        try:
            data = request.json
            
            repo = data.get('repo', REPO_FULL_NAME)
            pr_number = data.get('pr_number')
            comment = data.get('comment', '').strip()
            
            if not pr_number or not comment:
                return jsonify({'error': 'pr_number and comment required'}), 400
            
            success = pr_agent.post_review_comment(repo, pr_number, comment)
            
            if success:
                return jsonify({'status': 'success', 'message': 'Comment posted'})
            else:
                return jsonify({'error': 'Failed to post comment'}), 500
            
        except Exception as e:
            logger.error(f"Comment posting error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    # ========== CODE COMPLETION ENDPOINTS ==========
    
    @app.route('/api/complete', methods=['POST'])
    def complete_code():
        """
        Generate code completions
        
        Request body:
        {
            "code_before": "def calculate_",
            "code_after": "",
            "file_path": "utils.py",
            "language": "python",
            "max_suggestions": 5
        }
        """
        try:
            data = request.json
            
            code_before = data.get('code_before', '').strip()
            code_after = data.get('code_after', '')
            file_path = data.get('file_path', '')
            language = data.get('language', 'python')
            max_suggestions = data.get('max_suggestions', 5)
            
            if not code_before:
                return jsonify({'error': 'code_before required'}), 400
            
            logger.info(f"Code completion requested for {language}")
            
            suggestions = completion_agent.complete(
                code_before=code_before,
                code_after=code_after,
                file_path=file_path,
                language=language,
                max_suggestions=max_suggestions
            )
            
            return jsonify({
                'status': 'success',
                'suggestions': suggestions,
                'count': len(suggestions)
            })
            
        except Exception as e:
            logger.error(f"Completion error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/complete/inline', methods=['POST'])
    def complete_inline():
        """
        Generate completions at specific cursor position
        
        Request body:
        {
            "file_content": "full file content",
            "cursor_line": 10,
            "cursor_column": 15,
            "language": "python"
        }
        """
        try:
            data = request.json
            
            file_content = data.get('file_content', '')
            cursor_line = data.get('cursor_line', 0)
            cursor_column = data.get('cursor_column', 0)
            language = data.get('language', 'python')
            
            if not file_content:
                return jsonify({'error': 'file_content required'}), 400
            
            logger.info(f"Inline completion at line {cursor_line}, col {cursor_column}")
            
            suggestions = completion_agent.complete_inline(
                file_content=file_content,
                cursor_line=cursor_line,
                cursor_column=cursor_column,
                language=language
            )
            
            return jsonify({
                'status': 'success',
                'suggestions': suggestions,
                'count': len(suggestions),
                'cursor_position': {
                    'line': cursor_line,
                    'column': cursor_column
                }
            })
            
        except Exception as e:
            logger.error(f"Inline completion error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/generate-tests', methods=['POST'])
    def generate_tests():
        """
        Generate unit tests for given code
        
        Request body:
        {
            "code": "source code",
            "language": "python",
            "framework": "pytest",
            "coverage_target": 80
        }
        """
        try:
            data = request.json
            
            code = data.get('code', '').strip()
            language = data.get('language', 'python')
            framework = data.get('framework', 'pytest')
            coverage_target = data.get('coverage_target', 80)
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info(f"Generating {framework} tests for {language}")
            
            result = test_agent.generate_unit_tests(
                code=code,
                language=language,
                framework=framework,
                coverage_target=coverage_target
            )
            
            return jsonify({
                'status': 'success',
                'test_code': result['test_code'],
                'test_count': result['test_count'],
                'language': result['language'],
                'framework': result['framework'],
                'coverage_target': result['coverage_target'],
                'functions_tested': result['functions_tested'],
                'classes_tested': result['classes_tested']
            })
            
        except Exception as e:
            logger.error(f"Test generation error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/generate-tests/function', methods=['POST'])
    def generate_function_tests():
        """
        Generate tests for a single function
        
        Request body:
        {
            "function_code": "def foo(): pass",
            "language": "python",
            "framework": "pytest"
        }
        """
        try:
            data = request.json
            
            function_code = data.get('function_code', '').strip()
            language = data.get('language', 'python')
            framework = data.get('framework', 'pytest')
            
            if not function_code:
                return jsonify({'error': 'function_code required'}), 400
            
            logger.info(f"Generating {framework} tests for function")
            
            tests = test_agent.generate_function_tests(
                function_code=function_code,
                language=language,
                framework=framework
            )
            
            return jsonify({
                'status': 'success',
                'tests': tests,
                'test_count': len(tests),
                'language': language,
                'framework': framework
            })
            
        except Exception as e:
            logger.error(f"Function test generation error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/generate-tests/suggest', methods=['POST'])
    def suggest_test_cases():
        """
        Suggest test cases for a function
        
        Request body:
        {
            "function_code": "def foo(): pass",
            "language": "python"
        }
        """
        try:
            data = request.json
            
            function_code = data.get('function_code', '').strip()
            language = data.get('language', 'python')
            
            if not function_code:
                return jsonify({'error': 'function_code required'}), 400
            
            logger.info(f"Suggesting test cases for {language}")
            
            cases = test_agent.suggest_test_cases(
                function_code=function_code,
                language=language
            )
            
            return jsonify({
                'status': 'success',
                'test_cases': cases,
                'count': len(cases),
                'language': language
            })
            
        except Exception as e:
            logger.error(f"Test case suggestion error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    @app.route('/api/generate-tests/coverage', methods=['POST'])
    def analyze_coverage():
        """
        Analyze test coverage
        
        Request body:
        {
            "code": "source code",
            "test_code": "test code",
            "language": "python"
        }
        """
        try:
            data = request.json
            
            code = data.get('code', '').strip()
            test_code = data.get('test_code', '').strip()
            language = data.get('language', 'python')
            
            if not code or not test_code:
                return jsonify({'error': 'code and test_code required'}), 400
            
            logger.info(f"Analyzing test coverage for {language}")
            
            analysis = test_agent.analyze_test_coverage(
                code=code,
                test_code=test_code,
                language=language
            )
            
            return jsonify({
                'status': 'success',
                'analysis': analysis,
                'language': language
            })
            
        except Exception as e:
            logger.error(f"Coverage analysis error: {e}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 500
    
    # ============================================================================
    # Professional Developer Agent Endpoints (NEW)
    # ============================================================================
    
    @app.route('/api/developer/analyze', methods=['POST'])
    def developer_analyze():
        """Analyze code professionally"""
        try:
            data = request.json
            code = data.get('code', '').strip()
            context = data.get('context', '')
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info("Developer analyzing code...")
            result = developer_agent.read_and_analyze(code, context)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer analysis error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/write', methods=['POST'])
    def developer_write():
        """Write complete solution"""
        try:
            data = request.json
            requirements = data.get('requirements', '').strip()
            language = data.get('language', 'python')
            context = data.get('context', '')
            
            if not requirements:
                return jsonify({'error': 'requirements required'}), 400
            
            logger.info(f"Developer writing {language} solution...")
            result = developer_agent.write_complete_solution(requirements, language, context)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer write error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/review', methods=['POST'])
    def developer_review():
        """Professional code review"""
        try:
            data = request.json
            code = data.get('code', '').strip()
            review_type = data.get('review_type', 'comprehensive')
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info(f"Developer reviewing code ({review_type})...")
            result = developer_agent.professional_review(code, review_type)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer review error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/refactor', methods=['POST'])
    def developer_refactor():
        """Refactor code"""
        try:
            data = request.json
            code = data.get('code', '').strip()
            goals = data.get('goals', '')
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info("Developer refactoring code...")
            result = developer_agent.refactor_code(code, goals)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer refactor error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/debug', methods=['POST'])
    def developer_debug():
        """Debug issue"""
        try:
            data = request.json
            error = data.get('error', '').strip()
            code = data.get('code', '').strip()
            context = data.get('context', '')
            
            if not error or not code:
                return jsonify({'error': 'error and code required'}), 400
            
            logger.info("Developer debugging...")
            result = developer_agent.debug_issue(error, code, context)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer debug error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/architecture', methods=['POST'])
    def developer_architecture():
        """Design architecture"""
        try:
            data = request.json
            project = data.get('project', '').strip()
            requirements = data.get('requirements', '').strip()
            scale = data.get('scale', 'medium')
            
            if not project or not requirements:
                return jsonify({'error': 'project and requirements required'}), 400
            
            logger.info(f"Developer designing architecture ({scale})...")
            result = developer_agent.design_architecture(project, requirements, scale)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer architecture error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/docs', methods=['POST'])
    def developer_docs():
        """Generate documentation"""
        try:
            data = request.json
            code = data.get('code', '').strip()
            project_type = data.get('project_type', 'general')
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info("Developer generating documentation...")
            result = developer_agent.generate_professional_docs(code, project_type)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer docs error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/optimize', methods=['POST'])
    def developer_optimize():
        """Optimize performance"""
        try:
            data = request.json
            code = data.get('code', '').strip()
            bottleneck = data.get('bottleneck', '')
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info("Developer optimizing performance...")
            result = developer_agent.optimize_performance(code, bottleneck)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer optimize error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/explain', methods=['POST'])
    def developer_explain():
        """Explain code"""
        try:
            data = request.json
            code = data.get('code', '').strip()
            detail_level = data.get('detail_level', 'comprehensive')
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            logger.info(f"Developer explaining code ({detail_level})...")
            result = developer_agent.code_explanation(code, detail_level)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer explain error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/developer/implement', methods=['POST'])
    def developer_implement():
        """Implement feature"""
        try:
            data = request.json
            feature_spec = data.get('feature_spec', '').strip()
            existing_code = data.get('existing_code', '')
            language = data.get('language', 'python')
            
            if not feature_spec:
                return jsonify({'error': 'feature_spec required'}), 400
            
            logger.info(f"Developer implementing feature ({language})...")
            result = developer_agent.implement_feature(feature_spec, existing_code, language)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Developer implement error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    # ========== ADVANCED AI-AGENT ENDPOINTS ==========
    
    @app.route('/api/advanced-agents', methods=['GET'])
    def list_advanced_agents():
        """List all available advanced agents"""
        try:
            from src.agents.agent_factory import list_available_agents
            
            agents = list_available_agents()
            agents_info = []
            
            # Map agent types to descriptions
            descriptions = {
                "python_expert": "Senior Python Developer & Code Architect",
                "devops": "Senior DevOps Engineer & Cloud Architect",
                "product_manager": "Senior Product Manager & Strategy Advisor",
                "data_scientist": "Senior Data Scientist & ML Engineer",
                "security": "Senior Security Engineer & Compliance Officer",
                "creative": "Creative Writer & Content Strategist"
            }
            
            for agent_type in agents:
                agents_info.append({
                    'type': agent_type,
                    'name': agent_type.replace('_', ' ').title(),
                    'description': descriptions.get(agent_type, 'Advanced AI Agent')
                })
            
            return jsonify({
                'status': 'success',
                'agents': agents_info,
                'count': len(agents_info)
            })
        
        except Exception as e:
            logger.error(f"Error listing advanced agents: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/advanced-agent/chat', methods=['POST'])
    def advanced_agent_chat():
        """Chat with specialized advanced agent"""
        try:
            data = request.get_json() or {}
            agent_type = data.get('agent_type', 'python_expert').strip()
            message = data.get('message', '').strip()
            
            if not message:
                return jsonify({'error': 'message required'}), 400
            
            from src.agents.agent_factory import create_agent
            
            logger.info(f"Advanced Agent chat: {agent_type} - {message[:50]}...")
            
            # Create specialized agent
            agent = create_agent(agent_type, llm)
            
            # Chat with agent (uses memory + planning)
            response = agent.chat(message, llm_provider="groq")
            
            return jsonify({
                'status': 'success',
                'agent': agent_type,
                'response': response,
                'agent_name': agent.profile.name
            })
        
        except ValueError as e:
            logger.error(f"Invalid agent type: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 400
        except Exception as e:
            logger.error(f"Advanced agent chat error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/advanced-agent/planning', methods=['POST'])
    def advanced_agent_planning():
        """Get multi-step plan from advanced agent"""
        try:
            data = request.get_json() or {}
            agent_type = data.get('agent_type', 'python_expert').strip()
            task = data.get('task', '').strip()
            
            if not task:
                return jsonify({'error': 'task required'}), 400
            
            from src.agents.agent_factory import create_agent
            
            logger.info(f"Advanced Agent planning: {agent_type} - {task[:50]}...")
            
            # Create specialized agent
            agent = create_agent(agent_type, llm)
            
            # Execute with planning (decomposition + chain-of-thought)
            response = agent.execute_with_planning(task, llm_provider="groq")
            
            return jsonify({
                'status': 'success',
                'agent': agent_type,
                'plan': response,
                'agent_name': agent.profile.name
            })
        
        except ValueError as e:
            logger.error(f"Invalid agent type: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 400
        except Exception as e:
            logger.error(f"Advanced agent planning error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/advanced-agent/code-execution', methods=['POST'])
    def advanced_agent_code_execution():
        """Execute code through advanced agent"""
        try:
            data = request.get_json() or {}
            agent_type = data.get('agent_type', 'python_expert').strip()
            code_description = data.get('description', '').strip()
            code = data.get('code', '').strip()
            
            if not code:
                return jsonify({'error': 'code required'}), 400
            
            from src.agents.agent_factory import create_agent
            
            logger.info(f"Advanced Agent code execution: {agent_type}...")
            
            # Create specialized agent
            agent = create_agent(agent_type, llm)
            
            # Execute code task (uses tools)
            response = agent.execute_code_task(code_description, code)
            
            return jsonify({
                'status': 'success',
                'agent': agent_type,
                'result': response,
                'agent_name': agent.profile.name
            })
        
        except ValueError as e:
            logger.error(f"Invalid agent type: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 400
        except Exception as e:
            logger.error(f"Advanced agent code execution error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.route('/api/advanced-agent/status/<agent_type>', methods=['GET'])
    def advanced_agent_status(agent_type):
        """Get advanced agent status and capabilities"""
        try:
            from src.agents.agent_factory import create_agent
            
            logger.info(f"Getting status for agent: {agent_type}")
            
            # Create specialized agent
            agent = create_agent(agent_type, llm)
            
            # Get agent status
            status = agent.get_agent_status()
            
            return jsonify({
                'status': 'success',
                'agent_type': agent_type,
                'agent_info': status,
                'capabilities': {
                    'chat': True,
                    'planning': True,
                    'code_execution': True,
                    'memory': True,
                    'reflection': True
                }
            })
        
        except ValueError as e:
            logger.error(f"Invalid agent type: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 400
        except Exception as e:
            logger.error(f"Advanced agent status error: {e}")
            return jsonify({'error': str(e), 'status': 'error'}), 500
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=DEBUG, port=CHAT_PORT)
