import re
from src.llm_adapter import LLMAdapter
from src.models import AnalysisResult, Behavior, MermaidDiagram


CLASS_DIAGRAM_SYSTEM = """你是一位 UML 建模专家。根据需求分析结果生成 Mermaid classDiagram。

规则：
1. 类名使用英文大驼峰命名
2. 属性名和方法名使用中文描述
3. 关系标注使用中文
4. 使用标准 UML 关系：<|-- 继承, *-- 组合, o-- 聚合, --> 关联, ..> 依赖
5. 只输出 ```mermaid 代码块，不要其他内容"""

CLASS_DIAGRAM_PROMPT = """请根据以下分析结果生成 Mermaid 类图，属性和方法使用中文命名。

## 实体列表：
{entities}

## 实体关系：
{relationships}

属性名和方法名使用中文，关系标注使用中文。只输出 mermaid 代码块。"""


ACTIVITY_DIAGRAM_SYSTEM = """你是一位业务流程建模专家。你的任务是根据行为描述生成 Mermaid 活动图。

规则：
1. 使用 stateDiagram-v2 格式（Mermaid 推荐的活动图格式）
2. 每个状态代表一个活动步骤
3. 转换线上标注条件或触发事件
4. 包含 [*] 开始和结束状态
5. 对于条件分支，使用 <<choice>> 节点或直接在转换线上标注条件
6. 只输出代码块，以 ```mermaid 开头，``` 结尾"""

ACTIVITY_DIAGRAM_PROMPT = """请根据以下业务流程描述生成 Mermaid 活动图。

## 流程名称：{name}
## 流程描述：{description}
## 前置条件：{preconditions}
## 后置条件：{postconditions}
## 步骤：
{steps}

生成 stateDiagram-v2 格式的活动图，用状态节点表示每个步骤，
转换线标注条件和触发条件。只输出 mermaid 代码块。"""


STATE_DIAGRAM_SYSTEM = """你是一位状态机建模专家。根据实体描述生成 Mermaid 状态机图。

规则：
1. 使用 stateDiagram-v2 格式
2. 状态名和转换说明必须使用中文
3. 识别实体在其生命周期中的各种状态
4. 定义状态之间的转换条件
5. 包含 [*] 初始状态和结束状态
6. 只输出代码块，以 ```mermaid 开头，``` 结尾"""

STATE_DIAGRAM_PROMPT = """请根据以下实体描述生成 Mermaid 状态机图，状态名和注释全部使用中文。

## 实体名称：{name}
## 实体属性：
{attributes}

## 实体方法：
{methods}

## 相关约束：
{constraints}

分析该实体在其生命周期中可能经历的状态，用中文命名每个状态和转换条件，生成 stateDiagram-v2 格式的状态机图。
只输出 mermaid 代码块。"""


