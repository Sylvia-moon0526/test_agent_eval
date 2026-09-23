# 📊 Agent Eval Suite — AI Agent 自动化评测体系与可视化看板

<div align="center">

**Case 驱动评测 · LLM-as-Judge 多维打分 · Streamlit 实时看板**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/pytest-8.0%2B-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 📌 项目概述

Agent Eval Suite 是一套面向 AI Agent 的 **自动化质量评测体系**。它解决了 Agent 开发中的核心痛点——**"Agent 搭好了，怎么知道它到底好不好？"**

系统实现了从 **测试用例定义 → 批量自动执行 → 多维度指标计算 → LLM 评审打分 → 可视化看板** 的完整评测管线，为 Agent 的迭代优化提供数据支撑。


本项目测试基于 [Multi_tool_agent](https://github.com/Sylvia-moon0526/Multi_tool_agent.git) 进行开发，使用时请根据需要进行测试的Agent改变对应路径。


### 核心问题

| 痛点 | 本系统的解决方案 |
|:---|:---|
| Agent 输出质量难以量化 | 四维指标体系：关键词命中率 + 工具正确性 + 推理效率 + LLM Judge |
| 评测靠人肉、不可复现 | pytest 驱动的自动化管线，Case 参数化批量执行 |
| 结果不直观、难以定位问题 | Streamlit Dashboard 实时可视化，支持下钻到单个 Case 详情 |
| 评测标准不一致 | LLM-as-Judge 统一评分标准，消除人工评审的主观偏差 |

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Agent Eval Suite 全景架构                          │
│                                                                      │
│  ┌────────────────┐   ┌────────────────┐   ┌────────────────────┐    │
│  │ eval_cases.json│   │ test_agent_eval│   │    judge.py        │    │
│  │  (测试用例定义) │──>│  (评测执行引擎) │──>│ (LLM-as-Judge)     │    │
│  │                │   │                │   │                    │    │
│  │  • 输入问题     │   │  • Agent调用   │   │  • 正确性 (1-5)     │   │
│  │  • 期望工具     │   │  • 指标计算     │   │  • 完整性 (1-5)    │    │
│  │  • 期望关键词   │   │  • 结果记录     │   │  • 有用性 (1-5)    │    │
│  │  • 推理上限     │   │  • 耗时统计     │   │  • 综合评分 + 理由  │   │
│  └────────────────┘   └───────┬────────┘   └────────────────────┘    │
│                               │                                      │
│                               ▼                                      │
│                    ┌────────────────────┐                            │
│                    │ eval_results.json  │                            │
│                    │  (评测结果存储)     │                            │
│                    └─────────┬──────────┘                            │
│                              │                                       │
│                              ▼                                       │
│                    ┌────────────────────┐                            │
│                    │   dashboard.py     │                            │
│                    │ (Streamlit 可视化)  │                            │
│                    │                    │                            │
│                    │ • 总览指标卡片      │                            │
│                    │ • 分类通过率柱状图  │                            │
│                    │ • 详细结果数据表    │                            │
│                    │ • 单 Case 下钻详情  │                            │
│                    └────────────────────┘                            │
│                                                                      │
│  评测对象: Project1 Multi-Tool Agent (跨项目复用)                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术选型 | 说明 |
|:---|:---|:---|
| **评测引擎** | pytest + parametrize | Case 参数化驱动，一个函数跑所有用例 |
| **评测对象** | Project1 Multi-Tool Agent | 跨项目复用，验证评测体系通用性 |
| **LLM 评审** | LLM-as-Judge (Qwen3.5-9B) | 独立 LLM 从三维度打分，消除人工偏差 |
| **可视化看板** | Streamlit | 实时渲染评测结果，支持筛选和下钻 |
| **数据存储** | JSON 文件 | 轻量级，便于 Git 追踪和 CI 集成 |

---

## 📐 评测指标体系

### 四维评测模型

```
┌─────────────────────────────────────────────────────┐
│              Agent 质量评测四维模型                  │
│                                                     │
│  ┌──────────────┐       ┌──────────────┐            │
│  │ 1.关键词命中率│       │ 2.工具正确性  │            │
│  │              │       │              │            │
│  │ 答案是否包含  │       │ 是否调用了    │            │
│  │ 期望关键词    │       │ 正确的工具    │            │
│  │              │       │              │            │
│  │ score = hits │       │ match =      │            │
│  │  / total     │       │  expected ⊆  │           │
│  │              │       │  actual      │            │
│  └──────────────┘       └──────────────┘            │
│                                                     │
│  ┌──────────────┐       ┌──────────────┐            │
│  │ 3.推理效率    │       │ 4.LLM Judge  │            │
│  │              │       │              │            │
│  │ 工具调用轮数  │       │ 独立LLM三维度 │            │
│  │ 是否超出上限  │       │ 打分取均值    │            │
│  │              │       │              │            │
│  │ rounds ≤     │       │ avg = (正确性 │            │
│  │ max_rounds   │       │  + 完整性     │            │
│  │              │       │  + 有用性)/3  │            │
│  └──────────────┘       └──────────────┘            │
└─────────────────────────────────────────────────────┘
```

### 指标详解

| 指标 | 计算方式 | 判断标准 | 意义 |
|:---|:---|:---|:---|
| **关键词命中率** | `hits / total_keywords` | ≥ 50% 通过 | 验证答案内容是否命中核心信息点 |
| **工具使用正确性** | `expected_tools ⊆ used_tools` | 完全匹配 | 验证 Agent 是否选择了正确的工具 |
| **推理效率** | `tool_call_rounds` | ≤ `max_rounds` | 约束 Agent 不要过度推理、浪费 token |
| **LLM-as-Judge** | 独立 LLM 评分 (1-5) | ≥ 3.0 为合格 | 从语义层面评估答案质量，弥补关键词匹配的局限 |

### 测试用例分类

| 分类 | 用例数 | 评测重点 |
|:---|:---|:---|
| `single_tool` | 3 | 单工具调用正确性 |
| `multi_tool` | 2 | 多工具链式编排能力 |
| `error_recovery` | 2 | 异常输入的优雅降级 |

---

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- Project1 (Multi-Tool Agent) 已配置完成
- SiliconFlow API Key

### 安装 & 运行

```bash
# 1. 进入项目目录
cd project3_eval

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
export SILICONFLOW_API_KEY="sk-your-key"

# 4. 运行评测
pytest tests/test_agent_eval.py -v --tb=short

# 5. 查看可视化看板
streamlit run dashboard.py
```

---

## 📊 Dashboard 功能说明

### 总览面板

启动后首页展示四个核心指标卡片：

| 指标卡片 | 说明 |
|:---|:---|
| **总计用例** | 评测覆盖的 Case 总数 |
| **通过率** | `passed / total` 百分比 |
| **关键词命中率** | 所有通过 Case 的平均关键词命中率 |
| **Judge 评分** | LLM-as-Judge 的平均综合评分 (1-5) |

### 分类通过率柱状图

按 `single_tool` / `multi_tool` / `error_recovery` 分类展示通过率，快速定位薄弱环节。

### 详细结果表

支持按分类筛选，每行展示：

| 字段 | 说明 |
|:---|:---|
| Case ID | 唯一标识 |
| 状态 | ✅ pass / ❌ fail |
| 关键词命中率 | 百分比 |
| 工具匹配 | 是否调用了正确工具 |
| 推理轮数 | 工具调用次数 |
| 耗时 | 执行时间 (秒) |
| Judge 评分 | LLM 综合评分 |

### 单 Case 下钻

选择具体 Case 后展示：
- 原始输入
- Agent 输出预览
- 期望 vs 实际工具调用对比
- 性能指标详情

---

## 📁 项目结构

```
project3_eval/
├── dashboard.py              # Streamlit 可视化面板
├── judge.py                  # LLM-as-Judge 评分器
├── tests/
│   ├── eval_cases.json       # 测试用例定义（7 个 Case，3 个分类）
│   └── test_agent_eval.py    # 评测执行脚本（pytest 参数化）
├── results/                  # 评测结果输出（自动生成）
├── requirements.txt          # 依赖清单
└── README.md
```

---

## 📐 设计决策与工程思考

### 为什么用 LLM-as-Judge 而非纯规则评测？

| 方案 | 优势 | 局限 |
|:---|:---|:---|
| **纯规则（关键词/正则）** | 确定性强、成本低 | 无法评估语义质量，容易"关键词对了但答案不对" |
| **人工评审** | 最准确 | 不可规模化、主观偏差大、不可复现 |
| **LLM-as-Judge** | 语义理解、可规模化、成本可控 | 存在评分偏差，需配合规则评测交叉验证 |

本系统采用 **"规则 + LLM" 双轨制**：关键词命中率和工具正确性提供确定性底线，LLM Judge 补充语义层面的评估。

### 为什么评测对象跨项目复用 Project1？

- **通用性验证**：评测体系不绑定特定 Agent，可复用到任何 Agent 项目
- **解耦设计**：评测引擎通过 `sys.path` 引入目标 Agent，无需耦合代码
- **扩展性**：新增评测对象只需修改 import 路径，Case 定义完全独立

### 为什么用 pytest parametrize 而非自定义 runner？

- **生态兼容**：复用 pytest 的报告、CI 集成、插件生态
- **参数化驱动**：一个 `@pytest.mark.parametrize` 即可批量跑所有 Case
- **失败隔离**：单个 Case 失败不影响其他用例执行

---

## 🔮 扩展路线

- [ ] **CI/CD 集成**：GitHub Actions 每次 PR 自动跑评测，通过率低于阈值则阻断合并
- [ ] **评测 Case 自动生成**：用 LLM 基于 Agent 工具描述自动生成测试用例
- [ ] **回归检测**：对比两次评测结果，标记退化的 Case
- [ ] **多 Agent 评测**：支持同时评测多个 Agent，横向对比
- [ ] **成本统计**：记录每个 Case 的 token 消耗和 API 调用成本
- [ ] **评分一致性校准**：引入多个 Judge 交叉评分，计算 Cohen's Kappa

---

## 📄 License

MIT

---

<div align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给个 Star 支持！</strong>
</div>


