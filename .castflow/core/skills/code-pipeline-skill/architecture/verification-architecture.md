# Verification Architecture

局部 / 全局验证与重跑粒度的主定义页。

## 局部验证

### Local Closure

由 `integration-matching-agent` 在局部范围内检查：

- Requires 是否有对应 Provides
- 是否存在 `SignatureMismatch`
- 是否越出 `Owns`
- 是否存在 `ImplicitRequires`

### Local Coverage

由 `pipeline-verify-agent` 在局部范围内检查：

- 当前模块或子 pipeline 的 `Done Criteria` 是否覆盖
- 剩余问题是否属于可补全 caution
- 当前模块的局部 verdict 是什么

## 全局验证

### Global Closure

主流程在 Step 4 汇总：

- 各模块 / 各子 pipeline 的 Requires / Provides
- 跨 wave 依赖是否闭合
- 是否仍有 blocker

### Global Verdict

主流程在 Step 5 汇总：

- 所有局部 verdict
- 全局 `Done Criteria` 是否覆盖
- 最终 verdict 是否为 `GO / GO-WITH-CAUTION / NO-GO`

## 验证结果回写

| 结果 | 状态更新 | 调度影响 |
|---|---|---|
| Local GO | `Implementing -> LocallyVerified` | 等待汇入更大范围验证 |
| Local GO-WITH-CAUTION | 保持 `LocallyVerified` | 进入补全 wave 或局部重跑 |
| Local NO-GO | `Blocked` 或 `NeedsSubpipeline` | 从当前 dispatch 移出 |
| Global GO | `Accepted` | 进入 Step 9 |
| Global GO-WITH-CAUTION（intermediate） | 保持 `pending-pipeline` | 进入 Step 6 并重跑 Step 4 / Step 5 |
| Global GO-WITH-CAUTION（final） | `Accepted` | 进入 Step 9 |
| Global NO-GO | `Blocked` | 回到 recovery / re-dispatch |

## 局部重跑与全局重跑

### 只重跑局部验证

- 只修改某一模块内部实现
- 未影响共享 contract
- `Parent Summary` 未出现 breaking 变化

### 必须升级为全局重跑

- 修改了 Shared Core
- 修改了公共事件、权限、DTO contract
- closure 变化影响其它模块的 Requires / Provides
- 子 pipeline 回传的 `Parent Summary` 发生 breaking 变化

## 与其它主定义页的关系

- closure / coverage 模板：`config/handoff_protocol.md`
- 状态定义：`artifact-state-machine.md`
- wave / dispatch：`barrier-and-wave-scheduling.md`
