# traces/ - 配置与字段说明

本目录由 hook 脚本读写。包含 4 类内容：

| 类别 | 文件 | 说明 |
|------|------|------|
| 配置 | `config/limits.json` | trace-flush 的压缩/通知/过期阈值（运行时可改，无需重启） |
| 配置 | `config/hooks.config.json` | trace-collector 与 trace-flush 的语言/路径推断配置（适配非 Unity 项目） |
| 数据 | `trace.md` | hook 自动累积的执行记录，由 origin-evolve 消费 |
| 数据 | `weights.json` | 五维评分权重的自校准结果（首次使用前不存在，由 origin-evolve Step 6 写入） |
| 状态 | `.trace_buffer` / `.trace_prev_edits` / `.trace_lock` / `.pending_*.json` / `.trace_error.log` | hook 内部状态文件，不要手动编辑 |

修改 `config/limits.json` 或 `config/hooks.config.json` 后立即生效。

---

## trace.md 字段契约

每条 TRACE 块由 hook 写入，origin-evolve 读取。两侧共用同一份字段定义。

### 块头

```
<!-- TRACE status:<status> schema:<N> -->
```

| 字段 | 取值 | 写入方 |
|------|------|--------|
| `status` | `pending` / `processed` / `expired` / `invalid` | hook 写 `pending`，origin-evolve 改其他状态 |
| `schema` | 整数版本号（当前 1） | hook 写入。origin-evolve Step 1 校验：未知版本则中止并提示升级 |

### 块体字段

| 字段 | 类型 | 写入方 | 含义 |
|------|------|--------|------|
| `timestamp` | ISO8601 UTC | hook | trace 写入时刻 |
| `mode` | `standard` / `emergency` / `high-accuracy` / `_` | AI（IDP）/ hook | 执行模式，由 IDP 注入或留空 |
| `type` | `feature` / `bugfix` / `refactor` / `optimization` / `config` / `_` | AI / hook | 任务类型 |
| `request` | string | AI（IDP）| 用户请求摘要 |
| `intent` | string | AI（IDP）| AI 理解的意图 |
| `correction` | `_` / `auto:minor` / `auto:major` / `minor` / `major` | hook | 自我修正信号，由 collector 自动检测或 AI 标记 |
| `validated` | `_` / `true` / `false` / `pending-pipeline` / `invalid` | hook | 用户验证信号，从 `.pending_validated.json` 注入 |
| `pipeline_run_id` | string / `_` | hook | code_pipeline 的 run id |
| `modules` | `[Mod1, Mod2]` | hook | 从文件路径推断（依赖 config/hooks.config.json） |
| `skills` | `[skill1]` / `[]` | AI（IDP）| 本次涉及的 skill 名称 |
| `files_modified` | `[path, ...]` | hook | 编辑过的文件（最多前 20 个） |
| `file_count` | int | hook | 文件总数 |
| `lines_changed` | int | hook | 累计变更行数（估算） |
| `edit_count` | int | hook | 编辑事件总次数 |
| `score` | float | hook | 五维评分结果，>= 阈值才会写入此 trace |

**真理来源**：字段格式由 `trace-flush.py` 的 `format_trace()` 函数生成。修改字段时同步更新 `schema` 版本号，origin-evolve 会拒绝读取未知版本，避免静默漂移。

---

## limits.json 字段说明

控制 trace-flush 的压缩行为、过期策略和通知阈值。位于 `config/limits.json`。

### 压缩触发条件

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `compact_max_entries` | 80 | trace.md 中 TRACE 块总数超过此值时触发压缩。每次 AI 停止响应都会检查 |
| `compact_max_size_kb` | 100 | trace.md 文件大小（KB）超过此值时触发压缩。与 compact_max_entries 任一满足即触发 |

### Level 2 压缩（按龄淘汰低分条目）

Level 2 在 Level 1（清理 expired/invalid）之后执行，删除较老且分数较低的条目。

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `level2_age_days` | 14 | 条目 timestamp 距今超过此天数，才有资格被 Level 2 淘汰 |
| `level2_score_threshold` | 1.0 | 条目 score 低于此值才有资格被 Level 2 淘汰 |

