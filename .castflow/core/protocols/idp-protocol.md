# IDP Protocol - Intent Declaration Protocol

> **加载时点**：T2-EXECUTE 按需加载。仅当本次响应会写入 `.pending_idp.json` 时需要。完整时点定义见项目根 `CLAUDE.md`「使用Skill的分层加载」段。
> **关联**：`GLOBAL_SKILL_MEMORY.md` 协议 3（执行模式检测）决定 IDP 写入时机与模式选择。

---

## 协议定义

写代码前将意图声明写入 `.pending_idp.json`（位于 `.claude/traces/` 目录，覆盖写），供 trace-flush 注入 trace 语义字段。trace-flush 读取后无条件删除此文件。

## 写入格式

**标准格式**：

```json
{
  "mode": "standard",
  "request": "用户真实意图，一句话",
  "intent": "AI 的理解和实现计划",
  "scope": "涉及的文件或模块",
  "type": "feature",
  "skills": ["programmer-ui-skill"]
}
```

**紧急模式额外字段**：

```json
{
  "mode": "emergency",
  "retrospective": true,
  ...
}
```

## 字段取值

| 字段 | 取值 |
|------|------|
| `mode` | `standard` / `emergency` / `high-accuracy` |
| `type` | `feature` / `bugfix` / `refactor` / `optimization` / `config` |
| `request` | 用户原话或最贴近的转述（不能是 AI 的解读） |
| `intent` | AI 的实现计划（要做什么、怎么做） |
| `scope` | 涉及的文件路径或模块名 |
| `skills` | 本次使用的 Skill 名称数组 |

## 写入时机

写入时机的判定完全由 `GLOBAL_SKILL_MEMORY.md` 协议 3 决定，本文档不重复维护。
- 协议 3 判定执行模式（信息不足 / 紧急 / 标准 / 高精度）
- 模式决定是否写 IDP、何时写、是否带 `retrospective` 字段

## 约束

- 不写 `validated` 字段（由 trace-flush 管理）
- 同一响应只写一次 IDP（覆盖写）
- 文件位置：`<项目根>/.claude/traces/.pending_idp.json`

## 检查清单

- [ ] 在正确时机写入了 `.pending_idp.json`（标准/高精度：代码前；紧急：代码后）？
- [ ] `request` 反映用户真实意图而非 AI 的解释？
- [ ] `mode` 与 GLOBAL_SKILL_MEMORY 协议 3 的判断一致？
- [ ] 没有写入 `validated` 字段？
