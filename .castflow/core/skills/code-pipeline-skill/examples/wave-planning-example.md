# Wave Planning 示例

## 场景

共享底座只有两项真正决定下游模块能否开工：

- 权限协议
- 事件协议

## `Artifact State Table` 快照

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| MI_AUTH | SharedCore | Frozen | - | SharedBarrier | CP-01 |
| MI_EVENT | SharedCore | Frozen | - | SharedBarrier | CP-01 |
| M1 | Leaf | Frozen | MI_AUTH,MI_EVENT | LocalBarrier | CP-02 |
| M2 | Leaf | Frozen | MI_AUTH,MI_EVENT | LocalBarrier | CP-02 |
| M4 | Leaf | Frozen | MI_AUTH,MI_EVENT | LocalBarrier | CP-02 |
| M6 | DomainComplex | Exploring | MI_AUTH,MI_EVENT,M4 | LocalBarrier | CP-02 |
| M8 | DomainComplex | NeedsSubpipeline | MI_EVENT,M4,M5 | LocalBarrier | CP-02 |
| M12 | Leaf | Frozen | MI_EVENT | LocalBarrier | CP-02 |

## `Wave Plan`

| Wave | EntryCondition | IncludedModules | DeferredModules | ExitArtifact |
|---|---|---|---|---|
| Wave 1 | Step 1 建模完成 | MI_AUTH, MI_EVENT | M1, M2, M4, M6, M8, M12 | SharedBarrier Ready |
| Wave 2 | SharedBarrier Ready | M1, M2, M4, M12 | M6, M8 | Wave 2 Outputs Ready |
| Wave 3 | Wave 2 Outputs Ready | M6, M8 | - | Local Closure / Parent Summary |
| Wave 4 | 各波次结果已回写 | Global Step 4 / Step 5 | - | Global Verdict |

## `Wave Dispatch Table`

| Wave | Module | ArtifactState | Barrier | DispatchTarget | Inputs | ExpectedOutput | Fallback |
|---|---|---|---|---|---|---|---|
| Wave 2 | M1 | Frozen | SharedBarrier=Ready, LocalBarrier=Ready | programmer-m1-agent | Frozen Handoff, PCB, MI_AUTH, MI_EVENT | temp/pipeline-output/M1.md | main agent |
| Wave 2 | M2 | Frozen | SharedBarrier=Ready, LocalBarrier=Ready | programmer-m2-agent | Frozen Handoff, PCB, MI_AUTH, MI_EVENT | temp/pipeline-output/M2.md | main agent |
| Wave 2 | M4 | Frozen | SharedBarrier=Ready, LocalBarrier=Ready | programmer-m4-agent | Frozen Handoff, PCB, MI_AUTH, MI_EVENT | temp/pipeline-output/M4.md | main agent |
| Wave 2 | M12 | Frozen | SharedBarrier=Ready, LocalBarrier=Ready | main agent | Frozen Handoff, PCB, MI_EVENT | temp/pipeline-output/M12.md | hold |
| Wave 3 | M8 | NeedsSubpipeline | LocalBarrier=Blocked | sub-pipeline | Parent Scope, Shared Core, Parent Summary 模板 | Parent Summary | hold |

## 这个例子说明了什么

- `Wave Plan` 是编排意图，不等于实际派发
- 真正进入 Step 3 前，必须再生成 `Wave Dispatch Table`
- `Frozen` 且 barrier 就绪的模块进入普通模块配对派发
- `NeedsSubpipeline` 可以保留在 `Wave Dispatch Table`，但只能写成显式 `sub-pipeline` 派发行
- fallback 必须写成显式决策
