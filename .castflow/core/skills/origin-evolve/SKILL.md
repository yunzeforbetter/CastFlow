---
name: origin-evolve
description: Analyze execution traces to extract patterns, propose improvements to Skills/Memory, and drive self-evolution of the AI knowledge base
---

# Origin Evolve - Self-Evolution Engine

**定位**: 知识进化器。分析 AI 的执行历史，识别反复出现的模式，向用户提议改进，将批准的改进写入对应的知识文件。

**核心职责**:
1. 读取 `.claude/traces/trace.md` 中的执行记录
2. 利用 trace 的结构化字段进行多维模式识别
3. 生成结构化的改进提议（含证据、收益、风险）
4. 用户批准后将变更写入正确的归属文件
5. 校准评分模型权重（可选，写入 `traces/weights.json`）

**数据来源**:
- Hook 脚本（trace-collector + trace-flush）自动创建 trace 条目，包含文件路径、行数、编辑次数、修正检测、五维评分
- AI 在任务结束时补充 `type` 和 `skills` 字段，丰富 trace 的语义信息
- 本 Skill 消费这些结构化记录，输出改进写入各 Skill 的 SKILL_MEMORY.md、EXAMPLES.md 或 `.claude/rules/`
- 遵循 SKILL_ITERATION.md 的文件规范（追加时不破坏已有内容）

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 提议格式和分析示例 | EXAMPLES.md |
| 硬性规则和常见陷阱 | SKILL_MEMORY.md |
| 迭代和维护 | ITERATION_GUIDE.md |

---

## Trace 条目结构

Hook 自动生成的每条 trace 包含以下字段：

| 字段 | 来源 | 用途 |
|------|------|------|
| timestamp | Hook 自动 | 时间排序、会话匹配 |
| type | AI 补充 | 任务分类聚合（feature/bugfix/refactor/optimization/config） |
| correction | Hook 自动检测 + AI 可补充 | 修正模式识别的核心信号 |
| modules | Hook 从路径推断 | 模块热点分析、跨模块关联发现 |
| skills | AI 补充 | 知识缺口检测 |
| files_modified | Hook 自动 | 具体影响范围 |
| file_count | Hook 自动 | 变更规模 |
| lines_changed | Hook 自动 | 变更深度 |
| edit_count | Hook 自动 | 迭代复杂度（高 edit_count = 困难任务） |
| score | Hook 五维评分 | 条目显著性排序 |

correction 字段值含义：
- `_` : 无修正信号（占位符）
- `auto:minor` : Hook 检测到 1-2 次 AI 自我修正
- `auto:major` : Hook 检测到 3+ 次 AI 自我修正
- `minor` / `major` : AI 手动补充的修正标记

---

## 执行流程

```
触发 -> 读取trace -> 优先级排序 -> 模式识别 -> 生成提议 -> 用户审批 -> 写入变更 -> 标记已处理 -> 校准权重(可选)
```

### 触发方式

用户在对话中输入 `origin evolve` 或类似意图表达。

### Step 1: 读取与排序

读取 `.claude/traces/trace.md`，跳过 `status:processed` 的条目。若 pending 条目少于 10 条，建议用户继续积累后再分析。

按优先级排序待分析条目：
1. correction 含修正信号的条目（auto:minor/auto:major/minor/major）
2. score 较高的条目
3. edit_count 较高的条目

### Step 2: 模式识别

从排序后的 trace 集合中寻找四类模式：

- **修正模式**: correction 非 `_` 的条目聚合。同一 module 反复出现修正 -> 该模块缺少规则指导
- **模块热点**: 按 modules 字段聚合。某些模块组合高频共现 -> 模块间存在未文档化的关联
- **知识缺口**: skills 字段为空的条目。任务未匹配到任何 Skill -> Skill 元数据需要扩展
- **复杂度集中**: edit_count 高但 file_count 低的条目。同一文件被反复修改 -> 可能缺少该文件的使用规则或示例

### Step 3: 生成提议（含写入前治理）

每个识别到的模式，按以下流程生成提议：

**3a. 归属决策**：按 SKILL_MEMORY.md Rule 2 的决策树确定目标 skill 和目标文件。

**3b. 操作类型判定**：
- 目标文件中是否已有语义相似的条目？（检查 Anchors 重叠或描述相似）
  - 是 -> 操作类型 = **Merge**（合并到已有条目）
  - 否 -> 操作类型 = **Append**（追加新条目）

**3c. 容量检查**（Rule 7）：
- 计算目标文件当前字数
- 如果 Append/Merge 后会超过 SKILL_ITERATION 推荐范围 -> 附带 **Retire** 建议
- Retire 候选：对目标文件中所有带 Anchors 的条目执行 grep 验证，锚点在代码中不存在的条目标记为退休候选

**3d. 组装提议**：

每个提议包含：
- 操作类型（Append / Merge / Retire）
- 现象描述
- 证据（引用具体 trace 条目的 timestamp 和 modules）
- 建议变更内容（Merge 时展示 diff）
- 归属文件
- 预期收益
- 潜在风险
- 置信度

仅置信度高且收益明显大于风险时才提议。

### Step 4: 用户审批与执行

逐个展示提议。每个提议明确标注操作类型：

- **Append**：展示将要追加的完整条目（含 Anchors 和 Related 字段）
- **Merge**：展示原条目、合并后条目、以及两者的 diff
- **Retire**：展示条目内容、锚点验证结果（grep 输出）、标记 `[RETIRED]` 后的效果

用户批准后执行写入。拒绝的记录原因，追加 EVOLVE_REJECTION 条目到 trace.md。

### Step 5: 标记已处理

将已分析的 trace 条目 `status:pending` 替换为 `status:processed`。

### Step 6: 校准评分模型（可选）

当已处理条目累计达到 20+ 条时，可微调 `traces/weights.json`：

- 对比"产出有效提议的 trace"与"未产出提议的 trace"的各维度分布
- 某维度在有效 trace 中显著偏高 -> 该权重 +5~10%
- 准入率偏高或偏低 -> 调整 threshold
- 单次调整幅度不超过 10%
- 权重范围 0.2~3.0，阈值范围 1.0~3.0
- 此步骤为可选，仅在数据充分时执行
