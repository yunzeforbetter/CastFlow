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
2. `config/pipeline_protocol.md`
3. 进入 `L1+`、多模块协作或需要 Freeze / Closure / Coverage 时，再读 `config/handoff_protocol.md`
4. 进入复杂系统模式后，再按需读取对应主定义页：
   - 总模型：`architecture/orchestration-model.md`
   - 状态：`architecture/artifact-state-machine.md`
   - barrier / wave / dispatch：`architecture/barrier-and-wave-scheduling.md`
   - 子 pipeline：`architecture/subpipeline-strategy.md`
   - stalled / recovery：`architecture/stall-recovery.md`
   - 局部 / 全局验证：`architecture/verification-architecture.md`
5. 需要模板或判例时读取 `EXAMPLES.md` 与 `examples/*`

## 工作流总览

精确调度合同、读写路径与返回结构见 `config/pipeline_protocol.md` 的“Step 调度卡”；本页负责回答“现在走到哪一步、这一步解决什么、下一步该去哪里”。

### Step 1：需求拆分 + API 声明 + Handoff Draft / No-Handoff Rationale
- 执行单元：`requirement-analysis-agent`
- 解决的问题：这次需求要拆成哪些模块、谁提供什么 API、是否需要进入 `L1+` 协作
- 关键产物：功能拆分、API 声明、依赖关系、`Handoff Draft`（`L1+`）或 `No-Handoff Rationale`（`L0`）、Handoff Level Decision、Freeze Recommendation、Step 2 / Step 3 建议
- 下一步出口：明确进入 Step 2、直接进 Step 3、先回用户关闭 `UserDecision`，或升级为子 pipeline
- 深读：`SKILL_MEMORY.md` 规则 2 / 3 / 10、`EXAMPLES.md` 的 Step 1 / Handoff 样例

### Step 2：约束同步 + BLUEPRINT + Handoff Freeze
- 执行单元：`requirement-analysis-agent`
- 解决的问题：跨模块协作前，哪些约束、签名、事件与边界必须先锁死
- 关键产物：PCB、`BLUEPRINT`、`Frozen Handoff`（`L1+`）；复杂系统时补 `Artifact State Table`、`Wave Plan`
- 触发条件：`SKILL_MEMORY.md` 规则 3 命中，或复杂系统模式需要先冻结共享底座
- 深读：`config/pipeline_protocol.md`、`config/handoff_protocol.md`

### Step 3：模块实现
- 执行单元：模块配对执行单元；`L0` 快速路径允许单个 `main agent` 或单模块实现单元直接推进
- 解决的问题：各模块在 Frozen 边界（`L1+`）或单模块职责（`L0`）内独立实现
- 关键产物：代码、`temp/pipeline-output/{module_id}.md`、Handoff Update、COMPLIANCE_CHECKLIST
- 进入门槛：`L1+` 必须先过 Freeze Gate；`L0` 必须已有 `No-Handoff Rationale`，且一旦出现跨模块依赖立即回退升级到 `L1+`
- 深读：`SKILL_MEMORY.md` 规则 4 / 5 / 10 / 11、`EXAMPLES.md` 的 Step 3 模板

### Step 4：依赖闭合
- 执行单元：`integration-matching-agent`
- 解决的问题：Requires / Provides / TODO / 边界是否真的闭合
- 关键产物：Dependency Closure Report
- 约束：只验证，不改代码；无法证明闭合时必须保守落入缺口类分区
- 深读：`config/handoff_protocol.md` 的 closure 模板、`EXAMPLES.md` 判例

### Step 5：覆盖验收
- 执行单元：`pipeline-verify-agent`
- 解决的问题：在 closure 基础上判断业务完成度是否足够，最终是否 `GO / GO-WITH-CAUTION / NO-GO`
- 关键产物：Done Criteria Coverage、VERIFICATION_REPORT、pipeline result signal
- 下一步出口：`GO` 进入 Step 9；`GO-WITH-CAUTION` 进入 Step 6；`NO-GO` 回 recovery / re-dispatch
- 深读：`config/pipeline_protocol.md` 协议 5、`config/handoff_protocol.md` 的 coverage / re-closure 约束

### Step 6：补全 CompletableBlocks
- 执行单元：模块配对执行单元 / `main agent`
- 触发时机：Step 5 = `GO-WITH-CAUTION`
- 关键要求：只补 `CompletableBlocks`；补完后至少重跑 Step 4，若 closure 变化影响 coverage / verdict，再重跑 Step 5

### Step 7：边界条件测试
- 执行单元：`debug-skill`
- 输出：问题列表与修复建议

### Step 8：性能诊断
- 执行单元：`profiler-skill`
- 输出：性能问题与优化建议

### Step 9：完成与清理
- 执行单元：`main agent`
- 解决的问题：终结 pipeline、清理或保留上下文，以及处理 `pipeline_run_id`
- 深读：`config/pipeline_protocol.md` 协议 5、`SKILL_MEMORY.md` 规则 12

## 最小运行心智模型

### 1. 单一事实来源
`PIPELINE_CONTEXT.md` 是本组件的单一事实来源：头部 PCB 看当前约束，Step 段落看当前进度。

### 2. 三个关键门
- Step 1 / Step 2：决定当前走 `L0`、`L1+` 还是复杂系统模式
- Step 3：只有 Freeze Gate 或 `L0` 快速路径满足时才允许实现
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
