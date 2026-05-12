# traces/ - 配置与字段说明

本目录由 hook 脚本读写。包含 4 类内容：

| 类别 | 文件 | 说明 |
|------|------|------|
| 配置 | `config/limits.json` | trace-flush 的压缩/通知/过期阈值（运行时可改，无需重启） |
| 配置 | `config/hooks.config.json` | trace-collector 与 trace-flush 的语言/路径推断配置（适配非 Unity 项目） |
| 数据 | `trace.md` | hook 自动累积的执行记录，由 origin-evolve 消费 |
| 数据 | `weights.json` | 八维评分权重的自校准结果（首次使用前不存在，由 origin-evolve Step 6 写入） |
| 状态 | `.trace_buffer` / `.trace_prev_edits` / `.trace_lock` / `.pending_*.json` / `.trace_error.log` | hook 内部状态文件，不要手动编辑 |

修改 `config/limits.json` 或 `config/hooks.config.json` 后立即生效。

---

## trace.md 字段契约

每条 TRACE 块由 hook 写入，origin-evolve 读取。

### 块头

```
<!-- TRACE status:<status> schema:<N> -->
```

| 字段 | 取值 | 写入方 |
|------|------|--------|
| `status` | `pending` / `processed` / `expired` / `invalid` | hook 写 `pending`，origin-evolve 改其他状态 |
| `schema` | 整数版本号（当前 2） | hook 写入。origin-evolve Step 1 校验：未知版本则中止并提示升级 |

### 块体字段

| 字段 | 写入方 | 含义 |
|------|--------|------|
| `timestamp` | hook | trace 写入时刻（ISO8601 UTC） |
| `mode` | AI（IDP） | 执行模式：`standard` / `emergency` / `high-accuracy` / `rework` / `user-rule` |
| `type` | AI（IDP） | 任务类型：`feature` / `bugfix` / `refactor` / `optimization` / `config` |
| `modules` | hook | 从文件路径推断的模块名 |
| `skills` | AI（IDP） | 本次涉及的 skill 名称 |
| `score` | hook | 八维评分结果 |
| `score_breakdown` | hook | 各维度得分明细（如 `F=0.33 K=0.9 R=2.5`） |
| `correction` | hook | 自我修正信号：`_` / `auto:minor` / `auto:major` |
| `validated` | hook | 用户验证信号：`_` / `true` / `false` / `pending-pipeline` / `invalid` |
| `pipeline_run_id` | hook | code-pipeline 运行标记（可选） |
| `error_cause` | AI（IDP） | 错误根因（rework/user-rule/correction 场景） |
| `fix_approach` | AI（IDP） | 最终修复方案 |
| `user_feedback` | AI（IDP） | 用户关键反馈原话 |
| `lesson` | AI（IDP） | 可复用的经验总结 |

### 示例

```
<!-- TRACE status:pending schema:2 -->
timestamp: 2026-05-12T12:58:55Z
mode: rework
type: bugfix
modules: [Building]
skills: [programmer-ui-skill]
score: 4.84
score_breakdown: F=0.33 D=0.25 S=0.08 E=0.48 C=1.2 R=2.5
correction: auto:minor
validated: _
pipeline_run_id: _
error_cause: ObservableList.Add always appends, used it for ordered insert
fix_approach: Changed to Insert(index, item) with bounds check
user_feedback: 不行，列表顺序不对，必须插入到指定位置
lesson: ObservableList ordered insert must use Insert(index) not Add()
<!-- /TRACE -->
```

---

## 八维评分模型（v3）

```
score = F·1.0 + D·0.5 + K·1.5 + S·0.5 + E·0.8 + C·2.0 + R·2.5 + U·2.0
```

| 维度 | 含义 | 计算 | 权重 |
|------|------|------|------|
| F | 文件数 | `min(files/3, 1.0)` | 1.0 |
| D | 模块分散度 | `min(modules/2, 1.0)` | 0.5 |
| K | 关键路径 | Interface=1.0 / Impl=0.6 / Base=0.3 | 1.5 |
| S | 改动规模 | `min(lines/50, 1.0)` | 0.5 |
| E | 编辑密度 | `min(edits/5, 1.0)` | 0.8 |
| C | 自我修正 | revert≥3→1.0, ≥1→0.6 | 2.0 |
| R | 用户返工 | mode=rework→1.0, flag→0.8 | 2.5 |
| U | 用户规则 | mode=user-rule→1.0, flag→0.8 | 2.0 |


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
| `level2_age_days` | 14 | Level 2 淘汰的最低龄 |
| `level2_score_threshold` | 1.0 | Level 2 淘汰的最高分 |
| `level3_age_days` | 7 | Level 3 候选的最低龄 |
| `level3_score_threshold` | 0.5 | Level 3 候选的最高分 |
| `keep_top_n_per_module` | 3 | Level 3 每模块至少保留 N 条 |
| `passive_trigger_threshold` | 10 | pending 条目达到此值允许通知 |
| `passive_trigger_min_new` | 5 | 距上次通知后新增数达到此值才通知 |
| `pipeline_pending_expire_days` | 7 | pending-pipeline 超时标记 invalid |
| `validated_uncertain_expire_days` | 14 | validated:_ 超时标记 expired |
| `processed_expire_days` | 30 | PROCESSED 审计行过期清理 |

---

## hooks.config.json 字段说明

| 字段 | 作用 | 何时修改 |
|------|------|---------|
| `tracked_extensions` | collector 关注的源代码扩展名 | 项目使用清单外的语言 |
| `excluded_extensions` | 强制排除的扩展名 | 有特殊二进制文件被误判 |
| `generic_dir_segments` | 推断模块时跳过的通用目录名 | 顶层目录与默认值不同 |
| `module_dir_pattern` | 提取模块名的正则（group 1） | 模块组织约定不同 |

**适配示例**：

Go monorepo：
```json
{
  "tracked_extensions": [".go"],
  "generic_dir_segments": ["cmd", "pkg", "internal", "vendor"],
  "module_dir_pattern": "(?:internal|pkg)/([^/]+)"
}
```

React/TypeScript：
```json
{
  "tracked_extensions": [".ts", ".tsx", ".js", ".jsx"],
  "excluded_extensions": [".d.ts"],
  "generic_dir_segments": ["src", "app", "components", "hooks"],
  "module_dir_pattern": "features/([^/]+)"
}
```
