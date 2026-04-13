---
name: bootstrap-skill
description: CastFlow framework initializer - scans project and generates the complete .claude/ framework structure
---

# Bootstrap-Skill - CastFlow 框架初始化器

**定位**: 框架安装器。扫描项目结构，通过**独立并行 agent** 分析生成项目级 Skill，将完整的 AI 辅助开发框架安装到 `.claude/` 目录。模块级 Skill 由用户后续按需创建。

**核心职责**:
1. 全量初始化：扫描项目，生成项目级框架文件到 `.claude/`
2. 核心更新：同步 castflow submodule 的核心文件变更
3. 模块 Skill 创建：提供模板和流程，供用户按需为各模块生成 Skill

**执行架构**：主 agent 负责编排（扫描、确认、公共文件、验证），每个 skill 的分析和生成由独立并行 agent 全程闭环处理。

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 流程示例和格式 | EXAMPLES.md |
| 硬性规则和约束 | SKILL_MEMORY.md |
| 迭代和维护 | ITERATION_GUIDE.md |

---

## 全量初始化

**适用场景**：首次在项目中引入 CastFlow 框架

**前提条件**：
- 项目已添加 castflow 为 git submodule（位于 `.castflow/`）
- 项目有实际的源代码文件

**流程**：

```
Phase 1: 主agent扫描 -> Phase 2: 主agent确认+公共文件 -> Phase 3: 并行agent各自闭环(分析+生成) -> Phase 4: 主agent验证清理
```

### Phase 1：项目扫描（主 agent 执行）

自动检测以下维度：

**技术栈识别**
- 编程语言：按文件后缀统计（.cs/.ts/.py/.go/.java/.rs 等）
- 框架特征文件检测（Unity: ProjectSettings/; React: package.json; Go: go.mod 等）

**命名规范检测**
- 采样项目主代码目录的类/文件（排除第三方/生成代码）
- 统计字段/方法/常量命名模式

**项目规模评估**
- 源代码文件数量和目录深度
- 识别项目的主代码目录路径

### Phase 2：逐 Skill 确认（主 agent 执行）

向用户展示 Phase 1 的扫描结果（技术栈、命名规范），确认后逐个介绍每个 Skill，用户决定是否生成。

**确认顺序**：

**1. architect-skill（推荐）**

向用户说明：
> architect-skill 记录项目的架构约束规则（如 Manager 模式、分层架构、通信方式）和经过验证的设计模式。所有其他 Skill 和 Agent 都会参考它来确保架构一致性。

用户选择：生成 / 跳过

**2. debug-skill（可选）**

向用户说明：
> debug-skill 提供边界条件检查清单（null 检查、资源释放、状态转换）和项目特定的防御性编程指导。用于代码审查和质量把关。

用户选择：生成 / 跳过

**3. profiler-skill（可选）**

向用户说明：
> profiler-skill 提供性能红线（帧耗时、GC 分配）和优化反模式参考（热路径检测、缓存策略）。用于性能审查和优化。

用户选择：生成 / 跳过

**补充信息收集**：

- **命名规范**：展示扫描结果，用户可采纳、修改或留空
- **框架规则补充**：用户可添加自定义规则
- **语言选择**：默认中文（zh）。用户可指定其他语言（如 "英文"、"en"、"English" 等自然表达），该设置影响所有生成文件的描述性文本。代码本身（变量名、方法名）保持原文不译

**Phase 2 结束时，主 agent 完成三件事**：
1. 生成 `bootstrap-output/manifest.json`（格式见 EXAMPLES.md）
2. 生成 `bootstrap-output/content/claude/` 下的 CLAUDE.md 内容文件（命名规范、框架规则、项目规则）
3. 处理公共文件（核心文件复制、CLAUDE.md 生成、模板复制）：
   - `python .castflow/bootstrap.py --skill core`
   - `python .castflow/bootstrap.py --skill claude`
   - `python .castflow/bootstrap.py --skill templates`

### Phase 3：并行 Agent 闭环生成（核心并行阶段）

**执行模型**：每个 skill 由一个独立 agent **全程闭环处理**——从项目分析到最终 skill 文件落盘，不依赖主 agent 做组装。

