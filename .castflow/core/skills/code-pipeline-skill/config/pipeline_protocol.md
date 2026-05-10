# Pipeline Protocol

> `code-pipeline` 组件的执行期控制真源。它只约束进入该复合组件的执行过程，不改写 shared components 的本体规则。Handoff 的模板、Freeze、Closure、Coverage 见 `config/handoff_protocol.md`。

## 组件 own 的运行态文件

- `PIPELINE_CONTEXT.md`：`code-pipeline` 的运行期状态文件
- `temp/pipeline-output/{module_id}.md`：Step 3 模块输出
- `pipeline_merge.py`：本组件 own 的运行时归并脚本
- pipeline result signal：本组件 own 的运行时回填信号；默认落点为 `.claude/traces/.pending_pipeline_result.json`

## Step 调度卡

shared agents / templates 不承载 `code-pipeline` 的写入路径、输出格式或回填信号规则。
这些合同只在本组件内部定义；主 agent 不得只说“执行 Step N”，必须把对应调度卡显式附带。

Step 3 / Step 6 中的“模块配对执行单元”指：
- 按 `module_id` 匹配到的 `programmer-<module>-agent`
- 以及该 agent 加载的同模块 `programmer-<module>-skill`

| Step | 给 | 读 | 写 | 交 | 不足兜底 |
|---|---|---|---|---|---|
| `1/2` `requirement-analysis-agent` | 用户请求、现有代码/文档证据、约束文件；Step 2 再附 Step 1 产物与 L1 参数 | `CLAUDE.md`、`GLOBAL_SKILL_MEMORY.md`、相关 `SKILL_MEMORY.md`；非文本输入先读原始资产 | `PIPELINE_CONTEXT.md` 头部：`pipeline_run_id` + PCB；Step 1 / Step 2 段落 | Step 1：功能拆分 / API 声明 / 依赖关系 / 类似功能检索结果 / 模块策略建议（默认优先依托已有能力迭代） / `UserDecision`（存在可复用候选时必填） / `Handoff Draft`（`L1+`）或 `No-Handoff Rationale`（`L0`）/ Handoff Level Decision / Freeze Recommendation / Step 2 建议 / Step 3 建议<br>Step 2：`SHADOW_BANS` / `CONFIG_SYNTHESIS` / `MACRO_SCOPE` / `BLUEPRINT` / `ATOMIC_EXECUTION` + `Frozen Handoff`（`L1+`） | 证据不足时，只输出资产清单 / 功能关联 / Open Questions，不得冻结 Handoff 或补造 API；若检索到可复用候选且用户尚未明确选择，则不得提前产出最终骨架或直接进入 Step 2 / Step 3 |
| `3` 模块配对执行单元 | `module_id`、当前模块声明、`Frozen Handoff`（`L1+`）或 Step 1 的 `L0` 决策记录 / `No-Handoff Rationale`（`L0`）、PCB / Blueprint 切片、相关 skill 约束；复杂系统模式下再附当前 `Wave Dispatch Table` 行与最新 `Checkpoint Record` | `PIPELINE_CONTEXT.md`、当前模块 Handoff（`L1+`）或 Step 1 的 `L0` 记录（`L0`）/ Blueprint / `CONFIG_SYNTHESIS`、必要跨模块 API 声明；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record` | 模块代码、`temp/pipeline-output/{module_id}.md` | 带固定标记的 `PIPELINE_SUMMARY` / `PIPELINE_DETAIL` / Handoff Update / COMPLIANCE_CHECKLIST | 依赖未就绪时，只能写规范 TODO + Handoff Update，不得编造 API 或跨界补实现；`L0` 场景一旦出现跨模块依赖，必须停止实现并回退升级到 `L1+`；复杂系统模式下若 dispatch 前置条件失效，必须停止实现并回写 checkpoint / recovery note |
| `4` `integration-matching-agent` | `closure_scope`（`local` / `global`）、Step 1 / Step 2 声明产物、Handoff / Handoff Update、Step 3 模块输出；复杂系统模式下必要时再附当前 wave / 子 pipeline 范围 | `PIPELINE_CONTEXT.md`、`temp/pipeline-output/{module_id}.md`；需要深读时读 `PIPELINE_DETAIL`；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record`，以及相关 `Parent Summary` | `PIPELINE_CONTEXT.md` 的 Step 4 段落 | `Dependency Closure Report`；必须显式标明 `Local Closure` 或 `Global Closure`，并保持分区齐全：`Closed / SignatureMismatch / MissingProvider / BoundaryViolation / CompletableBlocks / BlockingBlocks / ImplicitRequires` | 无法证明闭合时，不得写成 `Closed`，必须保守落入缺口类分区；局部 closure 一旦影响共享 contract，必须升级为全局 Step 4 重跑 |
| `5` `pipeline-verify-agent` | `verdict_scope`（`local` / `global`）、`Dependency Closure Report`、Done Criteria 输入、必要时附相关模块 `PIPELINE_DETAIL`；复杂系统模式下再附当前局部 verdict / `Checkpoint Record` | `PIPELINE_CONTEXT.md`、Step 4 报告、Done Criteria Coverage 输入；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record` | `PIPELINE_CONTEXT.md` 的 Step 5 段落；仅当 `verdict_scope = global` 且 verdict 已最终化时才写 pipeline result signal | `Done Criteria Coverage` / `VERIFICATION_REPORT`；局部验证必须显式输出 local verdict，全局最终验证才输出 result signal JSON：`{ pipeline_run_id, result, finalized }` | 证据不足时不得给 `GO`；至少把缺口写入 coverage / verdict reason，必要时回退到 Step 4 / Step 6；局部 verdict 一旦影响共享 contract 或全局 closure，必须升级为全局 Step 5 重跑 |
| `6` 模块配对执行单元 / `main agent` | Step 5 的 `CompletableBlocks`、受影响 `module_id`、最新 Handoff Update、相关 `PIPELINE_DETAIL`；复杂系统模式下再附当前 `Wave Dispatch Table` 行、最新 `Checkpoint Record` 与待重跑 scope | `PIPELINE_CONTEXT.md`、Step 4 closure、Step 5 coverage / verdict、目标模块最新输出；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record` | 模块代码、`temp/pipeline-output/{module_id}.md`、必要时追加 checkpoint | 更新后的 `PIPELINE_SUMMARY` / `PIPELINE_DETAIL` / Handoff Update / COMPLIANCE_CHECKLIST / re-closure note / checkpoint update | 只能补 `CompletableBlocks`；若发现新 blocker、dispatch 失效或局部修改已影响共享 contract，必须回写 checkpoint 并升级到对应的局部 / 全局重跑，而不是继续宣布完成 |
| `7` `debug-skill` | 目标模块 / 子域、边界条件清单、当前 closure / verdict / blocker 信息；复杂系统模式下再附当前 wave / checkpoint / recovery 语境 | `PIPELINE_CONTEXT.md`、Step 4 / Step 5 报告、相关 `PIPELINE_DETAIL`；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record` | `PIPELINE_CONTEXT.md` 的 Step 7 段落 | 边界条件测试结论、失败路径、修复建议、是否需要回退到 recovery / re-dispatch | 缺少可验证输入时，只能输出风险列表与建议补测项，不得给出“已验证通过”的结论 |
| `8` `profiler-skill` | 目标模块 / 路径、性能假设、当前实现证据；复杂系统模式下再附当前 wave / checkpoint / shared contract 语境 | `PIPELINE_CONTEXT.md`、相关 `PIPELINE_DETAIL`、必要时读 Step 4 / Step 5 报告；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record` | `PIPELINE_CONTEXT.md` 的 Step 8 段落 | 性能问题、瓶颈位置、优化建议、是否影响当前 wave / global verdict | 缺少性能证据时，只能输出假设与采样建议，不得把主观推测写成确定性瓶颈 |
| `9` `main agent` | 最终 global verdict、`execution_steps`、`context_retention`、最新 Step 4 / Step 5 / Step 6 结果；复杂系统模式下再附最新 `Checkpoint Record` 与全局状态 | `PIPELINE_CONTEXT.md`、最新 coverage / verdict、pipeline result signal 状态；复杂系统模式下必须先读最新 `Artifact State Table` / `Wave Dispatch Table` / `Checkpoint Record` | 清理后的 `PIPELINE_CONTEXT.md`（`Persist` 模式）或删除该文件（`Cleanup` 模式） | 最终清理结果：`Cleanup` / `Persist`、`pipeline_run_id` 终结状态、是否还存在待处理 signal / blocker | 未完成 run_id 清理、仍有未消费 signal、或全局 verdict 仍未收敛时，不得宣布 Step 9 完成 |

