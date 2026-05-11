# Runtime State Header

> `code-pipeline` 的最小运行态真相。它内嵌在 `PIPELINE_CONTEXT.md` 顶部固定状态头中，只承载 gate 判定所需的最小事实，不承载完整 Step 文本。

## 文件定位

- 真相载体：`PIPELINE_CONTEXT.md` 顶部固定状态头
- 作用范围：本次 pipeline 的唯一 gate 真相
- 生命周期：Step 1 创建；Step 9 清理或终结

## 推荐头部格式

```md
pipeline_run_id: pipeline_20260511_143055
pipeline_mode: standard
pipeline_current_step: 1
pipeline_lifecycle_state: Discovering
pipeline_decision_status: none
pipeline_decision_basis: unknown
pipeline_freeze_status: not_applicable
pipeline_active_modules: []
pipeline_last_closure_scope: none
pipeline_last_verdict: none
pipeline_result_signal_status: none
```

## 字段说明

| 字段 | 取值 | 含义 |
|---|---|---|
| `pipeline_run_id` | `pipeline_{YYYYMMDD}_{HHMMSS}` | 本次 pipeline 生命周期唯一标识 |
| `pipeline_mode` | `standard` / `complex` | 当前模式 |
| `pipeline_current_step` | `1`-`9` | 当前步骤 |
| `pipeline_lifecycle_state` | `Discovering` / `PendingDecision` / `Frozen` / `Implementing` / `Verifying` / `Finalized` / `Aborted` | 当前生命周期状态 |
| `pipeline_decision_status` | `none` / `required` / `resolved` | 路线决策状态 |
| `pipeline_decision_basis` | `reuse` / `new` / `unknown` | 当前路线依据 |
| `pipeline_freeze_status` | `not_applicable` / `required` / `frozen` / `blocked` | Freeze 状态 |
| `pipeline_active_modules` | JSON array string | 当前被放行或验证中的模块 |
| `pipeline_last_closure_scope` | `none` / `local` / `global` | 最近一次 Step 4 的闭合范围 |
| `pipeline_last_verdict` | `none` / `GO` / `GO-WITH-CAUTION` / `NO-GO` | 最近一次 Step 5 verdict |
| `pipeline_result_signal_status` | `none` / `pending` / `finalized` | 当前 result signal 状态 |

## 状态迁移约束

### Step 1
- 初始进入：`pipeline_lifecycle_state = Discovering`
- 若无可复用候选：`pipeline_decision_status = resolved`
- 若有可复用候选且存在路线分歧：`pipeline_decision_status = required`，`pipeline_lifecycle_state = PendingDecision`
- 用户完成 `UserDecision`：`pipeline_decision_status = resolved`

### Step 2
- 只有 `pipeline_decision_status = resolved` 时才允许进入
- 命中冻结条件后：`pipeline_freeze_status = required`
- Freeze 完成后：`pipeline_freeze_status = frozen`，`pipeline_lifecycle_state = Frozen`

### Step 3
- 只有 `pipeline_decision_status = resolved` 且 `pipeline_freeze_status ∈ {not_applicable, frozen}` 时才允许进入
- 进入实现：`pipeline_lifecycle_state = Implementing`

### Step 4 / Step 5
- 进入闭合与验收：`pipeline_lifecycle_state = Verifying`
- Step 4 回写 `pipeline_last_closure_scope`
- Step 5 回写 `pipeline_last_verdict` 与 `pipeline_result_signal_status`

### Step 9
- 成功收尾：`pipeline_lifecycle_state = Finalized`
- 中止放弃：`pipeline_lifecycle_state = Aborted`

## 使用原则

- dispatch、freeze、verdict 的判断优先读取 `PIPELINE_CONTEXT.md` 顶部状态头
- `PIPELINE_CONTEXT.md` 正文只同步结论，不反向充当 gate 真相
- `pipeline_merge.py` 只操作 Step 3 归并块，不修改顶部状态头