```
主agent（编排者）
  |
  |-- Phase 2 已处理公共文件（core、CLAUDE.md、templates）
  |
  |-- 组装 prompt（注入技术栈、主代码目录、项目根路径）
  |
  |-- 同时发射所有 agent（每个 agent 独立完成分析+生成）:
  |     [architect-agent]  分析 → 写 content → bootstrap.py --skill architect → .claude/skills/architect-skill/ 就绪
  |     [debug-agent]      分析 → 写 content → bootstrap.py --skill debug     → .claude/skills/debug-skill/ 就绪
  |     [profiler-agent]   分析 → 写 content → bootstrap.py --skill profiler  → .claude/skills/profiler-skill/ 就绪
  |
  |-- 等待所有 agent 完成
```

**每个 agent 内部执行两步**：
1. **分析**：扫描项目代码，将提取的内容写入 `bootstrap-output/content/{skill_type}/`
2. **生成**：执行 `python .castflow/bootstrap.py --skill {skill_type}` 将 content 填入模板，直接生成最终的 skill 文件到 `.claude/skills/`

**独立性约束**（详见 SKILL_MEMORY.md 规则 6/7）：

- 每个 agent 完全独立运行，不共享上下文
- 每个 agent 的 prompt 必须自包含所有信息（技术栈、代码目录、项目根路径）
- 每个 agent 只写自己的 content 目录和对应的 skill 目录
- agent 之间无执行顺序依赖，失败互不影响

---

**architect agent prompt 模板**：

主 agent 发射时，将 `{TECH_STACK}`、`{SOURCE_DIR}`、`{PROJECT_ROOT}` 替换为实际值。

```
你是架构分析专家。独立完成 architect-skill 的分析和生成，全程闭环。

项目信息：
- 技术栈：{TECH_STACK}
- 主代码目录：{SOURCE_DIR}
- 项目根路径：{PROJECT_ROOT}

== 语言要求 ==
所有生成的 content 文件必须使用 {LANGUAGE} 撰写。
包括：规则描述、陷阱说明、表格标题、段落文字等所有描述性文本。
代码本身（变量名、方法名、类名）保持原文不译。

== SKILL_ITERATION 关键约束（必须遵守） ==

生成的 content 文件最终会填入模板，产出 4 个 Skill 文件。每个文件有严格的大小和内容限制：

| 最终文件 | 字数上限 | 代码块 | 说明 |
|---------|---------|--------|------|
| SKILL.md | < 800字 | 0-1个 | 只放导航和职责描述，不放数据表格 |
| EXAMPLES.md | < 3000字 | 允许 | 代码示例和速查表的唯一存放位置 |
| SKILL_MEMORY.md | < 2000字 | 0个 | 纯文字规则+检查清单，禁止代码块 |
| ITERATION_GUIDE.md | < 1000字 | 0个 | 模板已预置，无需生成 content |

关键禁令：
- hard_rules.md 和 common_pitfalls.md 中禁止使用代码块（```）
- 规则用纯文字描述 + 检查清单格式
- 代码示例只放在 constraint_examples.md 和 pattern_examples.md 中
- 禁止 Emoji 和特殊 Unicode 符号（箭头用 -> 代替）

== 第1步：分析 ==

扫描任务：
1. Grep "Manager|Service|Controller" 识别核心管理器模式
2. Grep "Subscribe|Publish|EventArgs|EventHandler" 识别事件通信模式
3. Grep "Factory|Create|Build" 识别工厂模式
4. Grep "interface I[A-Z]" 识别接口模式
5. 分析项目的分层结构（如有）
6. 识别依赖注入、单例、对象池等模式

将分析结果写入 bootstrap-output/content/architect/ 目录（6 个文件）：
- hard_rules.md - 硬性规则（纯文字，3-7 条，每条含定义+检查清单，禁止代码块）
- common_pitfalls.md - 常见陷阱（纯文字，3-7 条，每条含现象+防护，禁止代码块）
- constraint_rules_summary.md - 约束规则速查表（按类别的表格，每类 3-6 行）
- constraint_examples.md - 约束规则的代码示例（从项目提取 5-8 个核心示例）
- pattern_examples.md - 设计模式的代码示例（从项目提取 5-8 个核心示例）
- design_patterns.md - 设计模式概览（表格形式，模式名+适用场景+参考实现）

