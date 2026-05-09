# Orchestration Model

复杂系统模式下，主流程按以下三件事推进：

- `ArtifactState`
- barrier readiness
- wave readiness

主流程不再只看“某个 Step 是否全部结束”。

## 三层模型

### Macro Pipeline

主 pipeline 负责：

- 系统拆分
- 识别 `SharedCore / Leaf / DomainComplex`
- 冻结共享底座
- 规划 wave
- 决定 `DispatchTarget`
- 决定是否升级子 pipeline
- 汇总局部验证并给出全局 verdict

### Domain Pipeline

子 pipeline 负责：

- 某个复杂域内部的建模、冻结、实现、局部验证
- 只向父 pipeline 回传 `Parent Summary`

### Worker Agents

执行单元负责：

- `requirement-analysis-agent`：建模、声明、冻结建议
- 模块配对执行单元：按 `module_id` 匹配 agent + skill，并在已冻结边界内实现
- `integration-matching-agent`：closure
- `pipeline-verify-agent`：coverage 与 verdict
- `debug-skill`：边界条件与失败路径验证
- `profiler-skill`：性能诊断
- `main agent`：Step 9 终结与清理

## 核心放行规则

模块可以进入当前 Step 3 / Step 6，当且仅当：

- `ArtifactState = Frozen`
- 对应 barrier 已满足
- `HandoffStatus = Frozen`
- 当前 dispatch 已写入 `Wave Dispatch Table`

## 主流程只回答三个问题

1. 什么先冻结  
2. 什么现在可放行  
3. 什么该升级成子 pipeline

## 主题路由

| 你要判断什么 | 去哪里看 |
|---|---|
| 状态是否可推进 | `artifact-state-machine.md` |
| 当前是否可进入某 wave | `barrier-and-wave-scheduling.md` |
| 是否要拆子 pipeline | `subpipeline-strategy.md` |
| 是否已 stalled，下一步怎么恢复 | `stall-recovery.md` |
| 是局部重跑还是全局重跑 | `verification-architecture.md` |
