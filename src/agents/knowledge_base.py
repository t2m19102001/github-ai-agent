#!/usr/bin/env python3
"""
Knowledge Base System - Xây dựng kiến thức thực cho AI
Không phải hardcoded responses, mà là dynamic knowledge retrieval
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class KnowledgeItem:
    """Một unit kiến thức"""
    id: str
    category: str  # "odoo", "python", "architecture", "performance", etc.
    topic: str     # "module_development", "database_optimization", etc.
    title: str
    content: str
    tags: List[str]
    source: str    # "codebase", "documentation", "best_practices", "user_feedback"
    created_at: str
    updated_at: str
    relevance_score: float = 0.0
    usage_count: int = 0
    
    def to_dict(self):
        return asdict(self)


class KnowledgeBase:
    """Knowledge Base - Lưu trữ và quản lý kiến thức"""
    
    def __init__(self, storage_path: str = "data/knowledge_base.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.tag_index: Dict[str, List[str]] = {}
        self.load()
    
    def load(self):
        """Load knowledge base từ file"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item_dict in data:
                        item = KnowledgeItem(**item_dict)
                        self.knowledge_items[item.id] = item
                        self._update_indices(item)
                logger.info(f"✅ Loaded {len(self.knowledge_items)} knowledge items")
            except Exception as e:
                logger.error(f"Failed to load knowledge base: {e}")
        else:
            logger.info("Creating new knowledge base")
    
    def save(self):
        """Save knowledge base to file"""
        try:
            items_data = [item.to_dict() for item in self.knowledge_items.values()]
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(items_data, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Saved {len(self.knowledge_items)} knowledge items")
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {e}")
    
    def _update_indices(self, item: KnowledgeItem):
        """Update category and tag indices"""
        if item.category not in self.category_index:
            self.category_index[item.category] = []
        self.category_index[item.category].append(item.id)
        
        for tag in item.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(item.id)
    
    def add_item(self, category: str, topic: str, title: str, content: str, 
                 tags: List[str], source: str) -> str:
        """Thêm một knowledge item"""
        now = datetime.now().isoformat()
        item_id = hashlib.md5(f"{category}_{topic}_{title}_{now}".encode()).hexdigest()[:12]
        
        item = KnowledgeItem(
            id=item_id,
            category=category,
            topic=topic,
            title=title,
            content=content,
            tags=tags,
            source=source,
            created_at=now,
            updated_at=now,
            relevance_score=1.0,
            usage_count=0
        )
        
        self.knowledge_items[item_id] = item
        self._update_indices(item)
        logger.info(f"Added knowledge item: {title}")
        return item_id
    
    def search(self, query: str, category: Optional[str] = None, 
               top_k: int = 5) -> List[Tuple[KnowledgeItem, float]]:
        """Search knowledge by query"""
        query_lower = query.lower()
        results: List[Tuple[KnowledgeItem, float]] = []
        
        for item in self.knowledge_items.values():
            # Filter by category if specified
            if category and item.category != category:
                continue
            
            # Calculate relevance score
            score = 0.0
            
            # Title match (highest weight)
            if query_lower in item.title.lower():
                score += 3.0
            
            # Tag match
            for tag in item.tags:
                if query_lower in tag.lower() or tag.lower() in query_lower:
                    score += 2.0
            
            # Content match
            content_lower = item.content.lower()
            content_matches = len(re.findall(rf'\b{re.escape(query_lower)}\b', content_lower))
            score += content_matches * 0.5
            
            # Boost frequently used items
            score += (item.usage_count / 100.0) if item.usage_count > 0 else 0
            
            if score > 0:
                results.append((item, score))
        
        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_by_category(self, category: str, limit: int = 10) -> List[KnowledgeItem]:
        """Get all knowledge items in a category"""
        if category not in self.category_index:
            return []
        
        items = [self.knowledge_items[item_id] 
                for item_id in self.category_index[category][:limit]]
        return items
    
    def increment_usage(self, item_id: str):
        """Increment usage count for item"""
        if item_id in self.knowledge_items:
            self.knowledge_items[item_id].usage_count += 1
            self.knowledge_items[item_id].updated_at = datetime.now().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        return {
            "total_items": len(self.knowledge_items),
            "categories": list(self.category_index.keys()),
            "items_per_category": {cat: len(items) for cat, items in self.category_index.items()},
            "total_tags": len(self.tag_index),
            "storage_file": str(self.storage_path)
        }


class KnowledgeIngestion:
    """Import kiến thức từ nhiều nguồn"""
    
    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
    
    def ingest_odoo_knowledge(self):
        """Import Odoo development knowledge"""
        odoo_knowledge = [
            {
                "topic": "module_structure",
                "title": "Odoo Module Directory Structure",
                "content": """
Cấu trúc chuẩn của một Odoo module:

```
my_module/
├── __init__.py              # Package init, khai báo models
├── __manifest__.py          # Module metadata (name, version, dependencies)
├── models/
│   ├── __init__.py
│   └── my_model.py          # Inherit from models.Model
├── views/
│   ├── my_model_views.xml   # Form, Tree, Search views
│   └── my_model_actions.xml # Action definitions
├── controllers/
│   ├── __init__.py
│   └── main.py              # HTTP routes
├── static/
│   ├── css/
│   └── js/
├── data/
│   └── data.xml             # Default data
├── security/
│   └── ir.model.access.csv  # Access rights
├── reports/
│   └── my_report.xml        # Reporting
└── i18n/
    └── vi_VN.po             # Translations
```

Mỗi directory có mục đích cụ thể:
- **models/**: Business logic, data models
- **views/**: UI templates (XML)
- **controllers/**: Web routes, API endpoints
- **static/**: CSS, JavaScript assets
- **security/**: Access control rules
- **data/**: Initial data loading
                """,
                "tags": ["odoo", "module", "structure", "basics"],
                "source": "codebase"
            },
            {
                "topic": "module_development",
                "title": "Creating Odoo Models and Fields",
                "content": """
Tạo models trong Odoo:

```python
from odoo import models, fields

class SaleOrder(models.Model):
    _name = 'sale.order'
    _description = 'Sale Order'
    _order = 'date_order desc'
    
    # Fields
    name = fields.Char(string='Order Reference', required=True, copy=False)
    date_order = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    order_lines = fields.One2many('sale.order.line', 'order_id', string='Order Lines')
    total_amount = fields.Float(string='Total', compute='_compute_total')
    
    # Computed fields
    @api.depends('order_lines.subtotal')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(line.subtotal for line in record.order_lines)
    
    # Methods
    def action_confirm(self):
        # Xử lý xác nhận đơn hàng
        self.state = 'confirmed'
```

Các loại field phổ biến:
- **Char**: String field
- **Text**: Long text
- **Integer**: Integer number
- **Float**: Decimal number
- **Boolean**: True/False
- **Date/Datetime**: Date and time
- **Selection**: Dropdown list
- **Many2one**: Link to another record
- **One2many**: Reverse relationship
- **Many2many**: Multiple relationships
                """,
                "tags": ["odoo", "models", "fields", "development"],
                "source": "codebase"
            },
            {
                "topic": "access_control",
                "title": "Odoo Security and Access Control",
                "content": """
Quản lý quyền truy cập trong Odoo:

**1. Model Access (ir.model.access.csv)**
```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sale_order_user,Sale Order User,sale.model_sale_order,sales_team.group_sale_user,1,1,1,0
access_sale_order_manager,Sale Order Manager,sale.model_sale_order,sales_team.group_sale_manager,1,1,1,1
```

**2. Record Rules (Domain-based)**
```python
class SaleOrderRules(models.Model):
    _inherit = 'ir.rule'
    
    # User chỉ thấy đơn hàng của chính mình
    _sql_constraints = [
        ('sale_order_company_unique', 'unique (sale_order_id, company_id)', 
         'A sale order must be unique per company'),
    ]
```

**3. Field-level Security**
```python
name = fields.Char(string='Name', groups='sales_team.group_sale_manager')
# Field này chỉ visible cho managers
```

Best practices:
- Luôn tạo security rules cho models mới
- Kiểm tra permissions trong methods
- Sử dụng domain-based rules cho record-level security
                """,
                "tags": ["odoo", "security", "access_control", "best_practices"],
                "source": "codebase"
            }
        ]
        
        for knowledge in odoo_knowledge:
            self.kb.add_item(
                category="odoo",
                topic=knowledge["topic"],
                title=knowledge["title"],
                content=knowledge["content"],
                tags=knowledge["tags"],
                source=knowledge["source"]
            )
    
    def ingest_python_knowledge(self):
        """Import Python development knowledge"""
        python_knowledge = [
            {
                "topic": "performance_optimization",
                "title": "Python Performance Optimization Techniques",
                "content": """
Tối ưu hóa performance Python:

**1. Database Query Optimization**
- Sử dụng `.select_related()` cho ForeignKey relationships
- Sử dụng `.prefetch_related()` cho reverse ForeignKey và ManyToMany
- Sử dụng `.only()` để lấy chỉ những fields cần thiết
- Thêm database indexes cho các fields được query thường xuyên

```python
# BAD - N+1 queries
for order in Order.objects.all():
    print(order.customer.name)  # Query lại cho mỗi order

# GOOD - 1 query
orders = Order.objects.select_related('customer')
for order in orders:
    print(order.customer.name)  # Dữ liệu đã cached
```

**2. Caching Strategy**
- Use Redis cho session caching
- Cache expensive computations
- Implement cache invalidation

**3. Code Efficiency**
- Tránh nested loops (O(n²))
- Dùng list comprehensions
- Lazy load resources
- Use generators cho large datasets

**4. Profiling**
- Python cProfile
- Line profiler
- Memory profiler
                """,
                "tags": ["python", "performance", "optimization", "database"],
                "source": "codebase"
            },
            {
                "topic": "async_programming",
                "title": "Async/Await and Concurrency in Python",
                "content": """
Lập trình bất đồng bộ trong Python:

**1. Basic Async/Await**
```python
import asyncio

async def fetch_data():
    # Simulate I/O operation
    await asyncio.sleep(1)
    return "data"

async def main():
    result = await fetch_data()
    print(result)

asyncio.run(main())
```

**2. Concurrent Execution**
```python
async def main():
    # Execute multiple tasks concurrently
    results = await asyncio.gather(
        fetch_data(),
        fetch_data(),
        fetch_data()
    )
    return results
```

**3. Error Handling**
```python
async def safe_fetch():
    try:
        result = await fetch_data()
    except asyncio.TimeoutError:
        print("Request timeout")
    except Exception as e:
        print(f"Error: {e}")
```

**4. Async Context Managers**
```python
async with aiohttp.ClientSession() as session:
    async with session.get(url) as resp:
        data = await resp.json()
```

Benefits:
- Better throughput cho I/O-bound operations
- Responsive applications
- Scalable server design
                """,
                "tags": ["python", "async", "concurrency", "performance"],
                "source": "codebase"
            }
        ]
        
        for knowledge in python_knowledge:
            self.kb.add_item(
                category="python",
                topic=knowledge["topic"],
                title=knowledge["title"],
                content=knowledge["content"],
                tags=knowledge["tags"],
                source=knowledge["source"]
            )
    
    def ingest_architecture_knowledge(self):
        """Import architecture and design patterns"""
        arch_knowledge = [
            {
                "topic": "layered_architecture",
                "title": "Layered Architecture Pattern",
                "content": """
Mô hình kiến trúc phân lớp:

```
┌─────────────────────────────┐
│   Presentation Layer        │ (Controllers, Views, API)
├─────────────────────────────┤
│   Business Logic Layer       │ (Services, Business Rules)
├─────────────────────────────┤
│   Persistence Layer          │ (DAOs, Database Access)
├─────────────────────────────┤
│   Infrastructure Layer       │ (Utilities, Configuration)
└─────────────────────────────┘
```

**Advantages:**
- Separation of Concerns
- Easy to test each layer independently
- Allows parallel development
- Clear dependencies

**Implementation in Odoo:**
```
views/ (Presentation)
  ↓
controllers/ (Business Logic)
  ↓
models/ (Persistence)
  ↓
data/ (Infrastructure)
```

**Best Practices:**
- Each layer should have clear boundaries
- Minimize cross-layer dependencies
- Use dependency injection
- Document layer responsibilities
                """,
                "tags": ["architecture", "design_patterns", "layered", "best_practices"],
                "source": "codebase"
            },
            {
                "topic": "microservices",
                "title": "Microservices Architecture Principles",
                "content": """
Nguyên lý kiến trúc Microservices:

**1. Service Independence**
- Mỗi service là independent deployable unit
- Có database riêng
- Độc lập về technology stack

**2. Communication Patterns**
- Synchronous: REST API, gRPC
- Asynchronous: Message queues (RabbitMQ, Kafka)

**3. API Gateway**
- Single entry point
- Request routing
- Authentication/Authorization
- Rate limiting

**4. Service Discovery**
- Services tìm nhau qua service registry
- Automatic load balancing
- Health checking

**5. Data Management**
- Database per service pattern
- Event sourcing cho data consistency
- Distributed transactions (saga pattern)

**Challenges:**
- Complexity
- Distributed debugging
- Network latency
- Data consistency

**When to use:**
- Large, complex applications
- Multiple teams
- Different scaling requirements
- Technology diversity needs
                """,
                "tags": ["architecture", "microservices", "design_patterns", "scalability"],
                "source": "codebase"
            }
        ]
        
        for knowledge in arch_knowledge:
            self.kb.add_item(
                category="architecture",
                topic=knowledge["topic"],
                title=knowledge["title"],
                content=knowledge["content"],
                tags=knowledge["tags"],
                source=knowledge["source"]
            )
    
    def ingest_best_practices(self):
        """Import development best practices"""
        practices = [
            {
                "topic": "code_review",
                "title": "Code Review Best Practices",
                "content": """
Quy trình review code hiệu quả:

**1. Pre-review (Author)**
- Code tự test trước
- Follow style guide
- Viết meaningful commit messages
- Add comments cho logic phức tạp

**2. Review Process**
- Check logic correctness
- Look for performance issues
- Verify security
- Check error handling
- Review test coverage

**3. Feedback**
- Be constructive
- Ask questions instead of demanding
- Suggest improvements
- Explain reasoning

**4. Common Issues to Check**
- ✓ Error handling
- ✓ SQL injection vulnerabilities
- ✓ Race conditions
- ✓ Memory leaks
- ✓ Missing logging
- ✓ Hard-coded values
- ✓ Inefficient algorithms

**Tools:**
- GitHub Pull Requests
- GitLab Merge Requests
- Gerrit
- Upsource
                """,
                "tags": ["best_practices", "code_review", "quality"],
                "source": "codebase"
            },
            {
                "topic": "testing",
                "title": "Testing Strategy and Approaches",
                "content": """
Chiến lược testing toàn diện:

**1. Unit Testing**
- Test individual functions/methods
- Use mocking for dependencies
- Aim for >80% coverage
```python
def test_calculate_total():
    order = Order(items=[Item(10), Item(20)])
    assert order.calculate_total() == 30
```

**2. Integration Testing**
- Test interactions between components
- Use test database
- Test API endpoints

**3. End-to-End Testing**
- Test complete user workflows
- Automated UI testing
- Test data fixtures

**4. Performance Testing**
- Load testing
- Stress testing
- Benchmark critical paths

**5. Security Testing**
- SQL injection attempts
- XSS vulnerabilities
- Authentication/authorization
- Data validation

**Tools:**
- pytest
- unittest
- Selenium
- JMeter
- OWASP ZAP

**Coverage Goals:**
- Critical paths: 100%
- Core business logic: >80%
- Overall: >70%
                """,
                "tags": ["best_practices", "testing", "quality_assurance"],
                "source": "codebase"
            }
        ]
        
        for knowledge in practices:
            self.kb.add_item(
                category="best_practices",
                topic=knowledge["topic"],
                title=knowledge["title"],
                content=knowledge["content"],
                tags=knowledge["tags"],
                source=knowledge["source"]
            )
    
    def ingest_all(self):
        """Load all knowledge"""
        logger.info("📚 Ingesting knowledge...")
        self.ingest_odoo_knowledge()
        self.ingest_python_knowledge()
        self.ingest_architecture_knowledge()
        self.ingest_best_practices()
        self.kb.save()
        logger.info(f"✅ Knowledge ingestion complete: {len(self.kb.knowledge_items)} items")


# Singleton instance
_kb_instance = None

def get_knowledge_base() -> KnowledgeBase:
    """Get or create knowledge base instance"""
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
        # Auto-ingest nếu empty
        if len(_kb_instance.knowledge_items) == 0:
            ingestion = KnowledgeIngestion(_kb_instance)
            ingestion.ingest_all()
    return _kb_instance