格式要求：
- 纯 markdown，内容从项目真实代码提取，不可杜撰
- 禁止 Emoji 和特殊符号
- hard_rules.md + common_pitfalls.md 合计不超过 1500 字
- constraint_examples.md + pattern_examples.md 合计不超过 2500 字

== 第2步：生成 ==

分析完成后，执行：
  python {PROJECT_ROOT}/.castflow/bootstrap.py --skill architect

完成后报告：分析了哪些内容，生成了哪些文件。
```

---

**debug agent prompt 模板**：

```
你是边界条件分析专家。独立完成 debug-skill 的分析和生成，全程闭环。

项目信息：
- 技术栈：{TECH_STACK}
- 主代码目录：{SOURCE_DIR}
- 项目根路径：{PROJECT_ROOT}

== 语言要求 ==
所有生成的 content 文件必须使用 {LANGUAGE} 撰写。
包括：规则描述、陷阱说明、表格标题、段落文字等所有描述性文本。
代码本身（变量名、方法名、类名）保持原文不译。

== SKILL_ITERATION 关键约束（必须遵守） ==

| 最终文件 | 字数上限 | 代码块 | 说明 |
|---------|---------|--------|------|
| SKILL.md | < 800字 | 0-1个 | 模板已预置检查清单，focus_areas 和 project_checks 嵌入 |
| EXAMPLES.md | < 3000字 | 允许 | 代码示例的唯一存放位置 |
| SKILL_MEMORY.md | < 2000字 | 0个 | 纯文字规则+检查清单，禁止代码块 |

关键禁令：
- extra_rules.md 和 extra_pitfalls.md 中禁止使用代码块（```）
- 代码示例只放在 examples.md 中
- 禁止 Emoji 和特殊 Unicode 符号

== 第1步：分析 ==

扫描任务（根据技术栈选择适用项）：
- Unity: MonoBehaviour 生命周期模式、Destroy 后引用、协程管理
- React: useEffect 清理、ref 生命周期、异步状态更新
- Go: goroutine 泄漏、defer 模式、channel 关闭
- 通用: 资源加载/释放配对、事件订阅/取消配对、null 检查模式

将分析结果写入 bootstrap-output/content/debug/ 目录（5 个文件）：
- focus_areas.md - 重点检查领域（简短列表，嵌入 SKILL.md 的 focus_area 参数）
- project_checks.md - 项目特定检查项（简短列表，嵌入 SKILL.md）
- examples.md - 边界条件检查的代码示例（5-8 个，好的实践 vs 错误模式）
- extra_rules.md - 额外硬性规则（纯文字，2-4 条，禁止代码块）
- extra_pitfalls.md - 额外常见陷阱（纯文字，2-4 条，禁止代码块）

格式要求：
- 纯 markdown，代码示例从项目真实代码提取
- extra_rules.md + extra_pitfalls.md 合计不超过 800 字，禁止代码块
- examples.md 不超过 2000 字
- 禁止 Emoji 和特殊符号

== 第2步：生成 ==

分析完成后，执行：
  python {PROJECT_ROOT}/.castflow/bootstrap.py --skill debug

完成后报告：分析了哪些内容，生成了哪些文件。
```

---

**profiler agent prompt 模板**：

```
你是性能分析专家。独立完成 profiler-skill 的分析和生成，全程闭环。

项目信息：
- 技术栈：{TECH_STACK}
- 主代码目录：{SOURCE_DIR}
- 项目根路径：{PROJECT_ROOT}

== 语言要求 ==
所有生成的 content 文件必须使用 {LANGUAGE} 撰写。
包括：规则描述、陷阱说明、表格标题、段落文字等所有描述性文本。
代码本身（变量名、方法名、类名）保持原文不译。

== SKILL_ITERATION 关键约束（必须遵守） ==

| 最终文件 | 字数上限 | 代码块 | 说明 |
|---------|---------|--------|------|
| SKILL.md | < 800字 | 0-1个 | 模板已预置检查矩阵，budgets 和 optimizations 嵌入 |
| EXAMPLES.md | < 3000字 | 允许 | 代码示例的唯一存放位置 |
| SKILL_MEMORY.md | < 2000字 | 0个 | 纯文字规则+检查清单，禁止代码块 |

关键禁令：
- extra_rules.md 和 extra_pitfalls.md 中禁止使用代码块（```）
- 代码示例只放在 examples.md 中
- 禁止 Emoji 和特殊 Unicode 符号

