from pathlib import Path
from src.config import Config
from src.models import DesignOutput


class OutputFormatter:
    """输出格式化器：汇总所有图表和分析结果，写入输出目录。"""

    def __init__(self, config: Config):
        self.config = config

    def write_output(self, output: DesignOutput) -> None:
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        self._write_analysis_summary(output, out_dir)
        self._write_class_diagram(output, out_dir)
        self._write_activity_diagrams(output, out_dir)
        self._write_state_diagrams(output, out_dir)
        self._write_index(output, out_dir)

        print(f"\n设计产物已输出到: {out_dir.absolute()}/")

    def _write_analysis_summary(self, output: DesignOutput, out_dir: Path) -> None:
        lines = [
            "# 需求分析摘要",
            "",
            f"**输入文档**: {output.input_doc_name}",
            f"**生成时间**: {output.generated_at}",
            "",
            "## 概述",
            "",
            output.analysis.summary,
            "",
            "## 实体列表",
            "",
        ]
        for e in output.analysis.entities:
            lines.append(f"### {e.name}")
            if e.attributes:
                lines.append("\n| 属性 | 类型 | 可见性 |")
                lines.append("|------|------|--------|")
                for a in e.attributes:
                    lines.append(f"| {a.name} | {a.type} | {a.visibility} |")
            if e.methods:
                lines.append("\n| 方法 | 参数 | 返回值 | 可见性 |")
                lines.append("|------|------|--------|--------|")
                for m in e.methods:
                    params = ", ".join(m.parameters)
                    lines.append(f"| {m.name} | {params} | {m.return_type} | {m.visibility} |")
            if e.relationships:
                lines.append("\n**关系**:")
                for r in e.relationships:
                    lines.append(f"- {r.type} → {r.target} ({r.label})")
            lines.append("")

        lines.extend([
            "## 行为列表",
            "",
        ])
        for b in output.analysis.behaviors:
            lines.append(f"### {b.name}")
            lines.append(f"{b.description}\n")
            if b.preconditions:
                lines.append(f"**前置条件**: {', '.join(b.preconditions)}\n")
            if b.postconditions:
                lines.append(f"**后置条件**: {', '.join(b.postconditions)}\n")
            if b.steps:
                lines.append("| 步骤 | 执行者 | 动作 | 分支 |")
                lines.append("|------|--------|------|------|")
                for s in b.steps:
                    branches = ", ".join(s.branches) if s.branches else "-"
                    lines.append(f"| {s.order} | {s.actor} | {s.action} | {branches} |")
            lines.append("")

        lines.extend([
            "## 约束列表",
            "",
        ])
        for c in output.analysis.constraints:
            lines.append(f"- **[{c.type}]** {c.description} `({c.scope})`")

        (out_dir / "analysis.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_class_diagram(self, output: DesignOutput, out_dir: Path) -> None:
        if output.class_diagram and output.class_diagram.source_code.strip():
            (out_dir / "class_diagram.mermaid").write_text(
                output.class_diagram.source_code, encoding="utf-8"
            )

    def _write_activity_diagrams(self, output: DesignOutput, out_dir: Path) -> None:
        for i, d in enumerate(output.activity_diagrams):
            if d.source_code.strip():
                safe_name = d.title.replace(" ", "_").replace("-", "_").replace("/", "_")
                (out_dir / f"activity_{i+1}_{safe_name}.mermaid").write_text(
                    d.source_code, encoding="utf-8"
                )

    def _write_state_diagrams(self, output: DesignOutput, out_dir: Path) -> None:
        for i, d in enumerate(output.state_diagrams):
            if d.source_code.strip():
                safe_name = d.title.replace(" ", "_").replace("-", "_").replace("/", "_")
                (out_dir / f"state_{i+1}_{safe_name}.mermaid").write_text(
                    d.source_code, encoding="utf-8"
                )

    def _write_index(self, output: DesignOutput, out_dir: Path) -> None:
        lines = [
            "# 设计产物索引",
            "",
            f"输入文档: {output.input_doc_name}",
            f"生成时间: {output.generated_at}",
            "",
            "## 文件列表",
            "",
            "| 文件 | 说明 |",
            "|------|------|",
            "| [analysis.md](analysis.md) | 需求分析摘要（实体、行为、约束） |",
        ]
        if output.class_diagram and output.class_diagram.source_code.strip():
            lines.append("| [class_diagram.mermaid](class_diagram.mermaid) | 类图 |")
        for i, d in enumerate(output.activity_diagrams):
            if d.source_code.strip():
                safe_name = d.title.replace(" ", "_").replace("-", "_")
                lines.append(f"| [activity_{i+1}_{safe_name}.mermaid](activity_{i+1}_{safe_name}.mermaid) | {d.title} |")
        for i, d in enumerate(output.state_diagrams):
            if d.source_code.strip():
                safe_name = d.title.replace(" ", "_").replace("-", "_")
                lines.append(f"| [state_{i+1}_{safe_name}.mermaid](state_{i+1}_{safe_name}.mermaid) | {d.title} |")

        (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")
