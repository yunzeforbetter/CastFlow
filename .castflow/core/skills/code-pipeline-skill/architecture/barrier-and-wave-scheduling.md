# Barrier and Wave Scheduling

barrier、wave 与 dispatch 的主定义页。

## Barrier

### `SharedBarrier`

用于共享底座：

- 权限入口
- 事件协议
- 公共 DTO / key / ID
- 跨模块 contract

### `LocalBarrier`

用于模块自身前置依赖。  
模块只要自己的 `LocalBarrier` 已满足，就可以进入当前 wave。

### `GlobalBarrier`

只用于全局集成门：

- Step 4 的全局 closure
- Step 5 的全局 verdict
- Step 9 的收尾

## Wave

`Wave Plan` 负责回答：

- 这一波计划放谁
- 这一波暂缓谁
- 这一波完成后必须出现什么产物

字段与模板以 `config/pipeline_protocol.md` 为准。

## Dispatch

`Wave Dispatch Table` 负责回答：

- 哪个模块现在真的被放行
- 放行目标是谁
- 失败时退回哪里

字段与模板以 `config/pipeline_protocol.md` 为准。

## Dispatch 决策顺序

1. 检查 `ArtifactState` 是否仍为 `Frozen`
2. 检查对应 `SharedBarrier / LocalBarrier` 是否已满足
3. 检查 `HandoffStatus` 是否仍为 `Frozen`
4. 解析 `DispatchTarget`
5. 把最终决定写入 `Wave Dispatch Table`

## 放行约束

- `Frozen` 且 barrier 就绪，才允许进入普通模块派发
- `NeedsSubpipeline` 只能写成显式 `DispatchTarget = sub-pipeline` 的派发行
- `Stalled / Blocked` 先 recovery，不进入普通派发
- `DispatchTarget` 必须按职责名称表达，不把路径当成运行机制

## Fallback 规则

- 缺少可用模块配对执行单元：显式改为“实例化共享模板”或 `main agent`
- barrier 失效：从 dispatch 队列移出，回到 `Wave Plan` 的 deferred 集合
- 模块转入 `NeedsSubpipeline`：从普通派发移出
- 模块进入 `Stalled / Blocked`：先写 checkpoint，再 recovery

## 与其它主定义页的关系

- 状态来源：`artifact-state-machine.md`
- stalled 与 recovery：`stall-recovery.md`
- 子 pipeline：`subpipeline-strategy.md`
- 局部 / 全局重跑：`verification-architecture.md`