两个条件**同时满足**（age > 14 天 AND score < 1.0）才删除。

### Level 3 压缩（超量时强制削减）

Level 2 后若条目数仍超过 compact_max_entries，Level 3 从最老、最低分的条目中强制削减至上限。

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `level3_age_days` | 7 | Level 3 候选条目的最低龄要求（天）。7 天内的新条目不参与强制削减 |
| `level3_score_threshold` | 0.5 | Level 3 候选条目的最高分限制 |

### 模块保留策略

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `keep_top_n_per_module` | 3 | Level 3 压缩时，每个模块至少保留 N 条最高分条目 |

### 被动触发通知

origin-evolve 的被动触发机制：当积累足够多的 pending trace 时，在 trace.md 中写入 NOTIFY 块提醒用户执行分析。

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `passive_trigger_threshold` | 10 | pending 条目总数达到此值时，允许发送通知 |
| `passive_trigger_min_new` | 5 | 距上次通知后新增的 pending 条目数必须达到此值才再次通知 |

示例：上次通知时有 10 条 pending，现在有 14 条，new=4 < min_new(5)，不通知。等到 15 条时 new=5，触发通知。

### 过期策略

| 字段 | 默认值 | 作用 |
|------|--------|------|
| `pipeline_pending_expire_days` | 7 | pipeline 执行中途放弃时，`validated:pending-pipeline` 条目超过此天数被标记 `invalid` |
| `validated_uncertain_expire_days` | 14 | `validated:_` 且 `status:pending` 的条目超过此天数被标记 `expired` |
| `processed_expire_days` | 30 | 已处理（PROCESSED 审计行）的条目此天数后可被 Level 1 清理 |

### 调参建议

- **项目活跃度高**（每天多次 AI 操作）：适当降低 `compact_max_entries`（如 60）和 `level2_age_days`（如 10），保持 trace.md 精简
- **项目活跃度低**（偶尔使用）：适当提高 `validated_uncertain_expire_days`（如 30），给用户更多时间反馈
- **pipeline 流程长**：适当提高 `pipeline_pending_expire_days`（如 14），防止长流程 trace 被过早标记为 invalid
- **不希望被频繁提醒**：提高 `passive_trigger_threshold`（如 20）和 `passive_trigger_min_new`（如 10）

---

## hooks.config.json 字段说明

控制 hook 脚本对**项目语言/路径结构**的适配。位于 `config/hooks.config.json`，文件本身有 inline `_comment_*` 注释，下表是补充说明。

| 字段 | 作用 | 何时需要修改 |
|------|------|------------|
| `tracked_extensions` | trace-collector 关注的源代码扩展名 | 项目使用清单外的语言时（如 Elixir `.ex`） |
| `excluded_extensions` | 即使匹配 tracked 也强制排除的扩展名 | 项目有特殊的二进制/资产文件被误判 |
| `generic_dir_segments` | 推断模块时跳过的"通用容器"目录名 | 项目顶层目录与默认值不同（如 Go 项目用 `pkg`/`internal`） |
| `module_dir_pattern` | 提取模块名的正则（group 1 = 模块名） | 项目模块组织约定不同（如 `features/<name>` 或 `packages/<name>/src`） |

**典型适配示例**：

Go monorepo 项目：

```json
{
  "tracked_extensions": [".go"],
  "excluded_extensions": [],
  "generic_dir_segments": ["cmd", "pkg", "internal", "vendor"],
  "module_dir_pattern": "(?:internal|pkg)/([^/]+)"
}
```

React/TypeScript 项目：

```json
{
  "tracked_extensions": [".ts", ".tsx", ".js", ".jsx"],
  "excluded_extensions": [".d.ts"],
  "generic_dir_segments": ["src", "app", "components", "hooks"],
  "module_dir_pattern": "features/([^/]+)"
}
```

任何字段缺失时，hook 自动回退到 Python 代码中的默认值（保证可降级运行）。
