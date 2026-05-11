# Handoff Protocol

> `code-pipeline` 内的 Handoff 真源。这里只定义 `HandoffStatus`、Freeze、Closure、Coverage、Re-closure 与 `Parent Summary` 的控制语义。执行期控制见 `config/pipeline_protocol.md`。

## 1. Handoff Level

| Level | 何时使用 | 必须字段 |
|---|---|---|
| `L0` | 单模块、单 agent、无跨模块依赖 | 无正式 Handoff；Step 1 必须记录 `Handoff Level Decision = L0` 与 `No-Handoff Rationale` |
| `L1` | 2-3 个模块，依赖简单 | `Owns / Provides / Requires / Blocks` |
| `L2` | 3+ 模块、共享契约、并行实现、风险较高 | `L1` + `Goal / Constraints / Done Criteria / Open Questions` |
| `L3` | 模块内部仍需拆子 pipeline | `L2` + `Sub-pipeline Trigger / Parent Summary` |

## 2. `HandoffStatus`

`HandoffStatus` 只使用三种状态：

- `Draft`
- `Frozen`
- `Blocked`

`HandoffStatus` 不等于 `ArtifactState`。  
`ArtifactState` 是运行状态，定义见 `config/pipeline_protocol.md` 与 `architecture/artifact-state-machine.md`。

### `L0` 快速路径

`L0` 不生成模块级 Handoff，也不使用 `HandoffStatus`。进入 Step 3 前，Step 1 必须明确记录：

- `Handoff Level Decision = L0`
- `No-Handoff Rationale`：说明为何满足单模块 / 单 agent / 无跨模块依赖
- `Freeze Recommendation`：说明当前走 L0 快速路径而非 Handoff Freeze

若 Step 3 中出现跨模块 `Requires / Provides`、新增并行执行需求，或需要 `UserDecision` 才能继续，则必须停止 L0 快速路径，回到 Step 1 / Step 2 升级为 `L1+`。

## 3. Handoff 结构要求

`L1` / `L2` / `L3` 仍使用既有结构表达 `Owns / Provides / Requires / Blocks / Constraints / Done Criteria` 等信息，但这些结构主要承担交接内容与人类审阅职责，不单独构成 gate 真相。

- gate 判断以 `HandoffStatus`、Freeze Gate 与 runtime state 为准
- 模板、写法示例与章节布局应下沉到 `EXAMPLES.md` / `examples/*`
- 本页只保留进入 Step 3 / Step 4 / Step 5 所必需的控制语义

## 4. Freeze Gate

`L0` 快速路径进入 Step 3 前，必须满足：

- Step 1 已明确 `Handoff Level Decision = L0`
- `No-Handoff Rationale` 已说明单模块 / 单 agent / 无跨模块依赖
- Step 1 不得出现跨模块 `Requires / Provides`
- 若 Step 1 计划新增文件 / 类型 / 字段 / API：对应 `ArtifactBinding` 已完成
- Step 1 路线决策已收敛；若曾存在可复用候选与路线分歧，则 `PendingDecision` 已结束且 `UserDecision` 已解决
- `PCB.SHADOW_BANS` 与 `PCB.CONFIG_SYNTHESIS` 已就绪

`L1` / `L2` / `L3` 进入 Step 3 前，Handoff 必须满足：

- `HandoffStatus = Frozen`
- `Owns` 不重叠
- `Provides` 明确到 API / 数据 / 事件
- `Requires` 有候选 Provider，或明确标记 `unknown`
- `Blocks` 已分类
- 若 Step 1 计划新增文件 / 类型 / 字段 / API：对应 `ArtifactBinding` 已完成
- Step 1 路线决策已收敛；若曾存在可复用候选与路线分歧，则 `PendingDecision` 已结束且 `UserDecision` 已解决

`L2` / `L3` 额外要求：

- `Constraints` 已绑定
- `Done Criteria` 可验证

## 5. Handoff Update

Step 3 完成后，每个模块必须回写：

```md
## Handoff Update: {ModuleName}

### Implemented Provides
- 已兑现的 Provides

### Added Requires
- 实现中新增的依赖；没有则写 `None`

### Remaining Blocks
- 仍存在的阻塞；没有则写 `None`

### TODO
- 规范 TODO；没有则写 `None`

### Evidence
- 修改文件
- 参考 API
- 已验证 API
```

新增 `Requires` / `Blocks` 只能通过 Handoff Update 暴露。

## 6. Dependency Closure Report

Step 4 的统一输出结构：

```md
## Dependency Closure Report

### Closed

### SignatureMismatch

### MissingProvider

### BoundaryViolation

### CompletableBlocks

### BlockingBlocks

### ImplicitRequires
```

Step 4 只输出 closure，不做最终 verdict。

## 7. Done Criteria Coverage

Step 5 的统一输入结构：

```md
## Done Criteria Coverage

### {ModuleName}
- [x] 已覆盖的业务条件
- [ ] 未覆盖的业务条件
```

若当前模块只有 `L1` Handoff 且没有显式 `Done Criteria`，则在进入 Step 5 前，主 agent 必须基于 Step 1 的功能拆分、API 声明、必要时的 `ArtifactBinding` 与 Freeze Recommendation 先合成最小 coverage 输入；禁止让空白 coverage 直接进入 verdict。

Step 5 的最小输出结构：

```md
## VERIFICATION_REPORT

### Module Verdicts
- {ModuleName}: GO / GO-WITH-CAUTION / NO-GO

### Global Verdict
- GO / GO-WITH-CAUTION / NO-GO

### Reasons
- 证据 1
- 证据 2

### NextAction
- Step 6 / Step 9 / Recovery
```

最终 verdict 由 `pipeline-verify-agent` 给出。

## 8. Step 6 Re-closure

当 Step 5 = `GO-WITH-CAUTION`：

- Step 6 只补 `CompletableBlocks`
- 补完后至少重跑 Step 4
- 若 Step 4 输出变化影响 coverage 或 verdict，必须重跑 Step 5
- 首次 `GO-WITH-CAUTION` 的 result signal 必须写成 `finalized=false`；完成重跑后再由最终 Step 5 写 `finalized=true`
- Step 6 不得直接把 `GO-WITH-CAUTION` 改为 `GO`

## 9. `Parent Summary`

`Parent Summary` 只用于子 pipeline 回传父 pipeline：

```md
### Parent Summary
- Provides 已兑现：
- Requires 已闭合：
- Remaining Blocks：
- Module Verdict：GO / GO-WITH-CAUTION / NO-GO
```

它与 Step 3 模块输出里的 `PIPELINE_SUMMARY` 不是同一机制：

- `PIPELINE_SUMMARY`：模块实现归并
- `Parent Summary`：子 pipeline 对父 pipeline 的回传
