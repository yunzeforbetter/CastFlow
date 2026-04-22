---
name: skill-iteration
description: Skill 文件元规范 (meta-spec)。仅规范 Skill 自身的文件结构、格式、容量、命名。不涉及代码生成、需求拆解、日常 Skill 调用流程 - 这些归 GLOBAL_SKILL_MEMORY 与各 Skill 的 SKILL_MEMORY。仅在创建新 Skill、修改既有 Skill 结构时阅读，日常调用 Skill 时无需加载。
---

# SKILL_ITERATION.md - Skill 文件元规范

**定位**：Skill 文件本身的元规范（meta-spec）。规定 4 文件结构、格式、容量、命名。

**性质**：硬性规范，非建议。违反即 Skill 创建/迭代工作无效。

**加载时点**：仅 **T4-MAINTAIN**（创建新 Skill 或修改既有 Skill 自身结构时）。完整时点定义见项目根 `CLAUDE.md`「使用Skill的分层加载」段（唯一权威源）。

**何时需要阅读**（即 T4-MAINTAIN 触发）：
- 创建新 Skill 时
- 修改既有 Skill 的结构、字数、格式时
- 验收 Skill 文件交付物时

**何时不需要阅读**（常见误用，对照其他时点）：
- 日常调用某个 Skill 处理代码任务 → 目标 Skill 的 `SKILL.md` 由宿主自动注入，不需主动读本文档
- 准备生成代码（T1-PREPARE）→ 读 `GLOBAL_SKILL_MEMORY.md` 协议 1/2 + 该 Skill 的 SKILL_MEMORY.md
- 代码生成中决策 IDP 写入（T2-EXECUTE）→ 读 `GLOBAL_SKILL_MEMORY.md` 协议 3 + 按需 `protocols/idp-protocol.md`
- 拆解需求或编排工序 → 读 `code-pipeline-skill`
- 用户反馈接受/拒绝（T3-FEEDBACK）→ 读 `protocols/validated-protocol.md`

**与其他文档的边界**：

| 文档 | 管辖范围 | 与本文档的关系 |
|------|---------|--------------|
| 本文档（SKILL_ITERATION.md）| Skill 自身的"长什么样" | 元规范，T4-MAINTAIN 加载 |
| 项目 CLAUDE.md | 项目级规则 + 时点定义（唯一权威源） | 规定本文档的加载时点 = T4-MAINTAIN |
| GLOBAL_SKILL_MEMORY.md | Skill 调用时的运行时协议（API 验证、约束对齐、执行模式） | 互不重叠 |
| protocols/idp-protocol.md | IDP 写入规则 | 互不重叠 |
| protocols/validated-protocol.md | 用户反馈信号写入规则 | 互不重叠 |
| 各 Skill 的 SKILL_MEMORY.md | 该 Skill 业务领域的硬性规则 | 本文档规定其格式，CLAUDE.md 规定其加载时点 |
| 各 Skill 的 ITERATION_GUIDE.md | 该 Skill 自身的演进规则 | 本文档规定其格式，CLAUDE.md 规定其加载时点（T4-MAINTAIN） |

---

## 快速导航

