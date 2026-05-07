# 软件工程智能体 —— 分析+设计（组合a）

## 项目简介

本项目实现了一个基于大语言模型的软件工程智能体，覆盖**组合a：分析+设计**阶段。智能体以自然语言需求文档（PRD、用户故事）为输入，自动执行需求分析并生成 UML 设计模型，包括**类图、活动图、状态机图**三种，输出为 Mermaid 格式，可直接在 VSCode / GitHub / GitLab 中渲染。

**选题依据**：课程设计选题1（基于大语言模型的软件工程智能体），功能组合a。

**覆盖阶段**：需求分析 → 系统设计

| 输入 | 输出 |
|------|------|
| PRD / 需求规格说明书 (.md, .txt) | 分析摘要 + 类图 + 活动图 + 状态机图 (Mermaid) |

---

## 环境要求

| 依赖 | 版本要求 |
|------|----------|
| Python | 3.10+ |
| DeepSeek API Key | 注册地址 https://platform.deepseek.com |
| 操作系统 | Windows / macOS / Linux |

其他兼容接口的模型（Anthropic Claude、OpenAI GPT）也可使用。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/THEST515/type-work-llm.git
cd type-work-llm
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

编辑 `config.yaml`，  注意！：请将cofig.yaml.example中的example字段手动删除，只留config.yaml!!  填写 API Key：

```yaml
model_provider: deepseek
model_name: deepseek-chat
api_key: "你的API Key"
api_base: https://api.deepseek.com
```

或通过环境变量设置：

```bash
# Windows CMD
set DEEPSEEK_API_KEY=你的API Key

# Linux / macOS
export DEEPSEEK_API_KEY=你的API Key
```

### 4. 运行

```bash
python agent.py --task design --input example-prd.md --output design/
```

---

## 使用方法

### CLI 命令

```bash
python agent.py --task design --input <需求文档> --output <输出目录> [选项]
```

### 常用示例

```bash
# 基本运行
python agent.py --task design --input example-prd.md --output design/

# 使用配置文件
python agent.py --task design --input example-prd.md --config config.yaml

# 生成指定类型的图表
python agent.py --task design --input requirements.md --diagrams class,activity

# 交互模式（生成后可手动调整）
python agent.py --task design --input requirements.md --interactive

# 换用其他模型
python agent.py --task design --input requirements.md --provider anthropic --model claude-sonnet-4-6
python agent.py --task design --input requirements.md --provider openai --model gpt-4o
```

### CLI 参数一览

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--task` | 任务类型：`design` | 必填 |
| `--input` | 输入的需求文档路径 | 必填 |
| `--output` | 输出目录 | `design/` |
| `--config` | YAML 配置文件路径 | 无 |
| `--provider` | 模型提供商：`deepseek` / `anthropic` / `openai` | `deepseek` |
| `--model` | 模型名称 | `deepseek-chat` |
| `--api-key` | API Key（也可用环境变量） | 自动读取 |
| `--api-base` | API 地址 | `https://api.deepseek.com` |
| `--diagrams` | 图表类型，逗号分隔：`class,activity,state` | 全部三种 |
| `--temperature` | 模型温度 (0.0-1.0) | `0.3` |
| `--verbose` | 显示详细执行日志 | 关闭 |
| `--interactive` | 半交互模式 | 关闭 |

### 交互模式命令

```bash
python agent.py --task design --input requirements.md --interactive
```

```
agent> class      # 重新生成类图
agent> activity   # 重新生成活动图
agent> state      # 重新生成状态机图
agent> all        # 重新生成全部图表
agent> summary    # 显示需求分析摘要
agent> quit       # 退出
```

---

## VSCode IDE 集成

项目已配置 `.vscode/tasks.json`，无需切换终端即可在 IDE 内运行。

| 操作 | 按键 |
|------|------|
| 分析当前打开的文件 | `Ctrl+Shift+B` |
| 选择任务（4个预设） | `Ctrl+Shift+P` → `Tasks: Run Task` |

预设任务：
- 智能体: 分析+设计（当前文件）
- 智能体: 分析+设计（example-prd）
- 智能体: 只生成类图+活动图
- 智能体: 交互模式

---

## 项目结构

