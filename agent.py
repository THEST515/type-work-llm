#!/usr/bin/env python3
"""基于大语言模型的软件工程智能体 —— 分析+设计 (组合a)

用法:
    python agent.py --task design --input requirements.md --output design/
    python agent.py --task design --input requirements.md --config config.yaml
"""

import argparse
import sys
from pathlib import Path

from src.config import Config
from src.orchestrator import Orchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent",
        description="软件工程智能体 —— 根据PRD自动生成系统分析与设计模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python agent.py --task design --input requirements.md --output design/
  python agent.py --task design --input requirements.md --output design/ --verbose
  python agent.py --task design --input requirements.md --config config.yaml
        """,
    )
    parser.add_argument(
        "--task", required=True,
        choices=["design"],
        help="任务类型: design = 需求分析 + 设计模型生成",
    )
    parser.add_argument(
        "--input", required=True, type=str,
        help="输入的需求文档/PRD 路径 (支持 .md, .txt)",
    )
    parser.add_argument(
        "--output", default="design", type=str,
        help="输出目录 (默认: design/)",
    )
    parser.add_argument(
        "--diagrams", default="class,activity,state", type=str,
        help="要生成的图表类型，逗号分隔 (默认: class,activity,state)",
    )
    parser.add_argument(
        "--format", default="mermaid", type=str,
        choices=["mermaid", "plantuml"],
        help="输出格式 (默认: mermaid)",
    )
    parser.add_argument(
        "--model", default=None, type=str,
        help="使用的模型名称",
    )
    parser.add_argument(
        "--provider", default=None, type=str,
        choices=["deepseek", "anthropic", "openai"],
        help="模型提供商 (默认: deepseek)",
    )
    parser.add_argument(
        "--api-key", default=None, type=str,
        help="API Key（也可设环境变量 DEEPSEEK_API_KEY）",
    )
    parser.add_argument(
        "--api-base", default=None, type=str,
        help="API 地址（默认: https://api.deepseek.com）",
    )
    parser.add_argument(
        "--config", default=None, type=str,
        help="YAML 配置文件路径",
    )
    parser.add_argument(
        "--temperature", default=None, type=float,
        help="模型温度参数 (0.0-1.0)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="输出详细执行日志",
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="半交互模式：生成后可对图表提出修改意见",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.config:
        config = Config.from_yaml(args.config)
    else:
        config = Config.from_env()

    if args.provider:
        config.model_provider = args.provider
    if args.model:
        config.model_name = args.model
    if args.api_key:
        config.api_key = args.api_key
    if args.api_base:
        config.api_base = args.api_base
    if args.temperature is not None:
        config.temperature = args.temperature
    config.output_dir = args.output
    config.output_format = args.format
    config.diagrams = [d.strip() for d in args.diagrams.split(",")]
    config.verbose = args.verbose
    config.interactive = args.interactive

    if config.verbose:
        print(f"模型提供商: {config.model_provider}")
        print(f"模型名称: {config.model_name}")
        print(f"输出目录: {config.output_dir}")
        print(f"图表类型: {', '.join(config.diagrams)}")
        print()

    orchestrator = Orchestrator(config)
    output = orchestrator.run(args.input)

    if config.interactive:
        interactive_loop(orchestrator, output)


def interactive_loop(orchestrator: Orchestrator, output):
    print("\n=== 交互模式 ===")
    print("输入 'help' 查看命令, 'quit' 退出\n")

    while True:
        try:
            cmd = input("agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd in ("quit", "exit"):
            break
        elif cmd == "help":
            print("  class     - 重新生成类图")
            print("  activity  - 重新生成活动图")
            print("  state     - 重新生成状态机图")
            print("  all       - 重新生成全部图表")
            print("  summary   - 显示分析摘要")
            print("  quit      - 退出")
        elif cmd == "class":
            print("  重新生成类图...")
            output.class_diagram = orchestrator.class_gen.generate(output.analysis)
            orchestrator.formatter.write_output(output)
            print("  完成。")
        elif cmd == "activity":
            print("  重新生成活动图...")
            output.activity_diagrams = orchestrator.activity_gen.generate(output.analysis)
            orchestrator.formatter.write_output(output)
            print("  完成。")
        elif cmd == "state":
            print("  重新生成状态机图...")
            output.state_diagrams = orchestrator.state_gen.generate(output.analysis)
            orchestrator.formatter.write_output(output)
            print("  完成。")
        elif cmd == "all":
            print("  重新生成全部图表...")
            output.class_diagram = orchestrator.class_gen.generate(output.analysis)
            output.activity_diagrams = orchestrator.activity_gen.generate(output.analysis)
            output.state_diagrams = orchestrator.state_gen.generate(output.analysis)
            orchestrator.formatter.write_output(output)
            print("  完成。")
        elif cmd == "summary":
            print(f"\n{output.analysis.summary}\n")
        else:
            print(f"  未知命令: {cmd}")


if __name__ == "__main__":
    main()