== 第1步：分析 ==

扫描任务（根据技术栈选择适用项）：
- Unity: Update/LateUpdate 中的 GetComponent/new/Find 调用、GC 分配热点
- React: 不必要的 re-render、大型列表无虚拟化、图片未优化
- Go: 热路径中的内存分配、锁竞争、N+1 查询
- 通用: 对象池使用情况、缓存策略、高频循环中的低效操作

将分析结果写入 bootstrap-output/content/profiler/ 目录（5 个文件）：
- performance_budgets.md - 性能预算和红线（简短表格，嵌入 SKILL.md）
- project_optimizations.md - 项目特定优化建议（简短列表，嵌入 SKILL.md）
- examples.md - 性能优化代码示例（5-8 个，问题代码 vs 优化代码，带量化收益）
- extra_rules.md - 额外硬性规则（纯文字，2-4 条，禁止代码块）
- extra_pitfalls.md - 额外常见陷阱（纯文字，2-4 条，禁止代码块）

格式要求：
- 纯 markdown，优化建议必须有量化收益描述
- extra_rules.md + extra_pitfalls.md 合计不超过 800 字，禁止代码块
- examples.md 不超过 2000 字
- 禁止 Emoji 和特殊符号

== 第2步：生成 ==

分析完成后，执行：
  python {PROJECT_ROOT}/.castflow/bootstrap.py --skill profiler