```
circle/
├── agent.py                    # CLI 入口，argparse 命令行解析
├── config.yaml                 # YAML 配置文件
├── example-prd.md              # 示例需求文档（在线图书管理系统）
├── requirements.txt            # Python 依赖
├── .vscode/
│   ├── tasks.json              # VSCode 任务配置（Ctrl+Shift+B）
│   └── extensions.json         # 推荐插件（Mermaid Preview）
├── analysis-and-design.md      # 系统分析与设计文档（含类图/活动图/状态机图设计）
└── src/
    ├── models.py               # 数据模型（Entity, Behavior, AnalysisResult 等）
    ├── config.py               # 配置管理（YAML / 环境变量 / CLI 参数）
    ├── llm_adapter.py          # LLM 适配器（支持 DeepSeek / Anthropic / OpenAI）
    ├── analyzer.py             # 需求分析器（骨架提取 + 并发表格填充）
    ├── diagram_generators.py   # 图表生成器（类图 / 活动图 / 状态机图）
    ├── orchestrator.py         # 任务编排器（串行分析 + 并发图表生成）
    └── formatter.py            # 输出格式化（Mermaid 文件 + Markdown 报告）
```

---

## 系统架构

```
┌──────────────┐     ┌─────────────────┐     ┌────────────────────┐
│   CLI 接口    │────▶│   Orchestrator   │────▶│   OutputFormatter  │
│  (agent.py)  │     │ (orchestrator.py)│     │  (formatter.py)    │
└──────────────┘     └───────┬─────────┘     └────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌──────────┐  ┌──────────────┐  ┌──────────────────┐
       │ Analyzer │  │DiagramGens   │  │   LLMAdapter     │
       │(两阶段)  │  │(类/活动/状态)│  │(DeepSeek/Claude) │
       └──────────┘  └──────────────┘  └──────────────────┘
```

**核心设计**：
- **分析阶段**：骨架提取（1次快速调用）→ 并发细节填充（N实体+M行为同时跑），利用 ThreadPoolExecutor
- **图表阶段**：类图 + N张活动图 + M张状态机图并发生成
- **缓存优化**：所有同类型 LLM 调用共享相同 system prompt，可变信息放 user message 尾部，最大化 DeepSeek 缓存命中率
- **错误恢复**：JSON 解析失败自动修复（去尾部逗号、补全括号、LLM 自行修复三级策略）

---

## 输出产物

运行后在 `design/` 目录生成：

```
design/
├── README.md              # 产物索引
├── analysis.md            # 需求分析摘要（实体表、行为表、约束表）
├── class_diagram.mermaid  # 类图
├── activity_1_*.mermaid   # 活动图（每个核心行为一张）
└── state_1_*.mermaid      # 状态机图（每个有状态实体一张）
```

### 查看图表

- **VSCode**：安装 Mermaid Preview 插件（项目已推荐），打开 `.mermaid` 文件，按 `Ctrl+K V` 预览
- **在线**：复制内容到 [Mermaid Live Editor](https://mermaid.live/)
- **GitHub/GitLab**：直接嵌入 Markdown，平台自动渲染

---

## 配置说明

支持三种方式，优先级：CLI 参数 > YAML 配置文件 > 环境变量。

### 方式一：CLI 参数

```bash
python agent.py --task design --input requirements.md \
    --provider deepseek --model deepseek-chat --api-key sk-xxx
```

### 方式二：YAML 配置文件

```yaml
# config.yaml
model_provider: deepseek
model_name: deepseek-chat
api_key: "你的Key"
api_base: https://api.deepseek.com
temperature: 0.3
max_tokens: 8192
max_retries: 3
output_dir: design
diagrams:
  - class
  - activity
  - state
```

### 方式三：环境变量

| 变量名 | 说明 | 对应模型 |
|--------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | deepseek |
| `ANTHROPIC_API_KEY` | Anthropic API Key | anthropic |
| `OPENAI_API_KEY` | OpenAI API Key | openai |
| `AGENT_MODEL_PROVIDER` | 模型提供商 | 所有 |
| `AGENT_MODEL_NAME` | 模型名称 | 所有 |
| `AGENT_OUTPUT_DIR` | 输出目录 | 所有 |

---

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError` | 未安装依赖 | `pip install -r requirements.txt` |
| `AuthenticationError` | API Key 未设置或无效 | 检查 config.yaml 或环境变量 |
| `RateLimitError` | API 调用频率过高 | 稍等重试，程序内置指数退避重试 |
| `输入文件不存在` | 路径错误 | 使用绝对路径或确认文件在项目目录下 |
| 图表语法不对 | LLM 输出不稳定 | 程序自动校验修复；可使用 `--interactive` 重生成 |
| JSON 解析失败 | LLM 返回格式异常 | 三级修复策略自动处理，失败时打印原始响应 |