## 协议 1：L1 × L2 合成到 PCB

进入 Step 2，或虽跳过 Step 2 但即将进入 Step 3 前，必须把运行时参数与项目硬约束写入 PCB。

### L1 参数来源

- `config/params.schema.json`
- `config/defaults.json`

当前 L1 字段：

- `execution_steps`
- `context_retention`

### L2 约束来源

- 项目 `CLAUDE.md`
- `GLOBAL_SKILL_MEMORY.md`
- 相关 skill 的 `SKILL_MEMORY.md`

### 必须写入的 PCB 区块

| 区块 | 内容 |
|---|---|
| `SHADOW_BANS` | 禁止项 |
| `CONFIG_SYNTHESIS` | 命名、基类、命名空间、运行时参数 |
| `MACRO_SCOPE` | 功能点、模块关系、动线 |
| `BLUEPRINT` | 类、职责、Public API、事件契约 |
| `ATOMIC_EXECUTION` | 原子任务列表 |

进入 Step 3 前，`SHADOW_BANS` 与 `CONFIG_SYNTHESIS` 必须非空。

## 协议 2：非文本输入先双阶段解构

当 Step 1 输入包含 PDF、导图、截图或设计稿时，先输出：

1. 原始资产清单
2. 功能关联报告

用户确认前，禁止进入 API 声明与代码实现。输出位置在 `PIPELINE_CONTEXT.md` 的 Step 1 段落。

