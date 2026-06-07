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

规则：
1. 每个实体至少2属性2方法，每个行为至少3步
2. 提取所有业务流程：用户触发的（点餐/借书/注册）和系统自动触发的（定时提醒/自动备份/库存预警/状态流转/通知推送），两类同等重要
3. 需求文档每个功能子章节下的每个独立功能点（包括列表项），都检查是否要提取为实体或行为
4. 如果文档提到多种业务模式/场景/渠道（如堂食+外卖+预约），每种都应考虑是否有独立行为
5. 数据统计、分析报表、趋势预测、偏好分析等功能也是独立的业务流程
6. 只输出JSON，不要包含任何其他文字"""


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

        entities, behaviors, constraints = self._build_result(data)
        result = AnalysisResult(
            summary=data.get("summary", ""),
            entities=entities,
            behaviors=behaviors,
            constraints=constraints,
        )
        result.to_file("design/raw-analysis.json")

        # 通用遗漏检测：自动从 PRD 中提取功能点，比对 AI 覆盖情况
        uncovered = self._check_coverage(document, entities, behaviors)
        if uncovered:
            print("  ⚠ 以下功能点可能被 AI 遗漏，审核时请注意:")
            for line in uncovered:
                print(line)

        return result

    def _build_result(self, data: dict) -> tuple:
        entities, behaviors, constraints = [], [], []
        for e in data.get("entities", []):
            if isinstance(e, dict):
                try:
                    ent = Entity.from_dict(e)
                    if ent.name: entities.append(ent)
                except Exception: pass
        for b in data.get("behaviors", []):
            if isinstance(b, dict):
                try:
                    beh = Behavior.from_dict(b)
                    if beh.name: behaviors.append(beh)
                except Exception: pass
        for c in data.get("constraints", []):
            if isinstance(c, dict):
                try:
                    con = Constraint.from_dict(c)
                    if con.description: constraints.append(con)
                except Exception: pass
        return entities, behaviors, constraints

    # ─── 通用遗漏检测 ──────────────────────────────────

    @staticmethod
    def _extract_prd_items(document: str) -> list[str]:
        """从 PRD 中提取独立功能项（- 开头 或 功能子章节内的独立句子），用于后续比
        对。不做领域假设——纯靠 PRD 的结构特征。"""
        items = []
        # 功能子章节内的列表项（- xxx / * xxx / 数字. xxx）
        for m in re.finditer(
            r'[-*]\s*(.+?)(?=\n[-*\d]|\n\n|\n#{1,3}\s|\Z)',
            document, re.DOTALL
        ):
            text = m.group(1).strip()
            if len(text) > 3:
                items.append(text)
        return items

    @staticmethod
    def _extract_key_verb(text: str) -> list[str]:
        """从文本中提取核心动词短语。匹配'双字动词+0~15字宾语'模式——
        这是中文功能描述的通用结构，不依赖领域词典。"""
        # 覆盖常见业务动词（双字为主 + 少数高频单字动词的特殊情况）
        # 单字动词匹配要求后面紧跟的字符 >= 3 个，避免过度匹配
        verbs_2char = (
            r'发送|推送|记录|生成|统计|分析|提醒|检测|触发|检查|更新|创建|删除|导出|导入|'
            r'预约|取消|续借|注册|登录|支付|退款|计算|搜索|查询|显示|打印|备份|恢复|'
            r'分配|处理|通知|标记|确认|审核|管理|修改|添加|设置|配置|启动|停止|监控|'
            r'预测|排行|推荐|评分|评价|反馈|投诉|预警|消耗|扣除|累积|兑换|开具|'
            r'叫号|排班|挂号|就诊|取药|上架|下架|结账|翻台|点餐|下单|出票|'
            r'浏览|提交|扫描|识别|放行|充值|开票|签到|分账'
        )
        pattern = rf'({verbs_2char})[^，。；\n]{{1,15}}'
        result = []
        for m in re.finditer(pattern, text):
            v = m.group(0).strip()
            if len(v) >= 3:  # 至少3字符，过滤噪声
                result.append(v)
        return result

    @staticmethod
    def _check_coverage(document: str,
                        entities: list[Entity],
                        behaviors: list[Behavior]) -> list[str]:
        """对比 PRD 中的功能项与 AI 提取结果，返回未覆盖提示。"""
        # Step 1：构建 AI 覆盖文本池
        covered_pool = []
        for e in entities:
            covered_pool.append(e.name)
            for a in e.attributes: covered_pool.append(a.name)
            for m in e.methods: covered_pool.append(m.name)
            for r in e.relationships: covered_pool.append(r.label)
        for b in behaviors:
            covered_pool.append(b.name)
            covered_pool.append(b.description)
            for s in b.steps: covered_pool.append(s.action)
        covered_text = " ".join(covered_pool)

        # Step 2：提取 PRD 中的功能项
        prd_items = RequirementAnalyzer._extract_prd_items(document)

        # Step 3：对每个功能项，提取核心动词，检查是否被 AI 覆盖
        uncovered = []
        seen = set()
        for item in prd_items:
            verbs = RequirementAnalyzer._extract_key_verb(item)
            for v in verbs:
                if v in seen: continue
                seen.add(v)
                if v not in covered_text and len(v) >= 3:
                    # 在 item 中截取包含该动词的短句作为上下文
                    idx = item.find(v)
                    ctx = item[max(0, idx-5):idx+len(v)+15].strip()
                    uncovered.append(f"     ⚠ 未覆盖: 「{ctx}」")

        # 去重 + 最多显示10条
        return uncovered[:10]

    # ─── JSON 解析 ────────────────────────────────────

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
