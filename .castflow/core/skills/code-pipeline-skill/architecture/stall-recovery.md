# Stall Recovery

stalled、heartbeat、checkpoint 与 recovery 的主定义页。

## Heartbeat

长任务应周期性输出 heartbeat，至少包含：

- 当前 scope
- 当前 `ArtifactState`
- 已新增的 artifact
- 当前阻塞的 artifact
- 建议下一动作

`heartbeat` 是短状态反馈，不代替正式记录。

## Timebox

以下任务建议设置 timebox：

- 大型 Step 2 冻结
- 复杂域设计探索
- 多轮仍不收敛的 contract 对齐

timebox 到点后，必须写一条 `Checkpoint Record`。

## 判定为 `Stalled` 的信号

满足任一信号时，视为 stalled 风险；持续出现时升级为 `Stalled`：

- 长时间没有新的 checkpoint 或 artifact 更新
- 同一模块反复重写，但 barrier 状态不变
- token / 时间持续消耗，但没有新的 `Frozen` artifact
- 主流程只能说“继续等待”，却说不清当前卡在哪个 artifact
- 模块多次从 dispatch 中被推迟，原因没有收敛

## Recovery 动作

| 现象 | 恢复动作 |
|---|---|
| Shared Core 未冻结，导致大量模块一起等待 | 缩小冻结范围，只保留 Shared Core |
| 模块已 `Frozen`，但长期未进入实现 | 进入下一版 `Wave Dispatch Table` |
| 某复杂域长期 `Exploring` | 升级为 `sub-pipeline` |
| dispatch 目标反复变化 | 改为实例化共享模板或 `main agent` fallback |
| 局部验证已足够，但主流程仍全局等待 | 先做局部 closure / coverage |

## 恢复后的强制回写

执行 recovery 后，至少更新：

- `Artifact State Table`
- `Checkpoint Record`
- `Wave Dispatch Table`

## 用户可见反馈

反馈必须回答：

- 卡在哪个模块或 artifact
- 当前在等什么，不是在等谁
- 下一动作是什么
