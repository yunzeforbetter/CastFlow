# Artifact State Machine

`ArtifactState` 的主定义页。

## 状态集合

```text
Unmodeled
  ↓
Exploring
  ↓
Frozen
  ↓
Implementing
  ↓
LocallyVerified
  ↓
Integrated
  ↓
Accepted
```

异常状态：

- `Blocked`
- `NeedsSubpipeline`
- `Stalled`

## 状态含义

| `ArtifactState` | 含义 |
|---|---|
| `Unmodeled` | 还没有形成模块边界 |
| `Exploring` | 正在建模、拆分、识别依赖 |
| `Frozen` | 已具备可执行边界 |
| `Implementing` | 已进入 Step 3 / Step 6 |
| `LocallyVerified` | 已完成局部 closure / coverage |
| `Integrated` | 已完成更大范围对齐 |
| `Accepted` | 已被全局 verdict 接受 |
| `Blocked` | 存在 blocker，不能继续推进 |
| `NeedsSubpipeline` | 不应继续按单模块推进 |
| `Stalled` | 长时间 churn，必须先 recovery |

## `Frozen` 的最低要求

模块进入 `Frozen` 前，至少满足：

- `HandoffStatus = Frozen`
- `Owns / Provides / Requires` 已清晰
- 所需 barrier 已满足
- 不存在未决 `UserDecision`

## `Artifact State Table`

字段以 `config/pipeline_protocol.md` 为准。复杂系统模式下至少维护：

| 字段 | 含义 |
|---|---|
| Module | 模块或子域 |
| Type | `SharedCore` / `Leaf` / `DomainComplex` / `SubPipeline` |
| ArtifactState | 当前状态 |
| DependsOn | 关键依赖 |
| CurrentBarrier | 当前 barrier |
| LastCheckpoint | 最近一次 checkpoint |

## 状态到派发资格的映射

| `ArtifactState` | 是否可进入 `Wave Dispatch Table` | 默认动作 |
|---|---|---|
| `Unmodeled` | 否 | 继续建模 |
| `Exploring` | 否 | 继续冻结或拆分 |
| `Frozen` | 是 | 进入 dispatch 候选 |
| `Implementing` | 否 | 等待实现结果 |
| `LocallyVerified` | 否 | 等待汇入更大范围验证 |
| `Integrated` | 否 | 等待最终 verdict |
| `Accepted` | 否 | 等待收尾 |
| `Blocked` | 否 | 先解除 blocker |
| `NeedsSubpipeline` | 是（仅 `sub-pipeline` 派发） | 生成 checkpoint 后转子 pipeline |
| `Stalled` | 否 | 先 recovery |

## 状态跃迁约束

- `Exploring -> Frozen`：必须有清晰 Handoff 与约束对齐
- `Frozen -> Implementing`：必须满足 barrier 并写入 dispatch
- `Implementing -> LocallyVerified`：必须有 closure / coverage 证据
- `Stalled`：不能停留不处理，必须进入 `stall-recovery.md`
