"""审核编辑器：展示AI提取结果，支持人工审核和修改。"""
import sys
from src.models import AnalysisResult, Entity, Behavior, Constraint, Attribute, Method, Relationship, Step


def review(analysis: AnalysisResult, skip: bool = False) -> AnalysisResult:
    """展示分析结果，让用户选择确认/编辑/跳过。"""
    print(f"\n{'='*50}")
    print(analysis.preview_text())
    print(f"{'='*50}")

    if skip:
        print("  跳过审核，直接生成图表...")
        return analysis

    while True:
        print("\n[Enter]确认  [e]编辑  [r]重新加载文件  [q]退出")
        try:
            cmd = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n已取消")
            sys.exit(0)

        if cmd == "":
            print("已确认，生成图表...")
            analysis.to_file("design/raw-analysis.json")
            return analysis
        elif cmd == "e":
            analysis = _edit_loop(analysis)
            analysis.to_file("design/raw-analysis.json")
        elif cmd == "r":
            path = input("JSON文件路径 [design/raw-analysis.json]: ").strip()
            path = path or "design/raw-analysis.json"
            try:
                analysis = AnalysisResult.from_file(path)
                print(analysis.preview_text())
            except Exception as e:
                print(f"加载失败: {e}")
        elif cmd == "q":
            print("已退出。分析结果已保存到 design/raw-analysis.json")
            print("后续可用: python agent.py --task design --input xxx.md --edit-file design/raw-analysis.json --skip-review")
            sys.exit(0)
        else:
            print("无效命令")


def _edit_loop(analysis: AnalysisResult) -> AnalysisResult:
    while True:
        print("\n编辑: [le]列实体 [lb]列行为 [ae]加实体 [de]删实体 [ee]改实体")
        print("      [ab]加行为 [db]删行为 [eb]改行为 [done]完成")
        try:
            cmd = input("edit> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return analysis

        if cmd == "done":
            print(analysis.preview_text())
            return analysis
        elif cmd == "le":
            for i, e in enumerate(analysis.entities):
                print(f"  {i+1}. {e.name}")
        elif cmd == "lb":
            for i, b in enumerate(analysis.behaviors):
                print(f"  {i+1}. {b.name} - {b.description}")
        elif cmd == "ae":
            analysis.entities.append(_input_entity())
        elif cmd == "de":
            analysis = _delete_entity(analysis)
        elif cmd == "ee":
            analysis = _edit_entity(analysis)
        elif cmd == "ab":
            analysis.behaviors.append(_input_behavior())
        elif cmd == "db":
            analysis = _delete_behavior(analysis)
        elif cmd == "eb":
            analysis = _edit_behavior(analysis)
        else:
            print("未知命令")


def _input_entity() -> Entity:
    name = input("  实体名: ").strip()
    attrs = []
    print("  属性 (格式: 属性名:类型, 空行结束)")
    while True:
        s = input("    ").strip()
        if not s:
            break
        parts = s.split(":", 1)
        attrs.append(Attribute(name=parts[0].strip(), type=parts[1].strip() if len(parts) > 1 else "str"))
    methods = []
    print("  方法 (格式: 方法名, 空行结束)")
    while True:
        s = input("    ").strip()
        if not s:
            break
        methods.append(Method(name=s))
    return Entity(name=name, attributes=attrs, methods=methods)


def _delete_entity(analysis: AnalysisResult) -> AnalysisResult:
    try:
        idx = int(input("  删除第几个实体? ")) - 1
        if 0 <= idx < len(analysis.entities):
            print(f"  已删除: {analysis.entities[idx].name}")
            analysis.entities.pop(idx)
    except ValueError:
        pass
    return analysis


def _edit_entity(analysis: AnalysisResult) -> AnalysisResult:
    try:
        idx = int(input("  编辑第几个实体? ")) - 1
        if 0 <= idx < len(analysis.entities):
            e = analysis.entities[idx]
            print(f"  当前: {e.name}, {len(e.attributes)}属性, {len(e.methods)}方法")
            print("  [n]改名 [a]加属性 [m]加方法 [d]删除 [done]返回")
            sub = input("  > ").strip().lower()
            if sub == "n":
                e.name = input("  新名称: ").strip() or e.name
            elif sub == "a":
                s = input("  属性名:类型: ").strip()
                parts = s.split(":", 1)
                e.attributes.append(Attribute(name=parts[0], type=parts[1] if len(parts) > 1 else "str"))
            elif sub == "m":
                e.methods.append(Method(name=input("  方法名: ").strip()))
            elif sub == "d":
                analysis.entities.pop(idx)
    except ValueError:
        pass
    return analysis


def _input_behavior() -> Behavior:
    name = input("  流程名: ").strip()
    desc = input("  描述: ").strip()
    steps = []
    print("  步骤 (格式: 步骤描述, 空行结束)")
    i = 1
    while True:
        s = input(f"    {i}. ").strip()
        if not s:
            break
        steps.append(Step(order=i, action=s))
        i += 1
    return Behavior(name=name, description=desc, steps=steps)


def _delete_behavior(analysis: AnalysisResult) -> AnalysisResult:
    try:
        idx = int(input("  删除第几个行为? ")) - 1
        if 0 <= idx < len(analysis.behaviors):
            print(f"  已删除: {analysis.behaviors[idx].name}")
            analysis.behaviors.pop(idx)
    except ValueError:
        pass
    return analysis


def _edit_behavior(analysis: AnalysisResult) -> AnalysisResult:
    try:
        idx = int(input("  编辑第几个行为? ")) - 1
        if 0 <= idx < len(analysis.behaviors):
            b = analysis.behaviors[idx]
            print(f"  当前: {b.name}, {len(b.steps)}步")
            print("  [n]改名 [s]加步骤 [d]删除 [done]返回")
            sub = input("  > ").strip().lower()
            if sub == "n":
                b.name = input("  新名称: ").strip() or b.name
            elif sub == "s":
                b.steps.append(Step(order=len(b.steps)+1, action=input("  步骤: ").strip()))
            elif sub == "d":
                analysis.behaviors.pop(idx)
    except ValueError:
        pass
    return analysis
