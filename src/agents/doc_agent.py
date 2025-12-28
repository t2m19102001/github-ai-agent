#!/usr/bin/env python3
"""
Documentation Agent
Specializes in searching and analyzing documentation
"""

import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    from .base_agent import BaseAgent, AgentContext
    from ..rag.vector_store import VectorStore, SearchResult
    from ..memory.memory_manager import MemoryManager
except ImportError:
    from src.agents.base_agent import BaseAgent, AgentContext
    from src.rag.vector_store import VectorStore, SearchResult
    from src.memory.memory_manager import MemoryManager

try:
    from utils.logger import get_logger
except ImportError:
    from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DocumentSection:
    """Document section structure"""
    title: str
    content: str
    section_type: str  # api, tutorial, example, reference
    relevance_score: float
    metadata: Dict[str, Any]


@dataclass
class DocumentationResult:
    """Documentation search result"""
    query: str
    sections: List[DocumentSection]
    code_examples: List[str]
    related_topics: List[str]
    confidence: float
    sources: List[str]


class DocumentationAgent(BaseAgent):
    """Agent for documentation search and analysis"""
    
    def __init__(self, vector_store: VectorStore = None, 
                 memory_manager: MemoryManager = None, config: Dict[str, Any] = None):
        super().__init__("DocumentationAgent", config=config)
        
        self.vector_store = vector_store
        self.memory_manager = memory_manager
        
        # Documentation sources
        self.doc_sources = [
            "README.md",
            "docs/",
            "documentation/",
            "*.md",
            "*.rst"
        ]
        
        # Set system prompt
        self.system_prompt = """You are DocumentationAgent, an AI assistant specialized in searching and analyzing technical documentation.

Your responsibilities:
1. Search through documentation for relevant information
2. Extract key sections and code examples
3. Provide context-aware explanations
4. Suggest related topics and resources
5. Maintain accuracy and cite sources

Documentation types you handle:
- API documentation and reference
- Tutorials and guides
- Code examples and snippets
- Best practices and patterns
- Troubleshooting guides

Always provide clear, accurate, and well-structured responses with proper citations."""
        
        logger.info("Initialized DocumentationAgent")
    
    async def search_documentation(self, query: str, context: str = "", 
                               limit: int = 5) -> DocumentationResult:
        """Search documentation for relevant information"""
        try:
            # Generate query embedding (simplified)
            query_embedding = self._generate_query_embedding(query)
            
            # Search vector store
            search_results = []
            if self.vector_store:
                search_results = self.vector_store.search(query_embedding, k=limit)
            
            # Convert search results to document sections
            sections = []
            code_examples = []
            sources = []
            
            for result in search_results:
                doc = result.document
                section = DocumentSection(
                    title=doc.metadata.get("title", "Untitled Section"),
                    content=doc.content,
                    section_type=doc.metadata.get("type", "reference"),
                    relevance_score=result.score,
                    metadata=doc.metadata
                )
                sections.append(section)
                sources.append(doc.id)
                
                # Extract code examples
                examples = self._extract_code_examples(doc.content)
                code_examples.extend(examples)
            
            # Search memory for related information
            memory_results = []
            if self.memory_manager:
                memory_results = self.memory_manager.search(query, memory_type="fact", limit=3)
            
            # Generate related topics
            related_topics = self._extract_related_topics(query, sections, memory_results)
            
            # Calculate confidence
            confidence = self._calculate_search_confidence(
                search_results, memory_results, query
            )
            
            # Store search in memory
            if self.memory_manager:
                self.memory_manager.remember(
                    key=f"doc_search_{query}",
                    value={
                        "query": query,
                        "results": len(sections),
                        "confidence": confidence,
                        "timestamp": self._get_current_timestamp()
                    },
                    memory_type="search",
                    importance=0.6
                )
            
            result = DocumentationResult(
                query=query,
                sections=sections,
                code_examples=code_examples,
                related_topics=related_topics,
                confidence=confidence,
                sources=sources
            )
            
            logger.info(f"Documentation search for '{query}' found {len(sections)} sections")
            return result
            
        except Exception as e:
            logger.error(f"Error searching documentation: {e}")
            return DocumentationResult(
                query=query,
                sections=[],
                code_examples=[],
                related_topics=[],
                confidence=0.0,
                sources=[]
            )
    
    async def analyze_documentation(self, content: str, 
                                doc_type: str = "general") -> Dict[str, Any]:
        """Analyze documentation content"""
        try:
            # Extract structure
            structure = self._analyze_document_structure(content)
            
            # Extract key concepts
            concepts = self._extract_key_concepts(content)
            
            # Identify code examples
            examples = self._extract_code_examples(content)
            
            # Assess quality
            quality_score = self._assess_documentation_quality(content)
            
            # Generate summary
            summary = await self._generate_documentation_summary(
                content, structure, concepts, examples
            )
            
            analysis = {
                "doc_type": doc_type,
                "structure": structure,
                "key_concepts": concepts,
                "code_examples": examples,
                "quality_score": quality_score,
                "summary": summary,
                "recommendations": self._generate_doc_recommendations(
                    content, quality_score, concepts
                )
            }
            
            # Store analysis in memory
            if self.memory_manager:
                self.memory_manager.remember(
                    key=f"doc_analysis_{self._get_current_timestamp()}",
                    value=analysis,
                    memory_type="analysis",
                    importance=0.7
                )
            
            logger.info(f"Analyzed documentation content: {len(concepts)} concepts found")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing documentation: {e}")
            return {"error": str(e)}
    
    async def process_message(self, message: str, context: AgentContext) -> str:
        """Process incoming message"""
        try:
            # Check for documentation search request
            if any(keyword in message.lower() for keyword in [
                "search docs", "find documentation", "look up", "documentation"
            ]):
                query = self._extract_search_query(message)
                if query:
                    result = await self.search_documentation(query)
                    return self._format_search_result(result)
            
            # Check for documentation analysis request
            elif any(keyword in message.lower() for keyword in [
                "analyze docs", "review documentation", "check docs"
            ]):
                content = self._extract_content_for_analysis(message)
                if content:
                    analysis = await self.analyze_documentation(content)
                    return self._format_analysis_result(analysis)
            
            # Check for general documentation question
            elif any(keyword in message.lower() for keyword in [
                "how to", "what is", "explain", "documentation"
            ]):
                # Search for relevant documentation
                result = await self.search_documentation(message)
                if result.sections:
                    return self._format_search_result(result)
                else:
                    return await self._generate_explanation_response(message)
            
            # Default response
            else:
                return """I can help you with documentation! Here's what I can do:

1. **Search Documentation**: "search docs for [topic]" or "find [topic] documentation"
2. **Analyze Documentation**: "analyze [documentation content]" or "review docs"
3. **Answer Questions**: Ask questions about APIs, concepts, or implementation

Examples:
- "search docs for authentication"
- "analyze this API documentation: [paste content]"
- "how do I implement user authentication?"

What would you like to know about?"""
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error processing your request: {str(e)}"
    
    def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query (simplified)"""
        # This is a simplified embedding generation
        # In production, you'd use a proper embedding model
        import hashlib
        import math
        
        # Create a simple hash-based embedding
        words = query.lower().split()
        embedding = []
        
        for i in range(768):  # Standard embedding dimension
            if i < len(words):
                # Use word hash for embedding values
                word_hash = int(hashlib.md5(words[i % len(words)]).hexdigest()[:8], 16)
                embedding.append((word_hash % 1000) / 1000.0)
            else:
                embedding.append(0.0)
        
        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding))
        if norm > 0:
            embedding = [x/norm for x in embedding]
        
        return embedding
    
    def _extract_code_examples(self, content: str) -> List[str]:
        """Extract code examples from documentation"""
        import re
        
        # Code block patterns
        patterns = [
            r'```python\n(.*?)\n```',
            r'```javascript\n(.*?)\n```',
            r'```bash\n(.*?)\n```',
            r'```(.*?)\n```',
            r'`(.*?)`',
            r'```\n(.*?)\n```'
        ]
        
        examples = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    code = match[1] if len(match) > 1 else match[0]
                else:
                    code = match
                
                if code and len(code.strip()) > 10:  # Filter small fragments
                    examples.append(code.strip())
        
        # Remove duplicates and limit
        examples = list(dict.fromkeys(examples))[:5]  # Remove duplicates, max 5
        
        return examples
    
    def _extract_related_topics(self, query: str, sections: List[DocumentSection], 
                             memory_results: List) -> List[str]:
        """Extract related topics from search results"""
        topics = []
        
        # Extract topics from query
        query_words = query.lower().split()
        topics.extend([word for word in query_words if len(word) > 3])
        
        # Extract topics from section titles
        for section in sections:
            title_words = section.title.lower().split()
            for word in title_words:
                if len(word) > 3 and word not in topics:
                    topics.append(word)
        
        # Extract topics from memory results
        for memory_result in memory_results:
            if isinstance(memory_result.value, dict):
                memory_topics = memory_result.value.get("topics", [])
                topics.extend(memory_topics)
        
        # Remove duplicates and limit
        topics = list(dict.fromkeys(topics))[:10]  # Remove duplicates, max 10
        
        return topics
    
    def _calculate_search_confidence(self, search_results: List[SearchResult], 
                                  memory_results: List, query: str) -> float:
        """Calculate confidence score for search results"""
        confidence = 0.0
        
        # Base confidence from search results
        if search_results:
            avg_score = sum(r.score for r in search_results) / len(search_results)
            confidence += avg_score * 0.6
        
        # Boost from memory results
        if memory_results:
            confidence += len(memory_results) * 0.1
        
        # Query specificity boost
        if len(query.split()) >= 3:  # Multi-word query
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _analyze_document_structure(self, content: str) -> Dict[str, Any]:
        """Analyze document structure"""
        import re
        
        # Count headings
        headings = {
            "h1": len(re.findall(r'^# ', content, re.MULTILINE)),
            "h2": len(re.findall(r'^## ', content, re.MULTILINE)),
            "h3": len(re.findall(r'^### ', content, re.MULTILINE)),
            "h4": len(re.findall(r'^#### ', content, re.MULTILINE))
        }
        
        # Count code blocks
        code_blocks = len(re.findall(r'```', content))
        
        # Count lists
        lists = len(re.findall(r'^\s*[-*+]\s', content, re.MULTILINE))
        
        # Count tables
        tables = len(re.findall(r'\|.*\|', content))
        
        # Estimate sections
        total_headings = sum(headings.values())
        estimated_sections = max(1, total_headings)
        
        return {
            "headings": headings,
            "code_blocks": code_blocks,
            "lists": lists,
            "tables": tables,
            "estimated_sections": estimated_sections,
            "structure_score": min(1.0, (total_headings + code_blocks + lists) / 20)
        }
    
    def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from documentation"""
        import re
        
        # Technical terms patterns
        patterns = [
            r'\b[A-Z][a-z]+(?:API|SDK|Library|Framework|Class|Method|Function)\b',
            r'\b\w+(?:ing|tion|ment|er|ism)\b',
            r'\b(?:HTTP|HTTPS|JSON|XML|HTML|CSS|JavaScript|Python)\b',
            r'```(\w+)```',  # Code language indicators
        ]
        
        concepts = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            concepts.extend(matches)
        
        # Remove duplicates and common words
        common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        concepts = [c for c in concepts if c.lower() not in common_words and len(c) > 2]
        
        # Limit and return
        return list(dict.fromkeys(concepts))[:15]  # Remove duplicates, max 15
    
    def _assess_documentation_quality(self, content: str) -> float:
        """Assess documentation quality"""
        score = 0.0
        
        # Structure quality (0-0.3)
        if re.search(r'^#+ ', content, re.MULTILINE):
            score += 0.1
        if '```' in content:
            score += 0.1
        if re.search(r'^\s*[-*+]\s', content, re.MULTILINE):
            score += 0.1
        
        # Content quality (0-0.3)
        word_count = len(content.split())
        if word_count > 100:
            score += 0.1
        if word_count > 500:
            score += 0.1
        if word_count > 1000:
            score += 0.1
        
        # Examples quality (0-0.2)
        code_examples = self._extract_code_examples(content)
        if len(code_examples) > 0:
            score += 0.1
        if len(code_examples) > 3:
            score += 0.1
        
        # Clarity indicators (0-0.2)
        if re.search(r'\b(exampl|for instanc|such as|note that)\b', content, re.IGNORECASE):
            score += 0.1
        if not re.search(r'\b(todo|fixme|placeholder)\b', content, re.IGNORECASE):
            score += 0.1
        
        return min(1.0, score)
    
    async def _generate_documentation_summary(self, content: str, structure: Dict[str, Any], 
                                       concepts: List[str], examples: List[str]) -> str:
        """Generate documentation summary"""
        prompt = f"""Analyze this documentation content and provide a concise summary:

Content length: {len(content)} characters
Structure: {structure.get('estimated_sections', 0)} sections
Key concepts: {len(concepts)} concepts
Code examples: {len(examples)} examples

Provide a 2-3 sentence summary of what this documentation covers and its key points."""
        
        return await self.generate_response(prompt)
    
    def _generate_doc_recommendations(self, content: str, quality_score: float, 
                                 concepts: List[str]) -> List[str]:
        """Generate documentation improvement recommendations"""
        recommendations = []
        
        # Quality-based recommendations
        if quality_score < 0.5:
            recommendations.append("Add more structural elements (headings, lists)")
            recommendations.append("Include code examples to illustrate concepts")
        
        if quality_score < 0.7:
            recommendations.append("Expand explanations with more details")
            recommendations.append("Add cross-references to related topics")
        
        # Content-based recommendations
        if len(concepts) < 5:
            recommendations.append("Cover more key concepts and terminology")
        
        if len(self._extract_code_examples(content)) < 2:
            recommendations.append("Add practical code examples")
        
        # General recommendations
        recommendations.extend([
            "Review for clarity and consistency",
            "Add table of contents for longer documents",
            "Include troubleshooting section if applicable"
        ])
        
        return list(dict.fromkeys(recommendations))[:6]  # Remove duplicates, max 6
    
    async def _generate_explanation_response(self, query: str) -> str:
        """Generate explanation for general questions"""
        prompt = f"""Explain this concept clearly and concisely:

Query: {query}

Provide:
1. Clear definition
2. Key characteristics
3. Common use cases
4. Important considerations

Keep it technical but accessible."""
        
        return await self.generate_response(prompt)
    
    def _extract_search_query(self, message: str) -> Optional[str]:
        """Extract search query from message"""
        import re
        
        # Patterns for extracting search queries
        patterns = [
            r'search docs for (.+?)(?:\s|$)',
            r'find (.+?) documentation',
            r'look up (.+?)(?:\s|$)',
            r'documentation about (.+?)(?:\s|$)',
            r'what is (.+?)(?:\s|$)',
            r'how to (.+?)(?:\s|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_content_for_analysis(self, message: str) -> Optional[str]:
        """Extract content for documentation analysis"""
        # Look for content after analysis keywords
        import re
        
        patterns = [
            r'analyze (.+?)(?:\s|$)',
            r'review (.+?) documentation',
            r'check docs (.+?)(?:\s|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _format_search_result(self, result: DocumentationResult) -> str:
        """Format documentation search result"""
        response = f"""## Documentation Search Results for: "{result.query}"

### 📊 Search Confidence: {result.confidence:.1%}

### 📚 Relevant Sections ({len(result.sections)}):
"""
        
        for i, section in enumerate(result.sections[:3], 1):
            response += f"""**{i}. {section.title}**
{section.content[:200]}...
*Relevance: {section.relevance_score:.2f}*

"""
        
        if result.code_examples:
            response += f"""### 💻 Code Examples ({len(result.code_examples)}):
"""
            for i, example in enumerate(result.code_examples[:2], 1):
                response += f"""**Example {i}:**
```python
{example[:300]}
```

"""
        
        if result.related_topics:
            response += f"""### 🔗 Related Topics:
{', '.join(result.related_topics[:5])}

"""
        
        if result.sources:
            response += f"""### 📖 Sources:
{', '.join(result.sources[:3])}

"""
        
        return response
    
    def _format_analysis_result(self, analysis: Dict[str, Any]) -> str:
        """Format documentation analysis result"""
        if "error" in analysis:
            return f"Error analyzing documentation: {analysis['error']}"
        
        response = f"""## Documentation Analysis Results

### 📊 Quality Score: {analysis.get('quality_score', 0):.1%}

### 🏗️ Structure Analysis:
- **Sections**: {analysis.get('structure', {}).get('estimated_sections', 0)}
- **Code Blocks**: {analysis.get('structure', {}).get('code_blocks', 0)}
- **Lists**: {analysis.get('structure', {}).get('lists', 0)}

### 💡 Key Concepts ({len(analysis.get('key_concepts', []))}):
{', '.join(analysis.get('key_concepts', [])[:5])}

### 💻 Code Examples ({len(analysis.get('code_examples', []))}):
Found {len(analysis.get('code_examples', []))} code examples in the documentation.

### 📝 Summary:
{analysis.get('summary', 'No summary available.')}

### 🔧 Recommendations:
"""
        
        for rec in analysis.get('recommendations', [])[:5]:
            response += f"- {rec}\n"
        
        return response
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp string"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")


# Test function
async def test_documentation_agent():
    """Test documentation agent functionality"""
    try:
        from src.rag.vector_store import VectorStore
        
        # Create test vector store and memory
        vector_store = VectorStore(dimension=10, storage_path="test_vector_store")
        
        # Add test documents
        test_docs = [
            ("Authentication API allows users to login with username and password", 
             {"type": "api", "title": "Authentication"}),
            ("Use JWT tokens for secure authentication", 
             {"type": "tutorial", "title": "JWT Authentication"}),
            ("Error handling best practices include try-catch blocks", 
             {"type": "best_practices", "title": "Error Handling"})
        ]
        
        # Create fake embeddings
        import numpy as np
        for content, metadata in test_docs:
            embedding = np.random.rand(10)
            vector_store.add_document(content, metadata, embedding=embedding)
        
        # Create documentation agent
        doc_agent = DocumentationAgent(vector_store)
        
        # Test documentation search
        result = await doc_agent.search_documentation("authentication")
        
        print("Documentation Search Results:")
        print(f"Query: {result.query}")
        print(f"Sections found: {len(result.sections)}")
        print(f"Confidence: {result.confidence:.2f}")
        
        # Test message processing
        response = await doc_agent.chat("search docs for login authentication")
        print(f"Chat response: {response[:200]}...")
        
    except Exception as e:
        print(f"Error testing documentation agent: {e}")


if __name__ == "__main__":
    asyncio.run(test_documentation_agent())