## 协议 3：实现前先读 PCB

每次进入 Step 3 / Step 6 的原子实现单元前，必须：

1. 读取 `PIPELINE_CONTEXT.md`
2. 对齐 `PCB.BLUEPRINT`
3. 对齐 `PCB.CONFIG_SYNTHESIS`

PCB 未记录的逻辑，不得直接实现。

## 协议 4：Step 3 模块输出与归并

每个模块输出到：

`temp/pipeline-output/{module_id}.md`

该文件必须包含两层：

- `PIPELINE_SUMMARY`
- `PIPELINE_DETAIL`

并且必须使用以下固定包裹标记：

```md
<!-- PIPELINE_SUMMARY -->
...
<!-- /PIPELINE_SUMMARY -->

<!-- PIPELINE_DETAIL -->
...
<!-- /PIPELINE_DETAIL -->
```

缺任一标记、重复标记、把 `Parent Summary` 混入该文件，或 `temp/pipeline-output/` 中没有任何模块产物时，`pipeline_merge.py` 必须 fail-closed，拒绝归并。

### 归并规则

- 默认运行时命令为 `python .claude/scripts/pipeline_merge.py`，它只提取 `PIPELINE_SUMMARY`
- 提取结果回写到 `PIPELINE_CONTEXT.md` 的受控 Step 3 归并块；重复执行时必须替换旧块而不是继续追加
- Step 4 / Step 5 深读模块实现时，读取 `PIPELINE_DETAIL`
- 若 Step 3 没有任何可归并产物，则 Step 4 / Step 5 不得继续推进

### 与 `Parent Summary` 的区别

- `PIPELINE_SUMMARY`：Step 3 模块实现摘要
- `Parent Summary`：子 pipeline 回传父 pipeline 的摘要

`Parent Summary` 只在 `config/handoff_protocol.md` 定义，不参与 Step 3 模块归并。

## 协议 5：`pipeline_run_id` 生命周期

每次完整 `code-pipeline` 生命周期都必须使用唯一 run_id：

`pipeline_{YYYYMMDD}_{HHMMSS}`

### Step 1：写入 run_id

写入 `PIPELINE_CONTEXT.md` 文件头部：

```md
pipeline_run_id: pipeline_20260420_143055
```

### Step 3：自动打标

`trace-flush` 看到 `pipeline_run_id:` 后，会把本次 Step 3 trace 记为 `pending-pipeline`。

### Step 5：写回填信号

`pipeline-verify-agent` 输出 verdict 后，必须写入本组件的 result signal。默认运行时落点为：

`.claude/traces/.pending_pipeline_result.json`

```json
{
  "pipeline_run_id": "pipeline_20260420_143055",
  "result": "GO",
  "finalized": true
}
```

`result` 取值：

- `GO`
- `GO-WITH-CAUTION`
- `NO-GO`

`finalized` 语义：

- `true`：当前 verdict 已是本次 pipeline 的最终可回填结果
- `false`：只允许与 `GO-WITH-CAUTION` 一起出现，表示还要进入 Step 6 / 重跑 Step 4 / Step 5

`trace-flush` 的回填语义：

- `GO` + `finalized=true` -> `validated=true`
- `GO-WITH-CAUTION` + `finalized=false` -> 保持 `validated=pending-pipeline`
- `GO-WITH-CAUTION` + `finalized=true` -> `validated=true`
- `NO-GO` -> `validated=false`

若 `validated=pending-pipeline` 长时间未被最终 verdict 覆盖，`trace-flush` 会按 `pipeline_pending_expire_days` 把它标记为 `invalid`。
非法或不完整的 result signal 不得被消费；hook 必须保留原文件，等待修复后重试。

