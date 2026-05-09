# 复杂系统模式入口示例

## 进入信号

- 3+ 模块
- 存在共享事件、状态、权限 contract
- 某些模块仍可能继续拆分
- 需要 wave 或子 pipeline

## 初始拆分

### Shared Core

- MI_AUTH
- MI_EVENT

### Leaf Modules

- M1
- M2
- M3
- M4
- M5
- M7
- M12

### Domain Complex

- M6
- M8

## 初版 `Artifact State Table`

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| MI_AUTH | SharedCore | Exploring | - | SharedBarrier | CP-01 |
| MI_EVENT | SharedCore | Exploring | - | SharedBarrier | CP-01 |
| M1 | Leaf | Unmodeled | MI_AUTH,MI_EVENT | LocalBarrier | CP-01 |
| M6 | DomainComplex | Exploring | MI_AUTH,MI_EVENT,M4,M5 | LocalBarrier | CP-01 |
| M8 | DomainComplex | Exploring | MI_EVENT,M4,M5 | LocalBarrier | CP-01 |

## 初版 `Wave Plan`

| Wave | EntryCondition | IncludedModules | DeferredModules | ExitArtifact |
|---|---|---|---|---|
| Wave 1 | Step 1 建模完成 | MI_AUTH, MI_EVENT | M1, M2, M3, M4, M5, M6, M7, M8, M12 | SharedBarrier Ready |
| Wave 2 | SharedBarrier Ready | M1, M2, M3, M4, M5, M7, M12 | M6, M8 | Wave 2 Outputs Ready |
| Wave 3 | Wave 2 Outputs Ready | M6, M8 | - | Local Closure / Parent Summary |

## 初版 `Checkpoint Record`

### CP-01

- Scope: Alliance System
- ArtifactState: Exploring
- NewArtifacts: SharedCore / Leaf / DomainComplex 分类完成
- BlockingArtifact: Shared Event Contract not Frozen
- TimeboxUntil: next freeze review
- NextAction: 冻结 Shared Core，再生成首版 `Wave Dispatch Table`
- RecoveryAction: M8 -> sub-pipeline
