---
name: code-pipeline-skill
description: code_pipeline code-pipeline 功能开发流程编排 Step1需求拆分 Step2约束冻结 Step3模块实现 Step4依赖闭合 Step5验收 verdict 多模块 复杂系统 子pipeline
---

# Code Pipeline 工作流

`code-pipeline-skill` 是一个复合组件：它组合 shared agents、模块配对执行单元与可选 skill，在 pipeline 执行期间维护自己的协议与运行态投影；它不定义 shared components 的本体规则。

## 场景入口

- 标准模式：单模块、双模块、依赖链短，但仍需要 Step 1 / 3 / 4 / 5 的最小闭环
- 复杂系统模式：3+ 模块、共享契约重、需要 wave / dispatch / checkpoint / sub-pipeline
- 简单局部改动：若一个 skill 或单个 agent 就能收敛，不值得启 pipeline
- 但只要输入包含 PRD / 外部需求文档 / 设计稿，或执行者尚未掌握该功能域的现有承载面，就不得以“简单局部改动”为由跳过 pipeline；至少先完成一次 Step 1

## AI 读取顺序

1. `SKILL_MEMORY.md`
2. `config/step_contracts.md`
3. `config/pipeline_protocol.md`
4. 进入 `L1+`、多模块协作或需要 Freeze / Closure / Coverage 时，再读 `config/handoff_protocol.md`
5. 需要 runtime state 真身时，读 `config/runtime_state_schema.md`
6. 进入复杂系统模式后，再按需读取对应主定义页：
   - 总模型：`architecture/orchestration-model.md`
   - 状态：`architecture/artifact-state-machine.md`
   - barrier / wave / dispatch：`architecture/barrier-and-wave-scheduling.md`
   - 子 pipeline：`architecture/subpipeline-strategy.md`
   - stalled / recovery：`architecture/stall-recovery.md`
   - 局部 / 全局验证：`architecture/verification-architecture.md`
7. 需要模板或判例时读取 `EXAMPLES.md` 与 `examples/*`

## Step 1 快速门

- 在 `code-pipeline` 模式下，Step 1 的正文必须显式出现独立的 `### CapabilityScan` block，不能用 Phase 叙事、PRD 摘要或一句“已检索”代替
- `CapabilityScan` 至少要写出 `MatchedCapabilities`、`CandidateHosts`、`Evidence`、`Recommendation`；即使未命中可复用承载，也必须显式写 `None` / `未命中`，不能省略
- `Evidence` 只接受项目代码路径、符号、检索范围与命中说明；PRD、用户口述、设计说明只能定义 `scan scope`，不能单独充当源码证据
- 未满足以上条件时，主流程只能维持 `Discovering` 或 `PendingDecision`，不得宣布 Step 1 完成，更不得进入 Step 2 / Step 3

## 工作流总览

Step 1-9 的唯一 Step 收口页与 Step 级强规则入口见 `config/step_contracts.md`；执行期的精确调度合同、状态迁移与读写路径见 `config/pipeline_protocol.md`。本页只回答三件事：什么时候启 pipeline、每一步由谁执行、接下来该深读哪里。

Step 1 内部允许按 `DecompositionSnapshot`（拆解快照） -> `CapabilityScan`（能力探寻） -> `ArtifactBinding`（产物绑定） -> `DecisionSynthesis`（决策综合）做认知分治；scan 类任务可以拆给只读 subagent，但 `decision_status`、`Handoff Level Decision`、`Freeze Recommendation` 仍只由 Step 1 聚合层写回。

## Step 导航

