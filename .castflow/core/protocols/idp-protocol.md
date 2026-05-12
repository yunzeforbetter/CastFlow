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
  "type": "feature",
  "skills": ["programmer-ui-skill"]
}
```

**返工/纠正/强制规则模式（必须填写经验字段）**：

```json
{
  "mode": "rework",
  "type": "bugfix",
  "skills": ["programmer-ui-skill"],
  "error_cause": "错误使用了 ObservableList.Add() 而非 Insert()",
  "fix_approach": "改用 Insert(index, item) 并在插入前做边界检查",
  "user_feedback": "不行，这个列表顺序不对，必须插入到指定位置",
  "lesson": "ObservableList 的 Add 永远追加到末尾，需要有序插入时必须用 Insert"
}
```

## 字段取值

| 字段 | 取值 |
|------|------|
| `mode` | `standard` / `emergency` / `high-accuracy` / `rework` / `user-rule` |
| `type` | `feature` / `bugfix` / `refactor` / `optimization` / `config` |
| `skills` | 本次使用的 Skill 名称数组 |
| `error_cause` | 错误原因（为什么出错/被拒绝）。rework/user-rule/correction 场景必填 |
| `fix_approach` | 最终修复方案（怎么改对的） |
| `user_feedback` | 用户拒绝/要求时的关键原话 |
| `lesson` | 可复用的经验总结（一句话，未来遇到类似场景应如何做） |
| `rework` | `true`（可选，当 mode 已被占用但确实是用户返工场景时使用） |
| `user_rule` | `true`（可选，当 mode 已被占用但确实是用户强制规则场景时使用） |

## mode 值语义

| mode | 触发场景 | 评分影响 |
|------|---------|---------|
| `standard` | 正常功能开发 | 无额外加分 |
| `emergency` | 紧急修复 | 无额外加分 |
| `high-accuracy` | 高精度模式 | 无额外加分 |
| `rework` | 用户明确拒绝上一次结果并要求返工（"不行"、"重写"、"再来"） | R 维度 = 1.0 × 2.5 |
| `user-rule` | 用户下达硬性约束/规则（"必须用 X"、"禁止 Y"、"以后都这么做"） | U 维度 = 1.0 × 2.0 |

## 经验字段填写规则

当 `mode` 为 `rework` / `user-rule`，或检测到自我修正（revert）时，**必须**填写以下字段：

| 字段 | 怎么写 |
|------|--------|
| `error_cause` | 简明描述根因，不要写"代码有问题"这种废话，要具体到 API/逻辑/理解偏差 |
| `fix_approach` | 最终生效的修复手段，而非中间尝试 |
| `user_feedback` | 用户原话中的关键约束/判断（摘录，非转述） |
| `lesson` | 一句话：下次遇到同类场景应该怎么做。要可复用、可检索 |

标准模式下这些字段可省略（trace 输出为 `_`）。

## 约束

- 不写 `validated` 字段（由 trace-flush 管理）
- 同一响应只写一次 IDP（覆盖写）
- 文件位置：`<项目根>/.claude/traces/.pending_idp.json`

## 检查清单

- [ ] mode 为 rework/user-rule 时，error_cause 和 lesson 是否已填写？
- [ ] lesson 是否足够具体（不是"注意检查"而是"X 场景下必须用 Y 方法"）？
- [ ] user_feedback 是否摘录了用户原话关键部分？
- [ ] `mode` 与 GLOBAL_SKILL_MEMORY 协议 3 的判断一致？
- [ ] 没有写入 `validated` 字段？