完成后报告：分析了哪些内容，生成了哪些文件。
```

---

### Phase 4：验证与清理（主 agent 执行）

**前提**：所有 Phase 3 的并行 agent 已完成。

**步骤 1 - 结果检查**：

主 agent 检查 `.claude/skills/` 中各 skill 目录是否已生成：
- 缺失的 skill -> warning，询问用户是否重试或跳过
- 所有 skill 就绪 -> 继续验证

**步骤 2 - 规范验证**：

`python .castflow/bootstrap.py --validate`

**步骤 3 - 清理**：

删除 `bootstrap-output/` 临时目录。

**步骤 4 - 完成提示**：

向用户说明：
- 初始化完成，后续开发由 `.claude/` 和 `CLAUDE.md` 驱动
- 模块 Skill 可按需创建（见下方"模块 Skill 创建"章节）
- `.castflow/` 进入休眠

---

## Skill 创建

**触发方式**：

```
为xxx系统生成 skill
分析 Assets/Scripts/XXX/ 目录，生成模块 skill
帮我创建一个xxx的 skill
```

**模板选择**：根据 Skill 的用途选择对应模板。只有功能模块类 Skill 使用 programmer 模板，通用职责类不使用模板。

| 用户意图 | Skill 类型 | 模板 | 示例 |
|---------|-----------|------|------|
| 为某个代码模块创建 Skill | 功能模块 | `.claude/templates/programmer.template/` | 建筑系统、NPC系统、战斗系统 |
| 创建通用职责 Skill | 自由格式 | 无模板，遵循 SKILL_ITERATION.md 四文件结构 | 安全审查、日志规范、多语言 |

**判断标准**：如果 Skill 对应项目中一个具体的代码目录（如 `Assets/Scripts/Modules/Building/`），且包含 Manager/Controller/Handler 等核心类，则属于功能模块 -> 使用 programmer 模板。否则属于通用职责 -> AI 按 SKILL_ITERATION.md 规范直接创建四文件，不套模板。

**前提条件**（功能模块类）：
- 项目已完成全量初始化（`.claude/templates/programmer.template/` 目录存在）

**流程（功能模块类）**：

1. **确认模块信息**（主 agent）
   - 判断是否为功能模块类（有对应代码目录、有核心类）
   - 向用户确认：模块 ID、显示名
   - 确认模块的主要代码目录

2. **启动独立 agent 闭环生成 skill**

   主 agent 组装 prompt（替换占位符），启动独立 agent 完成**分析 + 生成**，全程在 `.claude/` 内部闭环，不依赖 CastFlow 目录。

   ```
   你是模块分析专家。独立完成模块 Skill 的分析与生成，全程闭环。

   模块信息：
   - 模块ID：{MODULE_ID}
   - 模块名称：{MODULE_NAME}
   - 代码目录：{MODULE_DIR}

   == 语言要求 ==
   所有生成的内容必须使用 {LANGUAGE} 撰写。
   包括：规则描述、陷阱说明、表格标题、段落文字等所有描述性文本。
   代码本身（变量名、方法名、类名）保持原文不译。

   == 第1步：分析 ==

   扫描任务：
   1. 识别模块的核心类和接口（Manager、Controller、Handler 等）
   2. 提取核心类的 public API（方法签名、参数、返回值）
   3. 分析模块与其他系统的依赖关系
   4. 识别模块特有的编码约束和常见陷阱
   5. 提取 3-5 个有代表性的代码示例

   == 第2步：从模板生成 skill ==

   读取 `.claude/templates/programmer.template/` 下的 4 个模板文件：
   - SKILL.template.md
   - EXAMPLES.template.md
   - SKILL_MEMORY.template.md
   - ITERATION_GUIDE.template.md

   将分析结果填入模板中的占位符（{{MODULE_ID}}、{{MODULE_DISPLAY_NAME}}、
   {{MODULE_HARD_RULES}}、{{MODULE_PITFALLS}} 等），直接生成最终文件到：
   .claude/skills/programmer-{MODULE_ID}-skill/（4个文件）

   格式要求：
   - 所有内容从项目真实代码提取，不编造
   - SKILL_MEMORY 条目遵循 SKILL_ITERATION.md 的 Anchors/Related 格式
   - 文件大小遵循 SKILL_ITERATION.md 的量化标准

   完成后报告：分析了哪些内容，生成了哪些文件。
   ```

   如果同时创建多个模块 Skill，并行启动多个 agent（每个模块一个）。

   **关于 programmer-agent**：模块 Skill 创建时不生成 agent。agent 的价值在于隔离上下文（pipeline 多模块并行时），日常使用 skill 即可。当 code-pipeline 运行时发现模块缺少 agent，会按需提议创建（见 code-pipeline-skill）。

3. **验证**（主 agent）
   - 检查生成的 skill 文件是否存在于 `.claude/skills/programmer-{MODULE_ID}-skill/`
   - 验证 4 个文件（SKILL.md / EXAMPLES.md / SKILL_MEMORY.md / ITERATION_GUIDE.md）均存在
   - 检查文件大小是否在 SKILL_ITERATION.md 规定范围内

**流程（通用职责类）**：

不使用 programmer 模板。AI 按 SKILL_ITERATION.md 的规范直接创建四文件：

1. 确认 Skill 的名称和职责定位
2. AI 创建 `.claude/skills/{skill-name}/` 目录，包含 SKILL.md、EXAMPLES.md、SKILL_MEMORY.md、ITERATION_GUIDE.md
3. SKILL.md 必须包含元数据和核心职责，超过推荐范围（500字）时必须包含快速导航表
4. 所有文件遵循 SKILL_ITERATION.md 的格式和大小规范
5. SKILL_MEMORY 条目包含 Anchors 和 Related 字段

---

## 核心更新

**适用场景**：castflow submodule 有新版本

**触发方式**：
- "bootstrap 更新核心"

**流程**：
1. 对比 `.castflow/core/` 与 `.claude/skills/` 的核心文件
2. 更新核心文件（SKILL_ITERATION, GLOBAL_SKILL_MEMORY, code-pipeline-skill, skill-creator）
3. 保留项目专属文件（CLAUDE.md, architect-skill, programmer-* skills, agents）
4. CLAUDE.md 按交互式合并策略处理

---
