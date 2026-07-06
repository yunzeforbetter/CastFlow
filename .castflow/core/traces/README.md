# traces/ - 配置与字段说明

本目录由 hook 脚本读写。trace 现在是**纯 memory 快照账本**（schema:4）——评分/buffer/IDP 子系统已退役，trace 只记录本会话模型写了哪些 auto-memory。

| 类别 | 文件 | 说明 |
|------|------|------|
| 配置 | `config/limits.json` | trace-flush 的压缩/通知/过期阈值（运行时可改，无需重启） |
| 配置 | `config/hooks.config.json` | trace-collector 的 memory 目录匹配正则（适配 autoMemoryDirectory 重定向） |
| 数据 | `trace.md` | hook 自动累积的 memory 快照账本，由 origin-evolve 消费 |
| 状态 | `.trace_memory_snapshots` / `.trace_lock` / `.pending_pipeline_result.json` / `.trace_error.log` | hook 内部状态文件，不要手动编辑 |

修改 `config/limits.json` 或 `config/hooks.config.json` 后立即生效。

---

## 机制概览

```
模型写 auto-memory (~/.claude/projects/<slug>/memory/*.md)
   │  PostToolUse: Write/Edit
   ▼
trace-collector: 命中 memory 路径 → 读全文 → type==user 排除 → 按 slug 留存 .trace_memory_snapshots
   │  Stop
   ▼
trace-flush: 有快照才写 trace.md（纯代码会话不产生条目）；快照以 <!-- MEMORY --> 子块嵌入
   │  git
   ▼
origin-evolve: 从 <!-- MEMORY --> 快照蒸馏出 skill 规则
```

**代码编辑不再采集。** 只有 `feedback`/`project`/`reference` 类型的 memory 被快照；`user` 类型（个人画像）被过滤，不进 git。

---

## trace.md 字段契约（schema:4）

每条 TRACE 块由 hook 写入，origin-evolve 读取。

### 块头

```
<!-- TRACE status:<status> schema:4 -->
```

| 字段 | 取值 | 写入方 |
|------|------|--------|
| `status` | `pending` / `processed` / `expired` / `invalid` | hook 写 `pending`，origin-evolve 改其他状态 |
| `schema` | 整数版本号（当前 4） | hook 写入。origin-evolve Step 1 校验：接受 1-4，未知版本则中止并提示升级 |

### 块体字段

| 字段 | 写入方 | 含义 |
|------|--------|------|
| `timestamp` | hook | trace 写入时刻（ISO8601 UTC） |
| `type` | hook | 快照主导类型（`feedback` > `project` > `reference`） |
| `validated` | hook | 用户/pipeline 验证信号：`_` / `true` / `false` / `pending-pipeline` / `invalid` |
| `pipeline_run_id` | hook | code-pipeline 运行标记（可选） |
| `memory_snapshots` | hook | 嵌入的 MEMORY 子块数量 |

### MEMORY 子块

每个快照嵌为一个子块，是 memory 文件的逐字副本（超 8KB 截断，标 `truncated:1`）：

```
<!-- MEMORY slug:<slug> type:<type> -->
description: <memory 的 description>
---
<memory 全文>
<!-- /MEMORY -->
```

### 示例

```
<!-- TRACE status:pending schema:4 -->
timestamp: 2026-07-03T13:00:00Z
type: feedback
validated: _
pipeline_run_id: _
memory_snapshots: 1
<!-- MEMORY slug:observablelist-ordered-insert type:feedback -->
description: ObservableList 有序插入必须用 Insert 不能用 Add
---
（memory 全文：规则 + Why + How to apply）
<!-- /MEMORY -->
<!-- /TRACE -->
```

> 旧 schema:1-3 条目可能仍携带已退役字段（`score`/`modules`/`correction`/`mode`/`lesson` 等）。origin-evolve 读到时不报错，但不依赖它们；这些条目会随 compaction 龄期自然淘汰。

---

## 复合组件 own 的 pending state

- `.pending_pipeline_result.json` 属于 `code-pipeline` own 的 runtime state
- 由 `trace-flush.py` 消费并回填 `validated` 字段
- `result=GO-WITH-CAUTION` + `finalized=false` → 保留 `pending-pipeline` 直到最终 verdict

---

## limits.json 字段说明

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `compact_max_entries` | 80 | trace 块总数超过此值触发压缩 |
| `compact_max_size_kb` | 100 | 文件大小超过此值触发压缩 |
| `level2_age_days` | 14 | Level 2 淘汰的最低龄（非经验资产的超龄骨架） |
| `level3_age_days` | 7 | Level 3 溢出淘汰的候选最低龄 |
| `keep_recent_n` | 20 | Level 3 溢出时始终保留最近 N 条 |
| `passive_trigger_threshold` | 10 | pending 条目达到此值允许通知 |
| `passive_trigger_min_new` | 5 | 距上次通知后新增数达到此值才通知 |
| `pipeline_pending_expire_days` | 7 | pending-pipeline 超时标记 invalid |
| `validated_uncertain_expire_days` | 14 | validated:_ 超时标记 expired |
| `processed_expire_days` | 30 | PROCESSED 审计行过期清理 |

**经验资产保护**：带 memory 快照或 `validated:true` 的条目在龄期压缩中**永不自动删除**，只有纯骨架条目会被淘汰。

---

## hooks.config.json 字段说明

| 字段 | 作用 | 何时修改 |
|------|------|---------|
| `memory_dir_pattern` | collector 识别 auto-memory 目录的正则 | `autoMemoryDirectory` 被重定向到非标准路径时 |

**默认值**匹配 Claude Code 原生 auto-memory 位置 `~/.claude/projects/<slug>/memory/`。绝大多数项目无需修改。
