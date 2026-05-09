# Complex System Mode

> 本页只给人导航，不作为 AI 运行期规则源。

## 什么时候进入复杂系统模式

满足任一条件时，考虑进入复杂系统模式：

- 3+ 模块协作
- 共享事件、状态、权限或跨模块 contract
- 需要 wave、局部放行或子 pipeline
- 长时间 churn，主流程不能只等一个大任务结束

## 主定义页

| 主题 | 主定义页 |
|---|---|
| 总模型 | `orchestration-model.md` |
| `ArtifactState` | `artifact-state-machine.md` |
| barrier / wave / dispatch | `barrier-and-wave-scheduling.md` |
| 子 pipeline | `subpipeline-strategy.md` |
| stalled / heartbeat / checkpoint / recovery | `stall-recovery.md` |
| 局部 / 全局验证 | `verification-architecture.md` |

## 建议阅读顺序

- 想先建立心智模型：`orchestration-model.md`
- 想判断能不能放行：`artifact-state-machine.md` -> `barrier-and-wave-scheduling.md`
- 想判断是否拆子 pipeline：`subpipeline-strategy.md`
- 想排查长时间 churn：`stall-recovery.md`
- 想判断局部重跑还是全局重跑：`verification-architecture.md`

## 与其他层的边界

- 执行期控制真源：`../config/pipeline_protocol.md`
- Handoff 真源：`../config/handoff_protocol.md`
- 最小模板与判例：`../EXAMPLES.md` 与 `../examples/*`
