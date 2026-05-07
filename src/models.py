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

    @staticmethod
    def from_dict(d: dict) -> "Method":
        params = _normalize_string_list(d.get("parameters", []))
        return Method(
            name=d.get("name", ""),
            parameters=params,
            return_type=d.get("return_type", "void"),
            visibility=d.get("visibility", "public"),
        )


@dataclass
class Relationship:
    type: str  # inheritance, association, aggregation, composition, dependency
    target: str
    label: str = ""
    multiplicity: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Relationship":
        return Relationship(
            type=d.get("type", "association"),
            target=d.get("target", ""),
            label=d.get("label", ""),
            multiplicity=d.get("multiplicity", ""),
        )


@dataclass
class Entity:
    name: str
    attributes: list[Attribute] = field(default_factory=list)
    methods: list[Method] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

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

    @staticmethod
    def from_dict(d: dict) -> "Step":
        branches = _normalize_string_list(d.get("branches", []))
        return Step(
            order=d.get("order", 0),
            action=d.get("action", ""),
            actor=d.get("actor", ""),
            branches=branches,
        )


@dataclass
class Behavior:
    name: str
    description: str = ""
    steps: list[Step] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "Behavior":
        return Behavior(
            name=d.get("name", ""),
            description=d.get("description", ""),
            steps=[Step.from_dict(s) for s in d.get("steps", [])],
            preconditions=_normalize_string_list(d.get("preconditions", [])),
            postconditions=_normalize_string_list(d.get("postconditions", [])),
        )


@dataclass
class Constraint:
    description: str
    type: str = ""   # invariant, pre-condition, post-condition, business-rule
    scope: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Constraint":
        return Constraint(
            description=d.get("description", ""),
            type=d.get("type", ""),
            scope=d.get("scope", ""),
        )


@dataclass
class AnalysisResult:
    entities: list[Entity] = field(default_factory=list)
    behaviors: list[Behavior] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    summary: str = ""

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
