import concurrent.futures
import json
import re
from src.llm_adapter import LLMAdapter
from src.models import AnalysisResult, Entity, Behavior, Constraint


SKELETON_SYSTEM = """你是系统分析师。从需求文档提取骨架信息，只输出JSON：

{
  "summary": "2-3句话概述系统",
  "entities": ["实体1", "实体2"],
  "behaviors": [{"name": "流程名", "description": "一句话描述"}],
  "constraints": [{"description": "约束", "type": "business-rule", "scope": "范围"}]
}

实体名用英文PascalCase。只输出JSON。"""

# 注意：system prompt 完全固定，可变信息放 user message 里，
# 这样 DeepSeek 可以对所有同类请求共享缓存前缀。
ENTITY_SYSTEM = """为指定实体补充属性、方法、关系。只输出JSON：
{
  "name": "实体名",
  "attributes": [{"name": "属性中文名", "type": "类型", "visibility": "public"}],
  "methods": [{"name": "方法中文名", "parameters": ["参数1: 类型"], "return_type": "返回值", "visibility": "public"}],
  "relationships": [{"type": "association", "target": "其他实体名", "label": "关系说明", "multiplicity": "1"}]
}
至少2属性2方法。关系只关联到给出的实体列表中的实体。只输出JSON。"""

BEHAVIOR_SYSTEM = """为指定业务流程补充步骤，只输出JSON：
{
  "name": "流程名",
  "description": "描述",
  "preconditions": ["前置条件"],
  "postconditions": ["后置条件"],
  "steps": [{"order":1, "action":"步骤", "actor":"角色", "branches":[]}]
}
至少3步。只输出JSON。"""


class RequirementAnalyzer:

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def analyze(self, document: str) -> AnalysisResult:
        # 第1步：快速提取骨架
        print("  提取骨架...", end=" ", flush=True)
        skeleton = self._call_llm_json(
            prompt=f"分析以下需求文档：\n\n{document}",
            system=SKELETON_SYSTEM,
        )
        if not skeleton:
            print("失败")
            return AnalysisResult(summary="骨架提取失败")
        entity_names = skeleton.get("entities", [])
        behaviors_raw = skeleton.get("behaviors", [])
        print(f"({len(entity_names)}实体, {len(behaviors_raw)}行为)")

        # 第2步：并发填充细节
        all_names = ", ".join(entity_names)
        entities = []
        behaviors = []
        constraints = [Constraint.from_dict(c) for c in skeleton.get("constraints", [])]

        n_entity = len(entity_names)
        n_behavior = len(behaviors_raw)
        total = n_entity + n_behavior

        if total == 0:
            return AnalysisResult(summary=skeleton.get("summary", ""))

        print(f"  填充细节 ({total}个任务并发)...", end=" ", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, total)) as pool:
            future_to_type = {}

            for name in entity_names:
                f = pool.submit(self._fill_entity, document, name, all_names)
                future_to_type[f] = ("entity", name)

            for b in behaviors_raw:
                f = pool.submit(self._fill_behavior, document, b.get("name", ""), b.get("description", ""))
                future_to_type[f] = ("behavior", b.get("name", ""))

            entity_results = {}
            behavior_results = {}
            done = 0
            for future in concurrent.futures.as_completed(future_to_type):
                typ, name = future_to_type[future]
                done += 1
                try:
                    result = future.result()
                    if typ == "entity" and result:
                        entity_results[name] = result
                    elif typ == "behavior" and result:
                        behavior_results[name] = result
                except Exception as e:
                    print(f"[{name}:{e}]", end="")

            entities = [entity_results[k] for k in entity_names if k in entity_results]
            behaviors = [behavior_results[k] for k in [b.get("name", "") for b in behaviors_raw] if k in behavior_results]

        print(f"完成 ({len(entities)}实体, {len(behaviors)}行为)")

        return AnalysisResult(
            summary=skeleton.get("summary", ""),
            entities=entities,
            behaviors=behaviors,
            constraints=constraints,
        )

    def _fill_entity(self, document: str, name: str, all_names: str):
        # 文档在前(共享缓存前缀)，实体信息在后(可变部分)
        data = self._call_llm_json(
            prompt=f"{document}\n\n---\n为实体「{name}」补充细节。系统中共有实体：{all_names}",
            system=ENTITY_SYSTEM,
        )
        if data:
            data["name"] = data.get("name", name)
            try:
                return Entity.from_dict(data)
            except Exception as e:
                print(f"[{name}.from_dict:{e}]", end="")
        return None

    def _fill_behavior(self, document: str, name: str, description: str):
        # 文档在前(共享缓存前缀)，流程信息在后(可变部分)
        data = self._call_llm_json(
            prompt=f"{document}\n\n---\n为流程「{name}」（{description}）补充步骤。",
            system=BEHAVIOR_SYSTEM,
        )
        if data:
            data["name"] = data.get("name", name)
            data["description"] = data.get("description", description)
            try:
                return Behavior.from_dict(data)
            except Exception as e:
                print(f"[{name}.from_dict:{e}]", end="")
        return None

    def _call_llm_json(self, prompt: str, system: str) -> dict | None:
        try:
            response = self.llm.chat(prompt=prompt, system=system)
        except Exception as e:
            print(f"[API:{e}]", end="")
            return None
        return self._parse_json(response)

    def _parse_json(self, text: str) -> dict | None:
        json_str = self._extract_json(text)
        if not json_str:
            return None

        for attempt in range(3):
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                if attempt == 0:
                    json_str = self._repair_json(json_str)
                elif attempt == 1:
                    repaired = self._llm_repair(json_str)
                    if repaired:
                        json_str = repaired
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
        bc = s.count('{') - s.count('}')
        brc = s.count('[') - s.count(']')
        return s + ']' * brc + '}' * bc

    def _llm_repair(self, broken: str) -> str | None:
        try:
            response = self.llm.chat(prompt=f"修复JSON，只输出正确JSON：\n```json\n{broken}\n```")
            return self._extract_json(response)
        except Exception:
            return None
