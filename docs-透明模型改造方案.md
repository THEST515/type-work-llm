# 透明模型改造方案

## 目标

让用户在图表生成前看到 AI 提取的实体、行为、约束，可以**审核、修改、增删**，确认后再生成图表。流程从黑盒变为可干预的透明流水线。

---

## 改造后的完整流程

```
输入 PRD
  │
  ▼
[1] AI 提取 ──────────────────────────────────────────
  │   LLM 分析需求文档，输出 JSON（实体/行为/约束）
  │   同时保存到文件: design/raw-analysis.json
  ▼
[2] 人工审核 ──────────────────────────────────────────
  │   终端展示提取结果摘要（实体列表、行为列表、约束列表）
  │   用户可以选择：
  │     a) 直接确认，跳到[4]
  │     b) 进入编辑模式，修改后跳到[4]
  │     c) 保存到文件，用外部编辑器修改后继续
  ▼
[3] 人工编辑（可选）───────────────────────────────────
  │   用户可以对实体增删改、对行为增删改步骤
  │   编辑方式：
  │     a) 终端交互式编辑（增删改查）
  │     b) 打开 design/raw-analysis.json 用 VSCode 编辑
  │     c) 打开 design/analysis-preview.md 用表格编辑
  ▼
[4] 图生成 ──────────────────────────────────────────
     根据（可能被修改后的）分析结果，并发生成类图+活动图+状态机图
```

---

## 详细设计

### 第 1 步：AI 提取 → 保存原始数据

**改动**：`analyzer.py` 分析完成后，把原始 JSON 写入 `design/raw-analysis.json`。

```python
# analyzer.py 中 analyze() 返回前
import json
from pathlib import Path

raw_path = Path("design") / "raw-analysis.json"
raw_path.parent.mkdir(exist_ok=True)
raw_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
```

同时生成一份人类可读的预览 `design/analysis-preview.md`（表格形式）：

```markdown
# 需求分析预览

## 实体 (7个)
| 序号 | 实体名 | 属性数 | 方法数 | 关系数 |
|------|--------|--------|--------|--------|
| 1 | User | 4 | 3 | 2 |
| 2 | Book | 5 | 3 | 1 |
...

## 行为 (5个)
| 序号 | 行为名 | 步骤数 | 描述 |
|------|--------|--------|------|
| 1 | 用户注册 | 4 | ... |
...

## 约束 (3个)
| 序号 | 描述 | 类型 |
|------|------|------|
| 1 | ... | business-rule |
```

### 第 2 步：人工审核（终端交互）

**新增 CLI 模式**：`--review`（默认开启）

```bash
python agent.py --task design --input example-prd.md --review
```

分析完成后暂停，显示摘要：

```
  => 提取到 7 个实体, 5 个行为, 3 个约束

--- 审核 ---
实体: User, Book, BorrowRecord, Reservation, Notification, BookCopy, AuditLog
行为: 用户注册与登录, 图书借阅, 图书归还, 续借, 预约图书
约束: 3 条

请选择:
  [Enter] 确认，直接生成图表
  [e]     进入编辑模式
  [f]     保存到文件，稍后编辑
  [q]     退出
>
```

### 第 3 步：人工编辑（三种方式）

#### 方式 A：终端交互式编辑

```
--- 编辑模式 ---
命令: list-e(实体) list-b(行为) add-e(加实体) del-e(删实体) 
       edit-e(改实体) add-b(加行为) done(完成)

> list-e
1. User (4属性, 3方法) → Book, BorrowRecord
2. Book (5属性, 3方法) → BorrowRecord
...

> edit-e 1
当前: User
  属性: 用户名, 密码, 邮箱, 角色
  方法: 注册, 登录, 修改信息
  关系: → Book(借阅), → BorrowRecord(拥有)

修改什么? [name/attr/method/rel/done]: attr
  1. [+] 添加
  2. [d] 删除
  3. 用户名: str  [修改]
  > 3
  新属性名: 手机号
  新类型: str
  已更新: 手机号: str

修改什么? [name/attr/method/rel/done]: done
```

#### 方式 B：JSON 文件编辑

生成 `design/raw-analysis.json`，用户在 VSCode 中直接编辑 JSON，保存后程序读取继续。

```bash
python agent.py --task design --input example-prd.md --edit-file design/raw-analysis.json
```

#### 方式 C：Markdown 表格编辑

生成 `design/analysis-preview.md`，用户在 VSCode 中编辑表格，程序解析 Markdown 表格中的修改。

### 第 4 步：图表生成

读取分析结果（可能是被修改后的），并发生成图表。和现在一样。

---

## 需要改动的文件

| 文件 | 改动 |
|------|------|
| `agent.py` | 新增 `--review`、`--skip-review`、`--edit-file` CLI 参数 |
| `analyzer.py` | 返回前写入 `raw-analysis.json` 和 `analysis-preview.md` |
| 新增 `src/reviewer.py` | 审核编辑器：终端交互 + 文件读写 + 实体行为 CRUD |
| `orchestrator.py` | 在分析后、图生成前插入审核步骤 |
| `src/models.py` | 给 AnalysisResult 加 `to_dict()` 和 `from_file()` 方法 |
| `README.md` | 增加审核模式的使用说明 |

---

## 新增 CLI 参数

| 参数 | 说明 |
|------|------|
| `--review` | 默认，分析后暂停让用户审核 |
| `--skip-review` | 跳过审核，直接出图（原来行为） |
| `--edit-file <path>` | 从已有的 JSON 文件加载分析结果，跳过 AI 提取 |

---

## 使用示例

```bash
# 正常流程（含审核）
python agent.py --task design --input example-prd.md

# 跳过审核直接出图（恢复原来行为）
python agent.py --task design --input example-prd.md --skip-review

# 从已有分析文件生成图（不需重新调 LLM）
python agent.py --task design --input example-prd.md --edit-file design/raw-analysis.json

# 先只提取不做图（只看 AI 提取了什么）
python agent.py --task design --input example-prd.md --diagrams none
```

---

## 效果对比

| | 现在（黑盒） | 改造后（透明） |
|------|-------------|---------------|
| AI 提取后 | 直接出图 | 暂停，展示结果 |
| 用户能否修改 | 不能 | 增删改查实体/行为 |
| 修改方式 | 只能重跑 | 终端编辑 / JSON / Markdown |
| 出错怎么办 | 重跑全部 | 只改错的那一个 |
| 调试效率 | 低（每次重跑 3-5 分钟） | 高（修改后秒出图） |
