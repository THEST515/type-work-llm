import concurrent.futures
from pathlib import Path
from src.config import Config
from src.llm_adapter import LLMAdapter
from src.analyzer import RequirementAnalyzer
from src.diagram_generators import ClassDiagramGenerator, ActivityDiagramGenerator, StateMachineGenerator
from src.formatter import OutputFormatter
from src.models import DesignOutput, MermaidDiagram, Behavior


class Orchestrator:

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMAdapter(config)
        self.analyzer = RequirementAnalyzer(self.llm)
        self.class_gen = ClassDiagramGenerator(self.llm)
        self.activity_gen = ActivityDiagramGenerator(self.llm)
        self.state_gen = StateMachineGenerator(self.llm)
        self.formatter = OutputFormatter(config)

    def run(self, input_doc: str) -> DesignOutput:
        print(f"[1/3] 加载需求文档: {input_doc}")
        document = self._load_document(input_doc)

        print(f"[2/3] 执行需求分析... (文档长度: {len(document)} 字符)")
        analysis = self.analyzer.analyze(document)
        print(f"  => 提取到 {len(analysis.entities)} 个实体, "
              f"{len(analysis.behaviors)} 个行为, "
              f"{len(analysis.constraints)} 个约束")

        output = DesignOutput(
            analysis=analysis,
            input_doc_name=Path(input_doc).name,
        )

        print(f"[3/3] 生成设计图 (并发)...")
        self._generate_all_concurrently(output, analysis)

        self.formatter.write_output(output)
        return output

    def _generate_all_concurrently(self, output: DesignOutput, analysis):
        diagrams = self.config.diagrams

        # 准备所有任务
        state_candidates = self.state_gen._identify_stateful_entities(analysis)
        if not state_candidates and analysis.entities:
            state_candidates = analysis.entities[:3]

        behavior_count = len(analysis.behaviors)
        state_count = len(state_candidates)
        total_tasks = (1 if "class" in diagrams else 0) + \
                      (behavior_count if "activity" in diagrams else 0) + \
                      (state_count if "state" in diagrams else 0)

        max_workers = min(10, max(1, total_tasks))
        activity_results = {}
        state_results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_to_key = {}

            if "class" in diagrams:
                f = pool.submit(self._gen_class, analysis)
                future_to_key[f] = "_class"

            if "activity" in diagrams:
                for i, behavior in enumerate(analysis.behaviors):
                    f = pool.submit(self._gen_one_activity, i, behavior, behavior_count)
                    future_to_key[f] = f"activity_{i}"

            if "state" in diagrams:
                for i, entity in enumerate(state_candidates):
                    f = pool.submit(self._gen_one_state, i, entity, state_count, analysis)
                    future_to_key[f] = f"state_{i}"

            for future in concurrent.futures.as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    result = future.result()
                except Exception as e:
                    print(f"  [{key}] 失败: {e}")
                    continue

                if key == "_class":
                    output.class_diagram = result
                elif key.startswith("activity_"):
                    idx = int(key.split("_")[1])
                    activity_results[idx] = result
                elif key.startswith("state_"):
                    idx = int(key.split("_")[1])
                    state_results[idx] = result

        output.activity_diagrams = [d for _, d in sorted(activity_results.items()) if d is not None]
        output.state_diagrams = [d for _, d in sorted(state_results.items()) if d is not None]

        print(f"  => 类图: 1 张, 活动图: {len(output.activity_diagrams)} 张, "
              f"状态机图: {len(output.state_diagrams)} 张")

    def _gen_class(self, analysis):
        return self._generate_with_repair(self.class_gen.generate, analysis, "类图")

    def _gen_one_activity(self, i: int, behavior: Behavior, total: int):
        print(f"  活动图 [{i+1}/{total}] {behavior.name}...", end=" ", flush=True)
        result = self.activity_gen.generate_for_behavior(behavior)
        if result:
            if not result.validate():
                result.source_code = self._repair_via_llm(result, "activity")
            print("完成")
        else:
            print("跳过")
        return result

    def _gen_one_state(self, i: int, entity, total: int, analysis):
        print(f"  状态机图 [{i+1}/{total}] {entity.name}...", end=" ", flush=True)
        result = self.state_gen.generate_for_entity(entity, analysis)
        if result:
            if not result.validate():
                result.source_code = self._repair_via_llm(result, "state")
            print("完成")
        else:
            print("跳过")
        return result

    def _load_document(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"输入文件不存在: {path}")
        return p.read_text(encoding="utf-8")

    def _generate_with_repair(self, generator_func, analysis, name: str):
        try:
            diagram = generator_func(analysis)
            if not diagram.validate():
                diagram.source_code = self._repair_via_llm(diagram, "class")
            return diagram
        except Exception as e:
            print(f"  [警告] {name}生成失败: {e}")
            return MermaidDiagram(diagram_type="classDiagram", source_code="", title=f"{name} (生成失败)")

    def _repair_via_llm(self, diagram: MermaidDiagram, diagram_type: str) -> str:
        import re
        repair_prompt = (
            f"以下 Mermaid 图表语法可能有误，请修复并只输出正确的 Mermaid 代码块：\n\n"
            f"```mermaid\n{diagram.source_code}\n```\n\n"
            f"图表类型应为: {diagram_type}\n只输出修复后的 ```mermaid 代码块。"
        )
        try:
            response = self.llm.chat(prompt=repair_prompt)
            match = re.search(r'```mermaid\s*([\s\S]*?)```', response)
            if match:
                return match.group(1).strip()
            match = re.search(r'```\s*([\s\S]*?)```', response)
            if match:
                return match.group(1).strip()
        except Exception:
            pass
        return diagram.source_code
