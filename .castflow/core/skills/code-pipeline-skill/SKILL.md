---
name: code-pipeline-skill
description: code_pipeline code-pipeline OpenSpec pipeline requirement analysis delivery orchestration multi-agent multi-stage workflow NOT bootstrap castflow install
---

# Code Pipeline 工作流

**定位**：流程编排者（Process Orchestrator）。协调多 Skill / Agent 按标准工序协作，输出可追溯的工程决策与代码实现。

**不是**：代码生成者、规则定义者、执行引擎。

**适用**：多模块协作、跨系统改造、高风险功能。简单任务直接用 Skill / Agent，不走 pipeline。

---

## 快速导航

### 场景入口

- **单模块 / 小改动**：先看 Step 1、Step 3 的最小路径；通常跳过 Step 2，少量场景可跳过 Step 4
- **双模块依赖**：重点看 Step 1、Step 4、Step 5，确认 API 声明、依赖闭合和最终判定
- **多模块复杂协作**：重点看 Step 2、Handoff、Step 4、Step 5，先冻结边界，再并行实现

### 常见问题 -> 去哪里看

| 你想知道什么 | 去哪里看 |
|---|---|
| 这个需求要不要进 pipeline | 本页“场景入口” + “工作流总览” |
| 什么时候必须执行 Step 2 | `SKILL_MEMORY.md` 规则 3 + `EXAMPLES.md` 决策速查 |
| Handoff 什么时候需要、要写到什么程度 | `config/handoff_protocol.md` |
| Step 4 和 Step 5 的区别 | 本页“工作流总览” + `EXAMPLES.md` Step 4/5 判例 |
| PCB / run_id / PIPELINE_CONTEXT 是怎么工作的 | `config/pipeline_protocol.md` |
| 要抄模板或看判例 | `EXAMPLES.md` |
| 某个 agent 到底负责什么 | 对应 agent 文档 |

### 文件分层

- **入口层**：`SKILL.md`
- **规则层**：`SKILL_MEMORY.md`
- **机制层**：`config/pipeline_protocol.md`、`config/handoff_protocol.md`
- **模板 / 判例层**：`EXAMPLES.md`
- **执行层**：`requirement-analysis-agent.md`、`integration-matching-agent.md`、`pipeline-verify-agent.md`
- **维护层**：`ITERATION_GUIDE.md`

---

## 工作流总览

### Step 1：需求拆分 + API 声明 + Handoff Draft
- Agent：`requirement-analysis-agent`
- 解决的问题：这次需求要拆成哪些模块、谁提供什么 API、谁依赖谁
- 关键产物：功能拆分清单、API 声明表、依赖关系图、Handoff Draft、Step 2 / Step 3 建议
- 深读：`SKILL_MEMORY.md` 规则 2、`EXAMPLES.md` Step 1 样例、`requirement-analysis-agent.md`

### Step 2：约束同步 + BLUEPRINT + Handoff Freeze（可选）
- Agent：`requirement-analysis-agent`
- 解决的问题：跨模块协作前，哪些约束、签名、事件和边界必须先锁定
- 关键产物：PCB 中的 `SHADOW_BANS / CONFIG_SYNTHESIS / BLUEPRINT / ATOMIC_EXECUTION`，以及 Frozen Handoff
- 深读：`SKILL_MEMORY.md` 规则 3、`config/pipeline_protocol.md`、`config/handoff_protocol.md`

### Step 3：模块实现
- Agent：`programmer-{module}-agent`
- 解决的问题：各模块在已冻结边界内独立实现，并回写 Handoff Update
- 关键产物：代码、`temp/pipeline-output/{module_id}.md`、COMPLIANCE_CHECKLIST、Handoff Update
- 深读：`SKILL_MEMORY.md` 规则 4 / 10 / 11 / 14

