---
name: origin-evolve
description: Analyze execution traces to extract patterns, propose improvements to Skills/Memory, and drive self-evolution of the AI knowledge base
---

# Origin Evolve - Self-Evolution Engine

**定位**: 知识进化器。分析 pipeline 和 skill 的执行历史，识别反复出现的模式，向用户提议改进，将批准的改进写入对应的知识文件。

**核心职责**:
1. 读取 `.claude/traces/trace.md` 中的执行记录
2. 识别失败模式、效率模式和知识缺口
3. 生成结构化的改进提议（含证据、收益、风险）
4. 用户批准后将变更写入正确的归属文件

**与其他 Skill 的关系**:
- code-pipeline-skill 在 Step 9 写入 trace 记录，本 Skill 消费这些记录
- 改进产出写入各 Skill 的 SKILL_MEMORY.md、EXAMPLES.md 或 `.claude/rules/`
- 遵循 SKILL_RULE.md 的文件规范（追加时不破坏已有内容）

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 提议格式和分析示例 | EXAMPLES.md |
| 硬性规则和常见陷阱 | SKILL_MEMORY.md |
| 迭代和维护 | ITERATION_GUIDE.md |

---

## 执行流程

```
触发 -> 读取trace -> 统计筛选 -> 模式识别 -> 生成提议 -> 用户审批 -> 写入变更 -> 标记已处理
```

### 触发方式

用户在对话中输入 `origin evolve` 或类似意图表达。

### Step 1: 读取与筛选

读取 `.claude/traces/trace.md`，跳过已标记 `processed` 的条目。若未处理条目少于 10 条，建议用户继续积累后再分析。

### Step 2: 模式识别

从 trace 中寻找三类模式:

- **失败模式**: 同一步骤反复重试、同一类错误反复出现、用户反复纠正同一问题
- **效率模式**: Skill 组合规律、Sub-agent 使用规律、步骤跳过规律
- **知识缺口**: 任务匹配不到 Skill、SKILL_MEMORY 未覆盖的陷阱

### Step 3: 生成提议

每个模式生成提议，包含: 现象、证据、建议变更、归属文件、预期收益、潜在风险、置信度。仅置信度高且收益明显大于风险时才提议。

### Step 4: 用户审批与执行

逐个展示提议，用户批准后写入对应文件。拒绝的记录原因避免重复提议。

### Step 5: 标记已处理

将已分析的 trace 条目标记为 `processed`。