| 我要做什么 | 查看 |
|----------|------|
| 创建新 Skill | [Skill 文件结构](#skill文件结构标准) + [创建前准备](#创建或迭代前的准备) |
| 修改既有 Skill 内容 | [禁止事项](#工作进行中的禁止事项) + [完成前验收](#工作完成前的验收检查) |
| 验收 Skill 文件交付 | [验收检查](#工作完成前的验收检查) + [规范检查命令集](#规范检查命令集) |
| 计算字数是否超限 | [文件大小量化标准](#文件大小量化标准) |
| 添加 SKILL_MEMORY 条目时容量已满 | [SKILL_MEMORY 容量治理](#3-skill_memorymd---硬性规范库) |

---

## 创建或迭代前的准备

只在**修改 Skill 自身结构**时执行。日常调用 Skill 不走这个清单。

- [ ] 已完整阅读本文档（SKILL_ITERATION.md）
- [ ] 修改既有 Skill 时，已读取该 Skill 的 `ITERATION_GUIDE.md`
- [ ] 用户已明确表达"创建新 Skill"或"修改 X Skill 的结构/规则"，而非"用 X Skill 帮我写代码"
- [ ] 已识别本次改动属于哪个文件（SKILL.md / EXAMPLES.md / SKILL_MEMORY.md / ITERATION_GUIDE.md），避免越职责放置内容

**误用反例**（这些情况不要读本文档）：
- "用 building-skill 帮我加一个仓库建筑" → 这是调用 Skill，读 building-skill 的 SKILL.md
- "code-pipeline 帮我重构 NPC 系统" → 这是工序编排，读 code-pipeline-skill
- "我刚学了某 API 应该怎么应用" → 这是约束对齐，读 GLOBAL_SKILL_MEMORY 协议 2

---

## 工作进行中的禁止事项

**以下行为严格禁止，违反即工作无效**：

### 禁止1：创建外部临时文档

**禁止**：
- 分析文档（ANALYSIS.md、OPTIMIZATION.md等）
- 总结文档（SUMMARY.md、OVERVIEW.md等）
- 临时记录（TEMP.md、TODO.md等）
- 规范内容存储在Skill目录之外

**允许**：
- 所有内容仅在4个核心文件中：SKILL.md、EXAMPLES.md、SKILL_MEMORY.md、ITERATION_GUIDE.md
- 如发现需要新内容，更新现有文件或新建必要文件

**检查**：见末尾 [规范检查命令集](#规范检查命令集)

---

### 禁止2：使用Emoji和特殊符号

**禁止的字符**（不能在 Skill 四文件中出现）：
- Emoji：任何 emoji 或特殊符号
- 特殊符号：箭头、勾叉等 Unicode 符号
- 特殊装饰：[Rules] [RETURN] 等括号装饰

**允许**：
- 标准Markdown：**粗体**、*斜体*、`代码`、代码块
- 列表标记：- 或 *
- 标题标记：# ## ### 等
- 链接：[文本](链接)
- 表格：| | |

**检查**：见末尾 [规范检查命令集](#规范检查命令集)

---

### 禁止3：违反文件职责

**每个文件有明确职责，违反即违规**：

| 文件 | 允许内容 | 禁止内容 |
|------|--------|--------|
| **SKILL.md** | 职责定义、流程说明 | 代码示例、API教程、版本历史 |
| **EXAMPLES.md** | 代码示例、参考位置 | 规范定义、历史记录、理论说明 |
| **SKILL_MEMORY.md** | 硬性规则、陷阱 | 日志、时间戳、版本记录、进度记录 |
| **ITERATION_GUIDE.md** | 迭代规则、触发条件 | 历史日志、检查记录、日期 |

**检查**：见末尾 [规范检查命令集](#规范检查命令集)

---

### 禁止4：未验证的参考

**所有文件引用必须在项目中真实存在**：

**禁止**：
- 引用不存在的文件路径
- 引用已删除的类或方法
- 创建虚假的命名空间
- 代码示例中用不存在的API
- **在没有运行 Grep 或 Read 前声明 API 签名**

**允许**：
- 所有参考都在项目中验证过（通过 Grep、Read、Find）
- 代码示例都能在IDE中编译运行
- 所有类/方法位置都准确

---

### 禁止5：代码示例不可编译

**EXAMPLES.md中的所有代码必须在IDE中编译通过**：

**禁止**：
- 伪代码（"概念代码"）
- 不完整的代码片段（缺少using声明）
- 使用不存在的API的代码

**允许**：
- 完整的可编译代码
- 包含所有必要的using声明
- 在项目中实际存在的类和方法

---

## 工作完成前的验收检查

**提交前必须完成以下5项检查，任一失败即工作无效**：

### 检查1：文件结构完整

**必须包含以下文件（恰好 4 个 .md）**：
- SKILL.md / EXAMPLES.md / SKILL_MEMORY.md / ITERATION_GUIDE.md

### 检查2：必需的元数据

**仅 SKILL.md 必须有 YAML 元数据**（name + description），其他 3 个文件为 SKILL.md 服务，元数据可选

**适用范围说明**：此规则仅约束 Skill 四文件体系。Agent 文件（`.claude/agents/*.md`）、规范文件（SKILL_ITERATION.md 等）、模板文件各有自己的元数据需求，不受此条限制

### 检查3：禁止内容扫描

- 无临时文档名（ANALYSIS/OPTIMIZATION/TEMP/TODO 等）
- 无 Emoji 和特殊符号
- SKILL_MEMORY.md / ITERATION_GUIDE.md 中无日期/版本标记

### 检查4：文件职责验证

**SKILL.md**：
- [ ] 包含元数据（name + description）
- [ ] 包含核心职责列表
- [ ] 超过推荐范围（500字）时包含快速导航表
- [ ] 不包含代码示例、版本历史

**EXAMPLES.md**：
- [ ] 包含快速导航表（始终强制）
- [ ] 包含 3-10 个核心示例（描述、代码、场景、陷阱、参考）
- [ ] 所有代码可编译、using 完整、参考真实存在

**SKILL_MEMORY.md**：
- [ ] 包含快速导航表（始终强制）
- [ ] 不包含日期、时间戳、版本信息、更新日志

**ITERATION_GUIDE.md**：
- [ ] 包含快速导航表（始终强制）
- [ ] 不包含日期、时间戳、版本信息、更新日志

### 检查5：参考验证（抽样）

- 对 EXAMPLES.md 中的文件路径和类名用 Grep/Find 抽样验证
- 无结果 = 违反规范 = 工作无效

**所有检查的具体命令**：见下方 [规范检查命令集](#规范检查命令集)

---

## 规范检查命令集

**完成工作后，按顺序运行以下命令**：

```bash
# 第1步：检查文件数量（必须恰好4个）
echo "检查：文件数量"
ls *.md | wc -l
# 预期结果：4

# 第2步：检查文件名
echo "检查：文件名"
ls SKILL.md EXAMPLES.md SKILL_MEMORY.md ITERATION_GUIDE.md 2>/dev/null && echo "PASS" || echo "FAIL"
# 预期结果：PASS

# 第3步：检查临时文档
echo "检查：临时文档"
find . -name "*.md" | grep -iE "(ANALYSIS|OPTIMIZATION|TEMP|TODO|ROOT_CAUSE|QUICK|FORMAL|SUMMARY|OVERVIEW)" | wc -l
# 预期结果：0

# 第4步：检查Emoji（严格）
echo "检查：Emoji1"
grep -nE '[❌✅⭐📋🔴🟡🟢✓✗→↔←↓↑]' *.md | wc -l
# 预期结果：0

# 第5步：检查特殊符号（严格）
echo "检查：特殊符号"
grep -nE '[►▼▲◄◆★]' *.md | wc -l
# 预期结果：0

# 第6步：检查元数据（仅 SKILL.md 必须）
echo "检查：元数据"
if grep -q "^name:" SKILL.md && grep -q "^description:" SKILL.md; then echo "SKILL.md PASS"; else echo "SKILL.md FAIL"; fi

# 第7步：检查日期标记
echo "检查：日期标记"
grep -nE '202[0-9]|月份|Updated|modified' SKILL_MEMORY.md ITERATION_GUIDE.md | wc -l
# 预期结果：0

# 第8步：检查SKILL.md中的代码块
echo "检查：SKILL.md代码"
grep -c '```' SKILL.md
# 预期结果：0 或 1（最多演示一个流程图）

# 最终检查：所有检查都通过
echo "=== 所有检查完成 ==="
```

**验收标准**：
- 所有预期结果都符合 → **PASS**，工作有效
- 任何一项不符合 → **FAIL**，工作无效，必须重做

---

## 元规范分层

Skill 创建和迭代时受**两层元规范**约束，两层同时生效：

| 层 | 文件 | 内容 | 适用范围 |
|---|------|------|---------|
| 全局元规范 | 本文档 SKILL_ITERATION.md | 4 文件结构、格式、容量、命名 | 所有 Skill |
| 单 Skill 元规范 | 各 Skill 的 ITERATION_GUIDE.md | 该 Skill 特有的迭代触发条件、优先级、文件职责分配 | 该 Skill 自身 |

**不要混淆**：本节的"两层"是 Skill 元规范的分层（描述"如何写 Skill 文件"）。Skill 调用时的运行时协议分层见 [GLOBAL_SKILL_MEMORY.md](./GLOBAL_SKILL_MEMORY.md)（描述"调用 Skill 时如何工作"），是完全不同的话题。

---

## Skill文件结构标准

**原则**：4个核心文件的职责必须清晰分离。用户按下列流程接触Skill：

```
新手（5秒）→ SKILL.md：我是什么、能做什么
   ↓
开发者（30秒）→ EXAMPLES.md：怎么用、有哪些场景
   ↓
深度用户 → SKILL_MEMORY.md：我有什么约束、陷阱
   ↓
维护者 → ITERATION_GUIDE.md：怎么维护、何时更新
```

---

### 1. SKILL.md - 职责定义和导航

**职责**：说明"这个Skill是什么、能做什么"

**必需内容**（按顺序）：
1. 元数据：`name:` 和 `description:`（一句话，不超过80字）
2. 核心职责：3-5点列表，每点一句话
3. 快速导航表（超过推荐范围时强制）：

```markdown
| 需要了解 | 查看 |
|---------|------|
| 代码示例和API用法 | EXAMPLES.md |
| 硬性规则和陷阱 | SKILL_MEMORY.md |
| 何时迭代 | ITERATION_GUIDE.md |
```

**文件大小**：300-500字 | **警戒线**：超800字=职责混杂

**快速导航规则**：

| 文件 | 快速导航 | 原因 |
|------|---------|------|
| SKILL.md | 超过推荐范围（>500字）时强制 | 小文件内容一目了然，大文件需要索引 |
| EXAMPLES.md | **始终强制** | 包含多个示例，必须有目录让 AI 按需定位 |
| SKILL_MEMORY.md | **始终强制** | 包含多条规则和陷阱，必须有目录快速检索 |
| ITERATION_GUIDE.md | **始终强制** | 包含多条迭代规则，必须有目录定位触发条件 |

**禁止内容**：
- 代码示例（全部放EXAMPLES.md）
- 具体API教程（全部放EXAMPLES.md）
- 规范定义（全部放SKILL_MEMORY.md）
- 迭代规则（全部放ITERATION_GUIDE.md）
- Emoji或特殊符号
- 任何时间信息

**检查**：
```bash
grep -c '```' SKILL.md
# 应该 = 0 或 1（最多1个流程图，不是代码示例）

wc -w SKILL.md
# 应该 < 800字
```

---

### 2. EXAMPLES.md - 代码示例库和参考

**职责**：提供"怎么用这个Skill"的准确示例和参考

**必需内容**（每个示例）：

```markdown
## 示例N：[简明标题]

描述
[这个示例解决什么问题，一句话]

场景
[什么情况下用这个示例]

代码
[完整、能编译的代码，含所有using]

常见陷阱
- [容易出错的地方1]
- [容易出错的地方2]

项目参考
[真实文件路径或类名]
```

**文件大小**：5-15个示例，800-2000字 | **警戒线**：超3000字=内容混杂

**质量约束**：
- 所有代码必须在IDE中编译通过
- 所有using声明完整
- 所有项目参考真实存在（grep/find验证）
- 代码应从项目实现中复制，不是推测

**禁止内容**：
- 规范定义（全部放SKILL_MEMORY.md）
- 迭代规则（全部放ITERATION_GUIDE.md）
- 版本历史或更新日志
- Emoji或特殊符号

**检查**：
```bash
# 验证参考真实存在
grep "参考:" EXAMPLES.md | grep -oE 'Assets/[^"]+' | while read path; do
  find . -path "*$path" | head -1 || echo "不存在: $path"
done
```

---

### 3. SKILL_MEMORY.md - 硬性规范库

**职责**：记录该Skill的不可协商的约束和常见陷阱

**必需内容**（两部分）：

**Part 1：硬性规则**（3-7条）
```markdown
规则N：[规则名称]

Anchors: [代码符号1, 代码符号2]
Related: 规则X、陷阱Y

定义
[什么是被禁止或被要求的，10-50字]

检查清单
- [ ] 检查项1
- [ ] 检查项2
```

**Part 2：常见陷阱**（3-7条）
```markdown
陷阱N：[陷阱名称]

Anchors: [代码符号1, 代码符号2]
Related: 规则X

现象
[这个陷阱的症状]

防护
[如何避免这个陷阱]
```

**Anchors 和 Related 字段**：

- `Anchors`：该条目引用的代码符号（类名、方法名）。用于 origin-evolve 的退休验证（grep 项目检查符号是否存在）。手动创建时可选，origin-evolve 写入时必填。
- `Related`：与本条目相关的其他规则/陷阱编号。用于 Merge 时识别候选，Retire 时标记需要连带审查的条目。

**[RETIRED] 标记**：

条目标题末尾添加 `[RETIRED]` 表示该条目已过期（如引用的代码符号不再存在）。AI 加载 SKILL_MEMORY 时跳过 RETIRED 条目。条目内容保留不删除，用户可随时移除标记恢复。

```markdown
### 规则3：XXX规则 [RETIRED]
```

**文件大小**：800-1500字 | **警戒线**：超2000字=规范混杂

**容量治理**（当接近或超过推荐范围时）：

支持三种操作，每种都需要用户确认：

- **Append**：添加新条目。条件：无语义重叠的已有条目。新条目必须包含 Anchors 和 Related。
- **Merge**：将新内容合并到已有条目。条件：新模式与已有条目 Anchors 重叠或描述同一代码区域。必须向用户展示合并前后的 diff。
- **Retire**：标记条目为 `[RETIRED]`。条件：Anchors 中的代码符号在项目中不再存在（通过 grep 验证）。不删除内容，仅加标记。

**容量检查流程**：写入前计算目标文件字数。如果写入后会超过推荐范围，必须先 Merge 或 Retire 已有条目腾出空间。如果超过警戒线，必须阻止写入直到容量回到范围内。

**禁止内容**（严格）：
- 日期/时间戳（严禁"最后更新于2025-02-26"）
- 版本历史（严禁"V2.0、v1.1"）
- 过程记录（严禁"修改于...、用户反馈时..."）
- 代码示例（全部放EXAMPLES.md）
- 任何时间信息

**原因**：这个文件随项目迁移，时间信息会过期。版本控制在git历史中。

**检查**：
```bash
# 禁止日期
grep -E '202[0-9]|更新|修改于|Last' SKILL_MEMORY.md
# 应该返回空

# 禁止代码块
grep -c '```' SKILL_MEMORY.md
# 应该 = 0
```

---

### 4. ITERATION_GUIDE.md - 维护和演进规则

**职责**：定义该Skill如何演进、何时更新什么

**必需内容**（4部分）：

**Part 1：Skill定位**（4点，100字内）
```markdown
本Skill的核心职责（与SKILL.md一致）：
1. [职责1]
2. [职责2]
3. [职责3]
4. [职责4]

目标用户：[谁会用此Skill]
```

**Part 2：迭代规则**（Rule 1/2/3）
```markdown
Rule N：[规则名称]
触发条件：[什么情况触发]
优先级：High/Medium/Low
文件：[修改哪个文件]
检查清单：
  - [ ] 项1
  - [ ] 项2
```

**Part 3：文件职责**（表格）
```markdown
| 文件 | 何时修改 | 禁止内容 |
|-----|--------|--------|
| SKILL.md | 职责变化时 | 代码、规则定义 |
| EXAMPLES.md | 新用法出现时 | 规则定义、日期 |
| SKILL_MEMORY.md | 发现新约束时 | 日期、版本、过程记录 |
| ITERATION_GUIDE.md | 定位变化时 | 日期、版本、检查记录 |
```

**Part 4：质量指标**（3-4个）
```markdown
指标1：[名称] - [目标值]
  测量：[如何验证]
```

**文件大小**：500-800字 | **警戒线**：超1000字=过度详细

**禁止内容**（严格）：
- 历史日志（严禁"检查记录"）
- 日期信息（严禁任何日期，如"2025-02-26"）
- 版本标记（严禁"V2.0"）
- 时间戳（严禁"10:30"）
- 个人签名（严禁"By xxx"）

**检查**：
```bash
# 禁止日期
grep -E '202[0-9]|检查于|更新于|历史' ITERATION_GUIDE.md
# 应该返回空

# 文件大小
wc -w ITERATION_GUIDE.md
# 应该 < 1000字
```

---

### 四文件的相互关系

**信息流关键约束**：

**必需的流向**：
- SKILL.md -> EXAMPLES.md（导航链接）
- EXAMPLES.md -> SKILL_MEMORY.md（约束链接）
- SKILL_MEMORY.md -> EXAMPLES.md（陷阱示例链接）
- ITERATION_GUIDE.md -> 所有文件（迭代指导）

**禁止的逆向**：
- SKILL_MEMORY.md 不得包含日期信息
- ITERATION_GUIDE.md 不得包含时间戳
- 任何文件不得包含 Emoji 或特殊符号

---

### 文件大小量化标准

| 文件 | 推荐范围 | 警戒线 | 超过=违规 |
|------|--------|--------|---------|
| SKILL.md | 300-500字 | 800字 | 职责混杂 |
| EXAMPLES.md | 800-2000字 | 3000字 | 内容混杂 |
| SKILL_MEMORY.md | 800-1500字 | 2000字 | 规范混杂 |
| ITERATION_GUIDE.md | 500-800字 | 1000字 | 过度详细 |

**检查方法**：
```bash
for file in SKILL.md EXAMPLES.md SKILL_MEMORY.md ITERATION_GUIDE.md; do
  words=$(wc -w < "$file" 2>/dev/null || echo 0)
  echo "$file: $words字"
done
```

---

### 维护触发清单

| 情景 | 修改SKILL.md | 修改EXAMPLES.md | 修改SKILL_MEMORY.md | 修改ITERATION_GUIDE.md |
|------|-------------|----------------|------------------|---------------------|
| 新用法出现 | - | **是** | 可能 | - |
| 发现新约束 | - | - | **是** | - |
| 职责范围变化 | **是** | 可能 | 可能 | **是** |
| 性能优化 | - | 可能 | - | - |
| 框架API变化 | - | **是** | 可能 | - |
| 用户反馈问题 | - | **是** | 可能 | - |

---

## 与 GLOBAL_SKILL_MEMORY 的边界（不重叠）

| 维度 | 本文档（SKILL_ITERATION.md） | GLOBAL_SKILL_MEMORY.md |
|------|---------------------------|------------------------|
| 关心什么 | Skill 文件长什么样 | 调用 Skill 时如何工作 |
| 加载时点 | T4-MAINTAIN | T1-PREPARE / T2-EXECUTE |
| 强制对象 | Skill 作者 | 所有调用 Skill 的 AI 行为 |
| 典型条目 | "EXAMPLES.md 必须 < 3000 字" | "使用任何 API 前必须 Read 源文件 + Grep 验证" |
| 修改频率 | 极低（框架级） | 极低（框架级） |

两份文档互不引用对方的内容，也互不重叠。时点完全不重合（T4 vs T1/T2）。

---

## 违反规范的后果

**任何规范违反，工作即无效**：

1. **无法接受** - 违反规范的工作必须重做
2. **浪费资源** - 修复违规内容消耗额外Token和时间
3. **技术债** - 遗留问题影响后续工作
4. **信任问题** - 影响工作质量评价

**没有例外**，时间压力不是理由。

---

## 关键原则

**这不是建议，这是规范**：
- 规范是"必须做"，不是"最好做"
- 违反规范 = 工作无效 = 必须重做
- 时间压力不能成为绕过规范的理由
- "很快完成"不能牺牲规范遵守

**宁可花费额外时间做规范的工作，也不能完成不规范的工作**

---

*SKILL_ITERATION.md | 创建和迭代规范*