### Step 4：依赖闭合（严格验证，禁止改代码）
- Agent：`integration-matching-agent`
- 解决的问题：Requires / Provides / TODO / 边界是否真的闭合
- 关键产物：Dependency Closure Report
- 深读：`SKILL_MEMORY.md` 规则 5 / 15、`config/handoff_protocol.md`、`EXAMPLES.md` Step 4 判例、`integration-matching-agent.md`

### Step 5：覆盖验收（仅决策，禁止改代码）
- Agent：`pipeline-verify-agent`
- 解决的问题：依赖闭合之后，业务完成度是否足够，最终能否 GO
- 关键产物：Done Criteria Coverage、Module / Global Verdict、`.pending_pipeline_result.json`
- 深读：`SKILL_MEMORY.md` 规则 6 / 15、`EXAMPLES.md` Step 5 判例、`pipeline-verify-agent.md`

### Step 6：补全 CompletableBlocks（可选）
- 触发时机：Step 5 = `GO-WITH-CAUTION`
- 关键要求：补完后至少回到 Step 4；若 Closure 变化影响 Coverage / Verdict，再回到 Step 5
- 深读：`config/handoff_protocol.md`“Step 6 Re-closure”

### Step 7：边界条件测试（可选）
- Skill：`debug-skill`

### Step 8：性能诊断（可选）
- Skill：`profiler-skill`

### Step 9：完成与清理
- 解决的问题：收尾、保留或清理上下文，以及终结 `pipeline_run_id`
- 深读：`SKILL_MEMORY.md` 规则 7、`config/pipeline_protocol.md` 协议 5

---

## 最小运行心智模型

### 1. 入口文件
`PIPELINE_CONTEXT.md` 是单一事实来源，头部是 PCB，看当前约束；尾部是 Step 记录，看当前进度。

### 2. 两类核心质量门
- **Handoff Freeze Gate**：进入 Step 3 前，先锁边界
- **Closure / Coverage / Verdict Gate**：Step 4 / Step 5 决定能否放行

### 3. 两类关键协议
- **pipeline_protocol**：讲执行期机制，解决 PCB、run_id、L1×L2 合成、协议触发
- **handoff_protocol**：讲模块协作机制，解决 Level、模板、Freeze、Update、Closure、Coverage

---

## 运行前置（按序加载）

1. `GLOBAL_SKILL_MEMORY.md` 协议 1-5
2. `config/pipeline_protocol.md` 协议 1-6
3. 涉及多 agent / 多模块协作时，按需读取 `config/handoff_protocol.md`
4. `config/params.schema.json` + `config/defaults.json` -> 合成 L1 参数
5. 项目 `CLAUDE.md` + 相关 `SKILL_MEMORY` -> 提取 L2 约束
6. 初始化 `PIPELINE_CONTEXT.md`（含 PCB 头部区 + run_id）

---

## 核心资产

**`PIPELINE_CONTEXT.md` 是单一事实来源**，含两个正交维度：

- **PCB 看板区**（头部，常驻）：`SHADOW_BANS / CONFIG_SYNTHESIS / MACRO_SCOPE / BLUEPRINT / ATOMIC_EXECUTION`
- **Step 段落区**（尾部，追加）：Step 1-9 流转记录

每个原子单元开工前都必须先读 `PIPELINE_CONTEXT.md`。PCB 未记录的逻辑视为无证据幻觉。

---

## L1 运行参数

- `execution_steps`：数组，要执行的步骤子集（Step1/3/4/5/9 为必选，其他可选）
- `context_retention`：`Cleanup` | `Persist`

详见 `config/params.schema.json`。

---

## 进化系统对接

pipeline 通过 `pipeline_run_id` 将 Step 3 的 trace 与 Step 5 的结果关联，为自我进化提供验证信号：

| Step 5 判定 | validated | 含义 |
|---|---|---|
| GO | true | 一次性合规，成功模式 |
| GO-WITH-CAUTION | true | 经补全后合规，包含可复用修复经验 |
| NO-GO | false | P0 反面教材 |

详见 `config/pipeline_protocol.md` 协议 5。
