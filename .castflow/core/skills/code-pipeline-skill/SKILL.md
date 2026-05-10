---
name: code-pipeline-skill
description: code_pipeline code-pipeline 功能开发流程编排 Step1需求拆分 Step2约束冻结 Step3模块实现 Step4依赖闭合 Step5验收 verdict 多模块 复杂系统 子pipeline
---

# Code Pipeline 工作流

`code-pipeline-skill` 是一个复合组件：它组合 shared agents、模块配对执行单元与可选 skill，在 pipeline 执行期间维护自己的 component-owned 协议与运行态文件；它不定义 shared components 的本体规则。

## 场景入口

- 标准模式：单模块、双模块、依赖链短，但仍需要 Step 1 / 3 / 4 / 5 的最小闭环
- 复杂系统模式：3+ 模块、共享契约重、需要 wave / dispatch / checkpoint / sub-pipeline
- 简单局部改动：若一个 skill 或单个 agent 就能收敛，不值得启 pipeline

## AI 读取顺序

1. `SKILL_MEMORY.md`
2. `config/step_contracts.md`
3. `config/pipeline_protocol.md`
4. 进入 `L1+`、多模块协作或需要 Freeze / Closure / Coverage 时，再读 `config/handoff_protocol.md`
5. 进入复杂系统模式后，再按需读取对应主定义页：
   - 总模型：`architecture/orchestration-model.md`
   - 状态：`architecture/artifact-state-machine.md`
   - barrier / wave / dispatch：`architecture/barrier-and-wave-scheduling.md`
   - 子 pipeline：`architecture/subpipeline-strategy.md`
   - stalled / recovery：`architecture/stall-recovery.md`
   - 局部 / 全局验证：`architecture/verification-architecture.md`
6. 需要模板或判例时读取 `EXAMPLES.md` 与 `examples/*`

## 工作流总览

Step 1-9 的唯一 Step 收口页与 Step 级强规则入口见 `config/step_contracts.md`；执行期的精确调度合同、读写路径与返回结构见 `config/pipeline_protocol.md` 的“Step 调度卡”。本页只负责回答“什么时候应该启 pipeline、现在走到哪一步、下一步该去哪里”。

## Step 导航

| Step | 执行单元 | 本页只保留的导航信息 | 深读 |
|---|---|---|---|
| Step 1 | `requirement-analysis-agent` | 做路线判定；若 Step 1 门禁未过，只能补分析或回用户，不得进入后续实现链路 | `config/step_contracts.md`、`EXAMPLES.md` |
| Step 2 | `requirement-analysis-agent` | 只在命中冻结条件时进入；完成后才允许进入需要 Freeze 的实现链路 | `config/step_contracts.md`、`config/pipeline_protocol.md`、`config/handoff_protocol.md` |
| Step 3 | 模块配对执行单元 / `main agent`（`L0`） | 负责实现；进入前必须确认路线门禁与 Freeze Gate 已过 | `config/step_contracts.md`、`EXAMPLES.md` |
| Step 4 | `integration-matching-agent` | 只做依赖闭合验证，不改代码 | `config/step_contracts.md`、`config/handoff_protocol.md` |
| Step 5 | `pipeline-verify-agent` | 只做 coverage / verdict 决策，不改代码 | `config/step_contracts.md`、`config/pipeline_protocol.md`、`config/handoff_protocol.md` |
| Step 6 | 模块配对执行单元 / `main agent` | 只补 `CompletableBlocks`，补完后至少回 Step 4 | `config/step_contracts.md`、`config/handoff_protocol.md` |
| Step 7 | `debug-skill` | 只在需要边界条件验证时进入 | `config/step_contracts.md` |
| Step 8 | `profiler-skill` | 只在需要性能诊断时进入 | `config/step_contracts.md` |
| Step 9 | `main agent` | 必做收尾；未完成 run_id / signal 清理不得结束 pipeline | `config/step_contracts.md`、`config/pipeline_protocol.md` |

## 最小运行心智模型

### 1. 单一事实来源
`PIPELINE_CONTEXT.md` 是本组件的单一事实来源：头部 PCB 看当前约束，Step 段落看当前进度。

### 2. 三个关键门
- Step 1：先完成类似功能检索、路线推荐与必要的 `UserDecision`
- Step 2 / Step 3：只有 Step 1 路线门禁与 Freeze Gate 满足时才允许冻结或实现
- Step 4 / Step 5：决定是进入 Step 6 补全，还是进入 Step 9 收尾

### 3. 复杂系统模式不是“更多并行”
复杂系统模式下，主流程看 `ArtifactState`、wave readiness、dispatch scope、checkpoint，而不是把所有模块一次性开工。

## 组件边界

- shared inputs：项目 `CLAUDE.md`、`GLOBAL_SKILL_MEMORY.md`、相关 skill 的 `SKILL_MEMORY.md`、shared agents、模块配对执行单元
- component-owned runtime state：`PIPELINE_CONTEXT.md`、`temp/pipeline-output/{module_id}.md`、pipeline result signal
- component-owned runtime binding：运行时投影脚本 `pipeline_merge.py`
- 本组件可以消费 shared components，但不要求 shared components 把自己的本体规则改写成 pipeline 语义

## Step 3 输出归并

- 每个模块输出到 `temp/pipeline-output/{module_id}.md`
- 该文件分为两层：`PIPELINE_SUMMARY` 与 `PIPELINE_DETAIL`
- 本组件 own 的运行时投影脚本 `pipeline_merge.py` 只提取 `PIPELINE_SUMMARY` 并合并回 `PIPELINE_CONTEXT.md`
- Step 4 / Step 5 深读模块实现时，读取 `PIPELINE_DETAIL`
- 双层输出的最小模板看 `EXAMPLES.md`
- `Parent Summary` 只用于子 pipeline 回传父 pipeline，不等于 Step 3 模块 summary；定义见 `config/handoff_protocol.md`

## 最小质量门

- 在 `code-pipeline` 执行期间，`PIPELINE_CONTEXT.md` 是本组件的单一事实来源
- 进入 Step 3 前：`L1+` 先过 Handoff Freeze Gate，`L0` 走 No-Handoff 快速路径
- Step 4 只验证，不改代码
- Step 5 只决策，不改代码
- Step 9 必须执行

## 复杂系统模式的主判断

- 主流程看 `ArtifactState`、barrier、wave readiness，而不是只等某个 agent 结束
- 共享底座优先冻结
- 只有满足局部 barrier 的模块才进入当前 wave
- `NeedsSubpipeline / Stalled / Blocked` 不进入普通模块配对执行单元派发
- 进入复杂系统模式后，`Step 3 / Step 4 / Step 5 / Step 6` 的调度必须显式携带 wave / dispatch / checkpoint / verification scope，而不是沿用标准模式最小卡

## 主定义页

| 主题 | 文件 |
|---|---|
| 执行期控制、PCB、run_id、复杂系统产物 | `config/pipeline_protocol.md` |
| Handoff、Freeze、Closure、Coverage、Parent Summary | `config/handoff_protocol.md` |
| `ArtifactState` 与派发资格 | `architecture/artifact-state-machine.md` |
| barrier / wave / dispatch | `architecture/barrier-and-wave-scheduling.md` |
| 子 pipeline 升级与回传 | `architecture/subpipeline-strategy.md` |
| stalled / heartbeat / checkpoint / recovery | `architecture/stall-recovery.md` |
| 局部 / 全局验证与重跑 | `architecture/verification-architecture.md` |
