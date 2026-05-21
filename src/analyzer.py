import json
import re
from src.llm_adapter import LLMAdapter
from src.models import AnalysisResult, Entity, Behavior, Constraint


ANALYSIS_SYSTEM = """你是系统分析师。从需求文档提取信息，只输出JSON：

{
  "summary": "2-3句话概述",
  "entities": [
    {
      "name": "实体名(英文PascalCase)",
      "attributes": [{"name": "属性中文名", "type": "类型", "visibility": "public"}],
      "methods": [{"name": "方法中文名", "parameters": ["参数1: 类型"], "return_type": "返回值", "visibility": "public"}],
      "relationships": [{"type": "association", "target": "目标实体", "label": "关系", "multiplicity": "1"}]
    }
  ],
  "behaviors": [
    {
      "name": "流程名",
      "description": "一句话描述",
      "preconditions": ["前置条件"],
      "postconditions": ["后置条件"],
      "steps": [{"order":1, "action":"步骤", "actor":"角色", "branches":[]}]
    }
  ],
  "constraints": [{"description": "约束", "type": "business-rule", "scope": "范围"}]
}

每个实体至少2属性2方法。每个行为至少3步。只输出JSON。"""


class RequirementAnalyzer:

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def analyze(self, document: str) -> AnalysisResult:
        print("  (单次分析，模型思考中请等待)...")
        response = self.llm.chat(
            prompt=f"分析以下需求文档，提取实体、行为、约束：\n\n{document}",
            system=ANALYSIS_SYSTEM,
        )
        data = self._parse_json(response)
        if not data:
            return AnalysisResult(summary=f"JSON解析失败\n\n原始响应:\n```\n{response[:2000]}\n```")

        entities = []
        for e in data.get("entities", []):
            if isinstance(e, dict):
                try:
                    ent = Entity.from_dict(e)
                    if ent.name:
                        entities.append(ent)
                except Exception:
                    pass

        behaviors = []
        for b in data.get("behaviors", []):
            if isinstance(b, dict):
                try:
                    beh = Behavior.from_dict(b)
                    if beh.name:
                        behaviors.append(beh)
                except Exception:
                    pass

        constraints = []
        for c in data.get("constraints", []):
            if isinstance(c, dict):
                try:
                    con = Constraint.from_dict(c)
                    if con.description:
                        constraints.append(con)
                except Exception:
                    pass

        return AnalysisResult(
            summary=data.get("summary", ""),
            entities=entities,
            behaviors=behaviors,
            constraints=constraints,
        )

    def _parse_json(self, text: str) -> dict | None:
        json_str = self._extract_json(text)
        if not json_str:
            return None
        for _ in range(3):
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                json_str = self._repair_json(json_str)
        return None

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if m:
            text = m.group(1).strip()
        m = re.search(r'\{[\s\S]*\}', text)
        return m.group(0) if m else ""

    def _repair_json(self, s: str) -> str:
        s = re.sub(r',\s*}', '}', s)
        s = re.sub(r',\s*]', ']', s)
        return s + ']' * (s.count('[') - s.count(']')) + '}' * (s.count('{') - s.count('}'))