### Step 9：清理 run_id

- `Cleanup`：`PIPELINE_CONTEXT.md` 随整体删除
- `Persist`：必须删除 `pipeline_run_id:` 行

禁止遗留过期 run_id。

## 协议 6：何时切到 Handoff 协议

满足任一条件时，必须读取 `config/handoff_protocol.md`：

- 需要 2+ agent 并行
- 存在跨模块 Requires / Provides
- 需要 Freeze Gate
- 需要 Step 4 / Step 5 的结构化 Closure / Coverage
- 存在 `L2` / `L3` Handoff

`HandoffStatus` 的定义和模板只以 `config/handoff_protocol.md` 为准。

## 协议 7：复杂系统模式产物

复杂系统模式激活后，`PIPELINE_CONTEXT.md` 除 PCB 与 Step 记录外，还必须维护以下四类产物。

### 术语边界

- `ArtifactState`：模块运行状态，主定义见 `architecture/artifact-state-machine.md`
- `HandoffStatus`：交接状态，主定义见 `config/handoff_protocol.md`

### `Artifact State Table`

最少字段：

| 字段 | 含义 |
|---|---|
| Module | 模块或子域 |
| Type | `SharedCore` / `Leaf` / `DomainComplex` / `SubPipeline` |
| ArtifactState | 当前运行状态 |
| DependsOn | 关键依赖 |
| CurrentBarrier | 当前受哪个 barrier 约束 |
| LastCheckpoint | 最近一次 checkpoint |

### `Wave Plan`

最少字段：

| 字段 | 含义 |
|---|---|
| Wave | 波次标识 |
| EntryCondition | 进入条件 |
| IncludedModules | 计划放行的模块 |
| DeferredModules | 暂缓模块 |
| ExitArtifact | 本波完成后必须出现的产物 |

### `Wave Dispatch Table`

最少字段：

| 字段 | 含义 |
|---|---|
| Wave | 当前波次 |
| Module | 将被放行的模块 |
| ArtifactState | 放行前状态 |
| Barrier | 当前已满足的 barrier |
| DispatchTarget | 匹配到的 `programmer-<module>-agent` / `sub-pipeline` / `main agent` |
| Inputs | 放行输入 |
| ExpectedOutput | 预期产物 |
| Fallback | 派发失败退路 |

### `Checkpoint Record`

最少字段：

| 字段 | 含义 |
|---|---|
| CheckpointId | 本次 checkpoint 标识 |
| Scope | 当前聚焦范围 |
| ArtifactState | 当前状态 |
| NewArtifacts | 新增产物 |
| BlockingArtifact | 当前真正阻塞的产物 |
| TimeboxUntil | 下一次必须重评的时点 |
| NextAction | 下一动作 |
| RecoveryAction | stalled 时的恢复动作 |

## 协议 8：复杂系统模式的读写顺序

复杂系统模式不是附加说明。进入该模式后，`Step 3 / Step 4 / Step 5 / Step 6` 的调度卡必须显式携带当前 wave / dispatch / checkpoint / verification scope 信息，不能只复用标准模式最小卡。

### 生成 `Wave Dispatch Table` 前必须读取

1. 最新 `Artifact State Table`
2. 最新 `Checkpoint Record`
3. 当前 `Wave Plan`
4. 对应模块的 Frozen Handoff

若无法说明“为什么现在能放行”，则不得生成新的 dispatch 行。

### 进入 dispatch 的前置条件

普通模块派发：

- `ArtifactState = Frozen`
- 对应 barrier 已满足
- `HandoffStatus = Frozen`
- 最新 `Checkpoint Record` 已说明放行原因
- 模块不处于 `Blocked / Stalled / NeedsSubpipeline`

显式 `sub-pipeline` 派发：

- `ArtifactState = NeedsSubpipeline`
- 最新 `Checkpoint Record` 已说明升级原因
- `DispatchTarget = sub-pipeline`
- `ExpectedOutput = Parent Summary`

### 派发后的回写

- 模块开始执行：`ArtifactState -> Implementing`
- 模块完成局部验证：状态更新由 `architecture/verification-architecture.md` 定义
- 派发失败、fallback 变化、或目标从普通派发改成 `sub-pipeline` / `main agent`：必须新增 `Checkpoint Record`
- 每一波结束后，至少更新一次 `Artifact State Table`、`Wave Dispatch Table`、`Checkpoint Record`

### Heartbeat 与 checkpoint

- `heartbeat`：短状态反馈
- `Checkpoint Record`：可复用的正式记录

复杂系统模式下，不能只有 heartbeat，没有 checkpoint。