def _extract_mermaid_block(text: str) -> str:
    """从 LLM 响应中提取 Mermaid 代码块。"""
    match = re.search(r'```mermaid\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    match = re.search(r'```\s*(classDiagram|stateDiagram[\s\S]*?)```', text)
    if match:
        return match.group(0).replace("```", "").strip()
    if text.strip().startswith("classDiagram") or text.strip().startswith("stateDiagram"):
        return text.strip()
    return text.strip()


def _validate_and_repair_mermaid(code: str, diagram_type: str) -> str:
    """校验并尝试修复 Mermaid 语法。"""
    code = code.strip()
    if not code:
        return ""

    declarations = {
        "class": "classDiagram",
        "activity": "stateDiagram-v2",
        "state": "stateDiagram-v2",
    }
    expected = declarations.get(diagram_type, "")

    if expected and not code.startswith(expected):
        lines = code.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("class ") or stripped.startswith("state") or stripped.startswith("[*]"):
                insert_idx = i
                break
        lines.insert(insert_idx, expected)
        code = "\n".join(lines)

    return code


class ClassDiagramGenerator:
    """类图生成器。"""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def generate(self, analysis: AnalysisResult) -> MermaidDiagram:
        entities_desc = self._format_entities(analysis)
        relationships_desc = self._format_relationships(analysis)

        prompt = CLASS_DIAGRAM_PROMPT.format(
            entities=entities_desc,
            relationships=relationships_desc if relationships_desc else "无",
        )
        response = self.llm.chat(prompt=prompt, system=CLASS_DIAGRAM_SYSTEM)
        code = _extract_mermaid_block(response)
        code = _validate_and_repair_mermaid(code, "class")
        return MermaidDiagram(diagram_type="classDiagram", source_code=code, title="系统类图")

    @staticmethod
    def _format_entities(analysis: AnalysisResult) -> str:
        lines = []
        for e in analysis.entities:
            lines.append(f"\n### {e.name}")
            if e.attributes:
                lines.append("属性:")
                for a in e.attributes:
                    vis = {"public": "+", "private": "-", "protected": "#"}.get(a.visibility, "+")
                    lines.append(f"  {vis} {a.name}: {a.type}")
            if e.methods:
                lines.append("方法:")
                for m in e.methods:
                    vis = {"public": "+", "private": "-", "protected": "#"}.get(m.visibility, "+")
                    params = ", ".join(m.parameters)
                    lines.append(f"  {vis} {m.name}({params}): {m.return_type}")
        return "\n".join(lines)

    @staticmethod
    def _format_relationships(analysis: AnalysisResult) -> str:
        lines = []
        for e in analysis.entities:
            for r in e.relationships:
                lines.append(f"- {e.name} --({r.type})--> {r.target}: {r.label} [{r.multiplicity}]")
        return "\n".join(lines)


class ActivityDiagramGenerator:
    """活动图生成器。"""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def generate(self, analysis: AnalysisResult) -> list[MermaidDiagram]:
        diagrams = []
        total = len(analysis.behaviors)
        for i, behavior in enumerate(analysis.behaviors):
            print(f"  [{i+1}/{total}] {behavior.name}...", end=" ", flush=True)
            diagram = self.generate_for_behavior(behavior)
            if diagram:
                diagrams.append(diagram)
                print("完成")
            else:
                print("跳过")
        return diagrams

    def generate_for_behavior(self, behavior: Behavior) -> MermaidDiagram | None:
        steps_desc = "\n".join(
            f"{s.order}. [{s.actor}] {s.action}" +
            (f" (分支: {', '.join(s.branches)})" if s.branches else "")
            for s in behavior.steps
        )
        prompt = ACTIVITY_DIAGRAM_PROMPT.format(
            name=behavior.name,
            description=behavior.description,
            preconditions=", ".join(behavior.preconditions) if behavior.preconditions else "无",
            postconditions=", ".join(behavior.postconditions) if behavior.postconditions else "无",
            steps=steps_desc,
        )
        response = self.llm.chat(prompt=prompt, system=ACTIVITY_DIAGRAM_SYSTEM)
        code = _extract_mermaid_block(response)
        code = _validate_and_repair_mermaid(code, "activity")
        if not code:
            return None
        return MermaidDiagram(
            diagram_type="stateDiagram-v2",
            source_code=code,
            title=f"活动图 - {behavior.name}",
        )


class StateMachineGenerator:
    """状态机图生成器。"""

    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def generate(self, analysis: AnalysisResult) -> list[MermaidDiagram]:
        diagrams = []
        candidates = self._identify_stateful_entities(analysis)
        total = len(candidates)
        for i, entity in enumerate(candidates):
            print(f"  [{i+1}/{total}] {entity.name}...", end=" ", flush=True)
            diagram = self.generate_for_entity(entity, analysis)
            if diagram:
                diagrams.append(diagram)
                print("完成")
            else:
                print("跳过")
        if not diagrams and analysis.entities:
            for i, entity in enumerate(analysis.entities[:3]):
                print(f"  [fallback] {entity.name}...", end=" ", flush=True)
                diagram = self.generate_for_entity(entity, analysis)
                if diagram:
                    diagrams.append(diagram)
                    print("完成")
                else:
                    print("跳过")
        return diagrams

    def generate_for_entity(self, entity, analysis: AnalysisResult) -> MermaidDiagram | None:
        attrs = "\n".join(f"- {a.name}: {a.type}" for a in entity.attributes)
        methods = "\n".join(f"- {m.name}({', '.join(m.parameters)}): {m.return_type}" for m in entity.methods)
        constraints = "\n".join(
            f"- [{c.type}] {c.description}"
            for c in analysis.constraints
            if entity.name.lower() in c.scope.lower() or entity.name.lower() in c.description.lower()
        )
        if not constraints:
            constraints = "无特定约束"

        prompt = STATE_DIAGRAM_PROMPT.format(
            name=entity.name,
            attributes=attrs or "无",
            methods=methods or "无",
            constraints=constraints,
        )
        response = self.llm.chat(prompt=prompt, system=STATE_DIAGRAM_SYSTEM)
        code = _extract_mermaid_block(response)
        code = _validate_and_repair_mermaid(code, "state")
        if not code:
            return None
        return MermaidDiagram(
            diagram_type="stateDiagram-v2",
            source_code=code,
            title=f"状态机图 - {entity.name}",
        )

    @staticmethod
    def _identify_stateful_entities(analysis: AnalysisResult) -> list:
        state_keywords = ["状态", "status", "state", "阶段", "phase", "生命周期", "lifecycle", "订单", "order",
                          "任务", "task", "流程", "process", "申请", "审批", "工单", "用户", "user"]
        candidates = []
        for e in analysis.entities:
            combined = e.name + " ".join(a.name for a in e.attributes)
            if any(kw in combined.lower() for kw in state_keywords):
                candidates.append(e)
        return candidates if candidates else analysis.entities[:2]
