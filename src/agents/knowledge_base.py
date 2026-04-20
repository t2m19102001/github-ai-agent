#!/usr/bin/env python3
"""Small in-memory knowledge base used by Flask routes and demos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple
import uuid


@dataclass
class KnowledgeItem:
    id: str
    category: str
    topic: str
    title: str
    content: str
    tags: List[str]
    source: str
    usage_count: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


class KnowledgeBase:
    def __init__(self):
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.category_index: Dict[str, List[str]] = {}
        self.tag_index: Dict[str, List[str]] = {}

    def add_item(self, category: str, topic: str, title: str, content: str, tags: List[str], source: str) -> str:
        item_id = str(uuid.uuid4())
        item = KnowledgeItem(item_id, category, topic, title, content, tags, source)
        self.knowledge_items[item_id] = item
        self.category_index.setdefault(category, []).append(item_id)
        for tag in tags:
            self.tag_index.setdefault(tag, []).append(item_id)
        return item_id

    def get_stats(self) -> Dict:
        return {
            "total_items": len(self.knowledge_items),
            "categories": len(self.category_index),
            "tags": len(self.tag_index),
        }

    def search(self, query: str, category: Optional[str] = None, top_k: int = 5) -> List[Tuple[KnowledgeItem, float]]:
        query_lower = query.lower()
        candidates = self.knowledge_items.values()
        if category:
            candidates = [self.knowledge_items[item_id] for item_id in self.category_index.get(category, [])]
        scored = []
        for item in candidates:
            haystack = f"{item.title} {item.content} {' '.join(item.tags)} {item.topic}".lower()
            score = haystack.count(query_lower)
            if score > 0 or query_lower in haystack:
                scored.append((item, float(score or 1)))
        scored.sort(key=lambda entry: entry[1], reverse=True)
        return scored[:top_k]

    def increment_usage(self, item_id: str) -> None:
        if item_id in self.knowledge_items:
            self.knowledge_items[item_id].usage_count += 1

    def get_by_category(self, category: str) -> List[KnowledgeItem]:
        return [self.knowledge_items[item_id] for item_id in self.category_index.get(category, [])]

    def save(self) -> None:
        return None


_KB = KnowledgeBase()


def get_knowledge_base() -> KnowledgeBase:
    return _KB
