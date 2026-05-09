# Stall Recovery 示例

## Heartbeat

一次合格的 heartbeat 至少说明：

- Scope: MI_EVENT / M8
- ArtifactState: `Exploring`
- NewArtifacts: `MI_AUTH` 已接近冻结
- BlockingArtifact: Shared Event Contract not Frozen
- NextAction: 缩小冻结范围，优先收敛 Shared Core

## `Checkpoint Record`

### CP-03

- Scope: MI_EVENT, M8
- ArtifactState: `Exploring`
- NewArtifacts: MI_AUTH Frozen Draft
- BlockingArtifact: Shared Event Contract not Frozen
- TimeboxUntil: next recovery review
- NextAction: 只保留 Shared Core 冻结范围
- RecoveryAction: M8 -> sub-pipeline，Leaf 模块 -> Wave 2

## 恢复后的 `Artifact State Table`

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| MI_AUTH | SharedCore | Frozen | - | SharedBarrier | CP-03 |
| MI_EVENT | SharedCore | Frozen | - | SharedBarrier | CP-03 |
| M1 | Leaf | Frozen | MI_AUTH,MI_EVENT | LocalBarrier | CP-03 |
| M2 | Leaf | Frozen | MI_AUTH,MI_EVENT | LocalBarrier | CP-03 |
| M6 | DomainComplex | Exploring | M4,M5 | LocalBarrier | CP-03 |
| M8 | DomainComplex | NeedsSubpipeline | MI_EVENT,M4,M5 | LocalBarrier | CP-03 |

## 恢复后的 `Wave Dispatch Table`

| Wave | Module | ArtifactState | Barrier | DispatchTarget | Inputs | ExpectedOutput | Fallback |
|---|---|---|---|---|---|---|---|
| Wave 2 | M1 | Frozen | SharedBarrier=Ready, LocalBarrier=Ready | programmer-m1-agent | Frozen Handoff, PCB, Shared Core | temp/pipeline-output/M1.md | main agent |
| Wave 2 | M2 | Frozen | SharedBarrier=Ready, LocalBarrier=Ready | programmer-m2-agent | Frozen Handoff, PCB, Shared Core | temp/pipeline-output/M2.md | main agent |
| Wave 3 | M8 | NeedsSubpipeline | LocalBarrier=Blocked | sub-pipeline | Parent Scope, Shared Core, Parent Summary 模板 | Parent Summary | hold |

## 用户可见反馈

优先反馈：

“Shared Core 已收敛，M8 仍处于 `Exploring`。主流程先放行 Wave 2，并把 M8 升级为子 pipeline。”
