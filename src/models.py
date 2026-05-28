from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Union


def _normalize_string_list(items: list) -> list[str]:
    """标准化列表元素为字符串。
    LLM 可能返回 ["param: type"] 或 [{"name": "param", "type": "type"}]，
    统一转为 ["param: type"]。
    """
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            name = item.get("name", item.get("key", ""))
            ptype = item.get("type", "")
            if name and ptype:
                result.append(f"{name}: {ptype}")
            elif name:
                result.append(name)
        else:
            result.append(str(item))
    return result


@dataclass
class Attribute:
    name: str
    type: str = "str"
    visibility: str = "public"

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type, "visibility": self.visibility}

    @staticmethod
    def from_dict(d: dict) -> "Attribute":
        return Attribute(
            name=d.get("name", ""),
            type=d.get("type", "str"),
            visibility=d.get("visibility", "public"),
        )


@dataclass
class Method:
    name: str
    parameters: list[str] = field(default_factory=list)
    return_type: str = "void"
    visibility: str = "public"

    def to_dict(self) -> dict:
        return {"name": self.name, "parameters": self.parameters,
                "return_type": self.return_type, "visibility": self.visibility}

    @staticmethod
    def from_dict(d: dict) -> "Method":
        params = _normalize_string_list(d.get("parameters", []))
        return Method(
            name=d.get("name", ""), parameters=params,
            return_type=d.get("return_type", "void"),
            visibility=d.get("visibility", "public"),
        )


@dataclass
class Relationship:
    type: str  # inheritance, association, aggregation, composition, dependency
    target: str
    label: str = ""
    multiplicity: str = ""

    def to_dict(self) -> dict:
        return {"type": self.type, "target": self.target,
                "label": self.label, "multiplicity": self.multiplicity}

    @staticmethod
    def from_dict(d: dict) -> "Relationship":
        return Relationship(
            type=d.get("type", "association"), target=d.get("target", ""),
            label=d.get("label", ""), multiplicity=d.get("multiplicity", ""),
        )


@dataclass
class Entity:
    name: str
    attributes: list[Attribute] = field(default_factory=list)
    methods: list[Method] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "attributes": [a.to_dict() for a in self.attributes],
            "methods": [m.to_dict() for m in self.methods],
            "relationships": [r.to_dict() for r in self.relationships],
        }

    @staticmethod
    def from_dict(d: dict) -> "Entity":
        return Entity(
            name=d.get("name", ""),
            attributes=[Attribute.from_dict(a) for a in d.get("attributes", [])],
            methods=[Method.from_dict(m) for m in d.get("methods", [])],
            relationships=[Relationship.from_dict(r) for r in d.get("relationships", [])],
        )


@dataclass
class Step:
    order: int
    action: str
    actor: str = ""
    branches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"order": self.order, "action": self.action,
                "actor": self.actor, "branches": self.branches}

    @staticmethod
    def from_dict(d: dict) -> "Step":
        branches = _normalize_string_list(d.get("branches", []))
        return Step(
            order=d.get("order", 0), action=d.get("action", ""),
            actor=d.get("actor", ""), branches=branches,
        )


@dataclass
class Behavior:
    name: str
    description: str = ""
    steps: list[Step] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "preconditions": self.preconditions, "postconditions": self.postconditions,
        }

    @staticmethod
    def from_dict(d: dict) -> "Behavior":
        return Behavior(
            name=d.get("name", ""), description=d.get("description", ""),
            steps=[Step.from_dict(s) for s in d.get("steps", [])],
            preconditions=_normalize_string_list(d.get("preconditions", [])),
            postconditions=_normalize_string_list(d.get("postconditions", [])),
        )


@dataclass
class Constraint:
    description: str
    type: str = ""   # invariant, pre-condition, post-condition, business-rule
    scope: str = ""

    def to_dict(self) -> dict:
        return {"description": self.description, "type": self.type, "scope": self.scope}

    @staticmethod
    def from_dict(d: dict) -> "Constraint":
        return Constraint(
            description=d.get("description", ""), type=d.get("type", ""), scope=d.get("scope", ""),
        )


@dataclass
class AnalysisResult:
    entities: list[Entity] = field(default_factory=list)
    behaviors: list[Behavior] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "entities": [e.to_dict() for e in self.entities],
            "behaviors": [b.to_dict() for b in self.behaviors],
            "constraints": [c.to_dict() for c in self.constraints],
        }

    def to_file(self, path: str) -> None:
        import json
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def from_file(path: str) -> "AnalysisResult":
        import json
        from pathlib import Path
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return AnalysisResult(
            summary=data.get("summary", ""),
            entities=[Entity.from_dict(e) for e in data.get("entities", [])],
            behaviors=[Behavior.from_dict(b) for b in data.get("behaviors", [])],
            constraints=[Constraint.from_dict(c) for c in data.get("constraints", [])],
        )

    def preview_text(self) -> str:
        lines = [f"实体 ({len(self.entities)}个):"]
        for i, e in enumerate(self.entities):
            rels = ", ".join(f"{r.type}→{r.target}" for r in e.relationships) or "无"
            lines.append(f"  {i+1}. {e.name} ({len(e.attributes)}属性, {len(e.methods)}方法) [{rels}]")
        lines.append(f"\n行为 ({len(self.behaviors)}个):")
        for i, b in enumerate(self.behaviors):
            lines.append(f"  {i+1}. {b.name} ({len(b.steps)}步) - {b.description}")
        lines.append(f"\n约束 ({len(self.constraints)}个):")
        for i, c in enumerate(self.constraints):
            lines.append(f"  {i+1}. [{c.type}] {c.description}")
        return "\n".join(lines)

    def has_stateful_entities(self) -> bool:
        return any(
            any(r.type == "stateful" for r in e.relationships)
            or any("状态" in a.name or "status" in a.name.lower() or "state" in a.name.lower() for a in e.attributes)
            for e in self.entities
        )


@dataclass
class MermaidDiagram:
    diagram_type: str  # classDiagram, stateDiagram-v2, flowchart, sequenceDiagram
    source_code: str
    title: str = ""

    def validate(self) -> bool:
        if not self.source_code.strip():
            return False
        code = self.source_code.strip()
        valid_starts = [
            "classDiagram", "stateDiagram", "stateDiagram-v2",
            "flowchart", "sequenceDiagram", "graph",
            "erDiagram", "gantt", "pie", "gitGraph",
        ]
        return any(code.startswith(start) for start in valid_starts)

    def to_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.source_code)


@dataclass
class DesignOutput:
    analysis: AnalysisResult = field(default_factory=AnalysisResult)
    class_diagram: Optional[MermaidDiagram] = None
    activity_diagrams: list[MermaidDiagram] = field(default_factory=list)
    state_diagrams: list[MermaidDiagram] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    input_doc_name: str = ""
