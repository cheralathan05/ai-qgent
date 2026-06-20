"""Knowledge Graph Engine for Phase 3."""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    PROJECT = "project"
    TASK = "task"
    FILE = "file"
    CONCEPT = "concept"
    MEETING = "meeting"
    GOAL = "goal"
    EVENT = "event"
    APP = "app"
    DEVICE = "device"
    REPOSITORY = "repository"
    SKILL = "skill"
    NOTE = "note"
    DOCUMENT = "document"


class RelationshipType(str, Enum):
    CREATED = "created"
    OWNS = "owns"
    WORKS_ON = "works_on"
    CONTAINS = "contains"
    RELATED_TO = "related_to"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    PART_OF = "part_of"
    LEADS = "leads"
    ATTENDED = "attended"
    BUILT = "built"
    LEARNED = "learned"


@dataclass
class KnowledgeEntity:
    id: str
    name: str
    type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KnowledgeRelationship:
    id: str
    source_id: str
    target_id: str
    type: RelationshipType
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class KnowledgeGraph:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_graph")
        os.makedirs(self.storage_path, exist_ok=True)
        self._entities: Dict[str, KnowledgeEntity] = {}
        self._relationships: Dict[str, KnowledgeRelationship] = {}
        self._adjacency: Dict[str, Set[str]] = {}
        self._load()

    def _entities_path(self):
        return os.path.join(self.storage_path, "entities.json")

    def _relationships_path(self):
        return os.path.join(self.storage_path, "relationships.json")

    def _load(self):
        try:
            if os.path.exists(self._entities_path()):
                with open(self._entities_path(), 'r') as f:
                    data = json.load(f)
                    for e in data:
                        entity = KnowledgeEntity(**e)
                        self._entities[entity.id] = entity
            if os.path.exists(self._relationships_path()):
                with open(self._relationships_path(), 'r') as f:
                    data = json.load(f)
                    for r in data:
                        rel = KnowledgeRelationship(**r)
                        self._relationships[rel.id] = rel
                        if rel.source_id not in self._adjacency:
                            self._adjacency[rel.source_id] = set()
                        self._adjacency[rel.source_id].add(rel.target_id)
            logger.info(f"Loaded {len(self._entities)} entities, {len(self._relationships)} relationships")
        except Exception as e:
            logger.warning(f"Failed to load knowledge graph: {e}")

    def _save(self):
        try:
            with open(self._entities_path(), 'w') as f:
                json.dump([asdict(e) for e in self._entities.values()], f, default=str)
            with open(self._relationships_path(), 'w') as f:
                json.dump([asdict(r) for r in self._relationships.values()], f, default=str)
        except Exception as e:
            logger.error(f"Failed to save knowledge graph: {e}")

    def add_entity(self, entity: KnowledgeEntity) -> KnowledgeEntity:
        self._entities[entity.id] = entity
        self._save()
        return entity

    def add_relationship(self, relationship: KnowledgeRelationship) -> KnowledgeRelationship:
        self._relationships[relationship.id] = relationship
        if relationship.source_id not in self._adjacency:
            self._adjacency[relationship.source_id] = set()
        self._adjacency[relationship.source_id].add(relationship.target_id)
        self._save()
        return relationship

    def create_entity(self, name: str, entity_type: EntityType, properties: Dict = None) -> KnowledgeEntity:
        import uuid
        entity = KnowledgeEntity(
            id=str(uuid.uuid4()),
            name=name,
            type=entity_type,
            properties=properties or {},
        )
        return self.add_entity(entity)

    def create_relationship(self, source_id: str, target_id: str, rel_type: RelationshipType, properties: Dict = None) -> KnowledgeRelationship:
        import uuid
        rel = KnowledgeRelationship(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            properties=properties or {},
        )
        return self.add_relationship(rel)

    def get_entity(self, entity_id: str) -> Optional[KnowledgeEntity]:
        return self._entities.get(entity_id)

    def find_entity(self, name: str, entity_type: Optional[EntityType] = None) -> Optional[KnowledgeEntity]:
        name_lower = name.lower()
        for e in self._entities.values():
            if e.name.lower() == name_lower:
                if entity_type is None or e.type == entity_type:
                    return e
            if name_lower in e.name.lower():
                if entity_type is None or e.type == entity_type:
                    return e
        return None

    def search_entities(self, query: str) -> List[KnowledgeEntity]:
        q = query.lower()
        return [
            e for e in self._entities.values()
            if q in e.name.lower() or q in (e.type.value if hasattr(e.type, 'value') else str(e.type)).lower()
        ]

    def get_relationships(self, entity_id: str) -> List[KnowledgeRelationship]:
        return [
            r for r in self._relationships.values()
            if r.source_id == entity_id or r.target_id == entity_id
        ]

    def get_connected_entities(self, entity_id: str, max_depth: int = 2) -> List[KnowledgeEntity]:
        visited: Set[str] = set()
        queue = [(entity_id, 0)]
        results = []

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            if current_id != entity_id:
                entity = self._entities.get(current_id)
                if entity:
                    results.append(entity)

            for rel in self._relationships.values():
                if rel.source_id == current_id and rel.target_id not in visited:
                    queue.append((rel.target_id, depth + 1))
                if rel.target_id == current_id and rel.source_id not in visited:
                    queue.append((rel.source_id, depth + 1))

        return results

    def get_all_entities(self) -> List[KnowledgeEntity]:
        return list(self._entities.values())

    def get_all_relationships(self) -> List[KnowledgeRelationship]:
        return list(self._relationships.values())

    def get_entity_count(self) -> int:
        return len(self._entities)

    def get_relationship_count(self) -> int:
        return len(self._relationships)

    def get_entity_types(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self._entities.values():
            t = e.type.value if hasattr(e.type, 'value') else str(e.type)
            counts[t] = counts.get(t, 0) + 1
        return counts

    def get_subgraph(self, entity_id: str, depth: int = 1) -> Dict[str, Any]:
        entities = self.get_connected_entities(entity_id, depth)
        entity_ids = {e.id for e in entities} | {entity_id}
        relationships = [
            r for r in self._relationships.values()
            if r.source_id in entity_ids and r.target_id in entity_ids
        ]
        return {
            "center": self._entities.get(entity_id),
            "entities": entities,
            "relationships": relationships,
            "total_entities": len(entities) + 1,
            "total_relationships": len(relationships),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": len(self._entities),
            "relationships": len(self._relationships),
            "entity_types": self.get_entity_types(),
        }


_knowledge_graph: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