| Step | 执行单元 | 导航信息 | 深读 |
|---|---|---|---|
| Step 1 | `requirement-analysis-agent` | 先产出 `DecompositionSnapshot`；复杂认知优先拆给只读 scan subagent；若 `CapabilityScan` 无独立 block 或缺少源码 `Evidence`，视为 Step 1 未完成；若存在路线分歧，必须停在决策态，不能直接推进实现 | `config/step_contracts.md`、`config/pipeline_protocol.md` |
| Step 2 | `requirement-analysis-agent` | 只在路线已收敛且命中冻结条件时进入 | `config/step_contracts.md`、`config/pipeline_protocol.md`、`config/handoff_protocol.md` |
| Step 3 | 模块配对执行单元 / `main agent`（`L0`） | 负责实现；进入前必须确认决策态已解决且 Freeze Gate 已过 | `config/step_contracts.md`、`config/pipeline_protocol.md` |
| Step 4 | `integration-matching-agent` | 只做依赖闭合验证，不改代码 | `config/step_contracts.md`、`config/handoff_protocol.md` |
| Step 5 | `pipeline-verify-agent` | 只做 coverage / verdict 决策，不改代码 | `config/step_contracts.md`、`config/pipeline_protocol.md`、`config/handoff_protocol.md` |
| Step 6 | 模块配对执行单元 / `main agent` | 只补 `CompletableBlocks`，补完后至少回 Step 4 | `config/step_contracts.md`、`config/handoff_protocol.md` |
| Step 7 | `debug-skill` | 只在需要边界条件验证时进入 | `config/step_contracts.md` |
| Step 8 | `profiler-skill` | 只在需要性能诊断时进入 | `config/step_contracts.md` |
| Step 9 | `main agent` | 必做收尾；未完成 run_id / signal 清理不得结束 pipeline | `config/step_contracts.md`、`config/pipeline_protocol.md` |

## 最小运行心智模型

### 1. 真相与投影分离
- 运行期 gate 真相由 `PIPELINE_CONTEXT.md` 顶部固定状态头承载
- `PIPELINE_CONTEXT.md` 正文只做投影与归档
- `temp/pipeline-output/{module_id}.md` 只承载模块实现结果

### 2. 三个关键门
- Step 1：先完成 `DecompositionSnapshot`、`CapabilityScan` 与必要的 `ArtifactBinding`，再进入 `DecisionSynthesis`
- Step 2 / Step 3：只有路线已收敛且 Freeze Gate 满足时才允许冻结或实现
- Step 4 / Step 5：决定是进入 Step 6 补全，还是进入 Step 9 收尾

### 3. 复杂系统模式不是“更多并行”
复杂系统模式下，主流程看 `ArtifactState`、wave readiness、dispatch scope、checkpoint，而不是把所有模块一次性开工。

## 组件边界

- shared inputs：项目 `CLAUDE.md`、`GLOBAL_SKILL_MEMORY.md`、相关 skill 的 `SKILL_MEMORY.md`、shared agents、模块配对执行单元
- component-owned runtime truth：`PIPELINE_CONTEXT.md` 顶部状态头、pipeline result signal
- component-owned runtime projection：`PIPELINE_CONTEXT.md` 正文、`temp/pipeline-output/{module_id}.md`
- component-owned runtime binding：运行时投影脚本 `pipeline_merge.py`

## Step 3 输出归并

- 每个模块输出到 `temp/pipeline-output/{module_id}.md`
- 该文件分为两层：`PIPELINE_SUMMARY` 与 `PIPELINE_DETAIL`
- `pipeline_merge.py` 只提取 `PIPELINE_SUMMARY` 并合并回 `PIPELINE_CONTEXT.md`
- Step 4 / Step 5 深读模块实现时，读取 `PIPELINE_DETAIL`
- `Parent Summary` 只用于子 pipeline 回传父 pipeline，不等于 Step 3 模块 summary；定义见 `config/handoff_protocol.md`

## 主定义页

| 主题 | 文件 |
|---|---|
| 执行期控制、状态迁移、run_id、复杂系统产物 | `config/pipeline_protocol.md` |
| Handoff、Freeze、Closure、Coverage、Parent Summary | `config/handoff_protocol.md` |
| `ArtifactState` 与派发资格 | `architecture/artifact-state-machine.md` |
| barrier / wave / dispatch | `architecture/barrier-and-wave-scheduling.md` |
| 子 pipeline 升级与回传 | `architecture/subpipeline-strategy.md` |
| stalled / heartbeat / checkpoint / recovery | `architecture/stall-recovery.md` |
| 局部 / 全局验证与重跑 | `architecture/verification-architecture.md` |
