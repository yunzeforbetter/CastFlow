# limits.json - 字段说明

`limits.json` 控制 trace-flush.py 的压缩行为、过期策略和通知阈值。修改后立即生效，无需重启。

---

## 压缩触发条件

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `compact_max_entries` | 80 | trace.md 中 TRACE 块总数超过此值时触发压缩。每次 AI 停止响应都会检查。 |
| `compact_max_size_kb` | 100 | trace.md 文件大小（KB）超过此值时触发压缩。与 compact_max_entries 任一满足即触发。 |

---

## Level 2 压缩（按龄淘汰低分条目）

Level 2 在 Level 1（清理 expired/invalid）之后执行，删除较老且分数较低的条目。

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `level2_age_days` | 14 | 条目 timestamp 距今超过此天数，才有资格被 Level 2 淘汰。保护近期条目不被误删。 |
| `level2_score_threshold` | 1.0 | 条目 score 低于此值才有资格被 Level 2 淘汰。高分条目（有价值的任务记录）不受影响。 |

两个条件同时满足（age > 14 天 AND score < 1.0）才删除。

---

## Level 3 压缩（超量时强制削减）

Level 2 后若条目数仍超过 compact_max_entries，Level 3 从最老、最低分的条目中强制削减至上限。

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `level3_age_days` | 7 | Level 3 候选条目的最低龄要求（天）。7 天内的新条目不参与强制削减。 |
| `level3_score_threshold` | 0.5 | Level 3 候选条目的最高分限制。score >= 0.5 的条目不参与强制削减，优先保留有意义的记录。 |

---

## 模块保留策略

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `keep_top_n_per_module` | 3 | Level 3 压缩时，每个模块至少保留 N 条最高分条目，防止低频模块的所有记录被全部清除。 |

---

## 被动触发通知

origin-evolve 的被动触发机制：当积累足够多的 pending trace 时，在 trace.md 中写入 NOTIFY 块提醒用户执行分析。

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `passive_trigger_threshold` | 10 | pending 条目总数达到此值时，允许发送通知。防止条目太少时频繁打扰用户。 |
| `passive_trigger_min_new` | 5 | 距上次通知后新增的 pending 条目数必须达到此值才再次通知。防止每次 Stop Hook 都重复通知。 |

示例：上次通知时有 10 条 pending，现在有 14 条，new=4 < min_new(5)，不通知。等到 15 条时 new=5，触发通知。

---

## 过期策略

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `pipeline_pending_expire_days` | 7 | pipeline 执行中途放弃（无 Step 5）时，`validated:pending-pipeline` 的条目在此天数后被 origin-evolve Step 0 标记为 `invalid`。防止废弃的 pipeline trace 永久占据分析队列。 |
| `validated_uncertain_expire_days` | 14 | `validated:_`（未收到用户接受/拒绝信号）且 `status:pending` 的条目在此天数后被 Step 0 标记为 `expired`。超过两周仍未验证的条目视为信号丢失，降优先级。 |
| `processed_expire_days` | 30 | origin-evolve 已处理（PROCESSED 审计行）的条目在此天数后可被 Level 1 压缩清理。保留一个月的处理历史供回溯，之后释放空间。 |

---

## 调参建议

- **项目活跃度高**（每天多次 AI 操作）：适当降低 `compact_max_entries`（如 60）和 `level2_age_days`（如 10），保持 trace.md 精简。
- **项目活跃度低**（偶尔使用）：适当提高 `validated_uncertain_expire_days`（如 30），给用户更多时间反馈。
- **pipeline 流程长**：适当提高 `pipeline_pending_expire_days`（如 14），防止长流程 trace 被过早标记为 invalid。
- **不希望被频繁提醒**：提高 `passive_trigger_threshold`（如 20）和 `passive_trigger_min_new`（如 10）。
