"""Smart Context - Project knowledge graph and semantic learning."""

import json
import time
from pathlib import Path
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class Entity:
    """A semantic entity in the project (class, function, pattern, etc.)."""
    id: str
    type: str  # class, function, module, pattern, concept
    name: str
    file_path: Optional[str]
    description: str
    first_seen: float
    last_accessed: float
    access_count: int
    tags: List[str]
    metadata: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Entity':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Relationship:
    """A relationship between two entities."""
    source_id: str
    target_id: str
    type: str  # uses, imports, extends, calls, related_to
    strength: float  # 0.0 to 1.0
    context: str
    created_at: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Relationship':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConversationMemory:
    """Stores conversation context and learnings."""
    topic: str
    summary: str
    entities_discussed: List[str]
    decisions_made: List[str]
    timestamp: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConversationMemory':
        """Create from dictionary."""
        return cls(**data)


class ProjectKnowledgeGraph:
    """Builds and maintains semantic knowledge about the project."""
    
    def __init__(self, flux_dir: Path):
        """Initialize knowledge graph.
        
        Args:
            flux_dir: Flux configuration directory
        """
        self.flux_dir = flux_dir
        self.graph_file = flux_dir / "knowledge_graph.json"
        
        # Core data structures
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.conversations: List[ConversationMemory] = []
        self.patterns: Dict[str, List[str]] = defaultdict(list)  # pattern -> entity IDs
        
        # Load existing graph
        self._load()
    
    def learn_from_code(self, file_path: str, content: str, language: str = "python"):
        """Extract entities and relationships from code.
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
        """
        if language == "python":
            self._learn_from_python(file_path, content)
    
    def _learn_from_python(self, file_path: str, content: str):
        """Extract Python classes, functions, and patterns."""
        import re
        
        # Extract classes
        class_pattern = r'^class\s+(\w+)(?:\(([\w,\s]+)\))?:'
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            bases = match.group(2) if match.group(2) else None
            
            entity_id = f"class:{file_path}:{class_name}"
            
            if entity_id not in self.entities:
                self.entities[entity_id] = Entity(
                    id=entity_id,
                    type="class",
                    name=class_name,
                    file_path=file_path,
                    description=f"Class {class_name} in {file_path}",
                    first_seen=time.time(),
                    last_accessed=time.time(),
                    access_count=1,
                    tags=[],
                    metadata={'bases': bases}
                )
            else:
                self.entities[entity_id].last_accessed = time.time()
                self.entities[entity_id].access_count += 1
            
            # Add inheritance relationships
            if bases:
                for base in bases.split(','):
                    base = base.strip()
                    base_id = f"class:*:{base}"  # Unknown file for now
                    self.add_relationship(entity_id, base_id, "extends", 1.0, f"{class_name} extends {base}")
        
        # Extract functions
        func_pattern = r'^(?:async\s+)?def\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            func_name = match.group(1)
            
            entity_id = f"function:{file_path}:{func_name}"
            
            if entity_id not in self.entities:
                self.entities[entity_id] = Entity(
                    id=entity_id,
                    type="function",
                    name=func_name,
                    file_path=file_path,
                    description=f"Function {func_name} in {file_path}",
                    first_seen=time.time(),
                    last_accessed=time.time(),
                    access_count=1,
                    tags=[],
                    metadata={}
                )
            else:
                self.entities[entity_id].last_accessed = time.time()
                self.entities[entity_id].access_count += 1
        
        # Extract imports (creates relationships)
        import_pattern = r'^(?:from\s+([\w.]+)\s+)?import\s+([\w,\s]+)'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            module = match.group(1) if match.group(1) else ""
            imports = match.group(2)
            
            for imp in imports.split(','):
                imp = imp.strip()
                if module:
                    target_id = f"module:*:{module}.{imp}"
                else:
                    target_id = f"module:*:{imp}"
                
                # Create relationship from file to imported module
                file_id = f"module:{file_path}:{Path(file_path).stem}"
                self.add_relationship(file_id, target_id, "imports", 0.8, f"{file_path} imports {imp}")
    
    def learn_from_conversation(
        self,
        topic: str,
        user_message: str,
        assistant_message: str,
        entities_mentioned: List[str] = None
    ):
        """Learn from conversation interactions.
        
        Args:
            topic: Conversation topic/intent
            user_message: User's message
            assistant_message: Assistant's response
            entities_mentioned: List of entity IDs discussed
        """
        # Extract key decisions or actions
        decisions = []
        if "decided" in assistant_message.lower() or "will" in assistant_message.lower():
            # Simple heuristic - could be improved with LLM extraction
            decisions.append(assistant_message[:200])
        
        # Create conversation memory
        memory = ConversationMemory(
            topic=topic,
            summary=f"User: {user_message[:100]}... | Assistant: {assistant_message[:100]}...",
            entities_discussed=entities_mentioned or [],
            decisions_made=decisions,
            timestamp=time.time()
        )
        
        self.conversations.append(memory)
        
        # Update entity access patterns
        for entity_id in (entities_mentioned or []):
            if entity_id in self.entities:
                self.entities[entity_id].last_accessed = time.time()
                self.entities[entity_id].access_count += 1
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        strength: float,
        context: str
    ):
        """Add a relationship between entities."""
        # Check if relationship exists
        for rel in self.relationships:
            if rel.source_id == source_id and rel.target_id == target_id and rel.type == rel_type:
                # Update strength (average with new strength)
                rel.strength = (rel.strength + strength) / 2
                return
        
        # Create new relationship
        self.relationships.append(Relationship(
            source_id=source_id,
            target_id=target_id,
            type=rel_type,
            strength=strength,
            context=context,
            created_at=time.time()
        ))
    
    def register_pattern(self, pattern_name: str, entity_ids: List[str]):
        """Register a design pattern with associated entities.
        
        Args:
            pattern_name: Name of the pattern (e.g., "singleton", "factory")
            entity_ids: Entity IDs involved in this pattern
        """
        self.patterns[pattern_name].extend(entity_ids)
    
    def get_relevant_context(
        self,
        query: str,
        file_paths: List[str] = None,
        limit: int = 10
    ) -> Dict:
        """Get relevant context for a query.
        
        Args:
            query: User's query or intent
            file_paths: Files currently being worked on
            limit: Max entities to return
            
        Returns:
            Dictionary with relevant entities, relationships, and conversations
        """
        query_lower = query.lower()
        relevant_entities = []
        
        # Score entities by relevance
        for entity_id, entity in self.entities.items():
            score = 0.0
            
            # Name match
            if entity.name.lower() in query_lower or query_lower in entity.name.lower():
                score += 2.0
            
            # File path match
            if file_paths and entity.file_path:
                if any(fp in entity.file_path for fp in file_paths):
                    score += 1.5
            
            # Tag match
            for tag in entity.tags:
                if tag.lower() in query_lower:
                    score += 1.0
            
            # Recent access boost
            time_since_access = time.time() - entity.last_accessed
            if time_since_access < 3600:  # Last hour
                score += 0.5
            
            # Access frequency boost
            if entity.access_count > 5:
                score += 0.3
            
            if score > 0:
                relevant_entities.append((score, entity))
        
        # Sort by score and limit
        relevant_entities.sort(reverse=True, key=lambda x: x[0])
        relevant_entities = [e for _, e in relevant_entities[:limit]]
        
        # Get related relationships
        entity_ids = {e.id for e in relevant_entities}
        relevant_relationships = [
            r for r in self.relationships
            if r.source_id in entity_ids or r.target_id in entity_ids
        ]
        
        # Get recent conversations about these entities
        relevant_conversations = []
        for conv in reversed(self.conversations[-50:]):  # Last 50 conversations
            if any(eid in conv.entities_discussed for eid in entity_ids):
                relevant_conversations.append(conv)
                if len(relevant_conversations) >= 5:
                    break
        
        return {
            'entities': [e.to_dict() for e in relevant_entities],
            'relationships': [r.to_dict() for r in relevant_relationships],
            'conversations': [c.to_dict() for c in relevant_conversations],
            'total_entities': len(self.entities),
            'total_relationships': len(self.relationships)
        }
    
    def get_entity_neighbors(self, entity_id: str, max_depth: int = 2) -> Set[str]:
        """Get all entities connected to this entity.
        
        Args:
            entity_id: Starting entity ID
            max_depth: Maximum relationship depth to traverse
            
        Returns:
            Set of connected entity IDs
        """
        visited = set()
        queue = [(entity_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # Find connected entities
            for rel in self.relationships:
                if rel.source_id == current_id and rel.target_id not in visited:
                    queue.append((rel.target_id, depth + 1))
                elif rel.target_id == current_id and rel.source_id not in visited:
                    queue.append((rel.source_id, depth + 1))
        
        return visited
    
    def get_stats(self) -> Dict:
        """Get knowledge graph statistics."""
        entity_types = defaultdict(int)
        for entity in self.entities.values():
            entity_types[entity.type] += 1
        
        relationship_types = defaultdict(int)
        for rel in self.relationships:
            relationship_types[rel.type] += 1
        
        return {
            'total_entities': len(self.entities),
            'total_relationships': len(self.relationships),
            'total_conversations': len(self.conversations),
            'total_patterns': len(self.patterns),
            'entity_types': dict(entity_types),
            'relationship_types': dict(relationship_types),
            'most_accessed_entities': sorted(
                [{'name': e.name, 'count': e.access_count} for e in self.entities.values()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]
        }
    
    def save(self):
        """Save knowledge graph to disk."""
        data = {
            'entities': {eid: e.to_dict() for eid, e in self.entities.items()},
            'relationships': [r.to_dict() for r in self.relationships],
            'conversations': [c.to_dict() for c in self.conversations[-100:]],  # Keep last 100
            'patterns': dict(self.patterns)
        }
        
        with open(self.graph_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load(self):
        """Load knowledge graph from disk."""
        if not self.graph_file.exists():
            return
        
        try:
            with open(self.graph_file, 'r') as f:
                data = json.load(f)
            
            self.entities = {
                eid: Entity.from_dict(e) for eid, e in data.get('entities', {}).items()
            }
            self.relationships = [
                Relationship.from_dict(r) for r in data.get('relationships', [])
            ]
            self.conversations = [
                ConversationMemory.from_dict(c) for c in data.get('conversations', [])
            ]
            self.patterns = defaultdict(list, data.get('patterns', {}))
        except Exception:
            pass
    
    def export_for_sharing(self, output_file: Path):
        """Export knowledge graph for team sharing.
        
        Args:
            output_file: Path to export file
        """
        # Export everything except conversation history (privacy)
        data = {
            'entities': {eid: e.to_dict() for eid, e in self.entities.items()},
            'relationships': [r.to_dict() for r in self.relationships],
            'patterns': dict(self.patterns),
            'stats': self.get_stats()
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_shared_graph(self, import_file: Path):
        """Import knowledge graph from team member.
        
        Args:
            import_file: Path to import file
        """
        try:
            with open(import_file, 'r') as f:
                data = json.load(f)
            
            # Merge entities
            for eid, entity_dict in data.get('entities', {}).items():
                if eid not in self.entities:
                    self.entities[eid] = Entity.from_dict(entity_dict)
            
            # Merge relationships
            existing_rels = {
                (r.source_id, r.target_id, r.type) for r in self.relationships
            }
            for rel_dict in data.get('relationships', []):
                rel = Relationship.from_dict(rel_dict)
                if (rel.source_id, rel.target_id, rel.type) not in existing_rels:
                    self.relationships.append(rel)
            
            # Merge patterns
            for pattern, entity_ids in data.get('patterns', {}).items():
                self.patterns[pattern].extend(entity_ids)
            
            self.save()
        except Exception:
            pass
