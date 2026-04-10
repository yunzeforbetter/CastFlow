# CostFlow

一套可移植的 AI 辅助开发框架。从项目代码中提取架构知识，生成结构化的 Skill 体系，并通过执行记录自动积累经验，让 AI 助手从第一天就深度理解你的项目，且越用越好。

---

## 解决什么问题

AI 助手在大型项目中常见的四个问题：

**1. 架构遗忘** -- AI 不了解项目的分层架构、通信方式、设计模式，生成的代码风格不一致、架构不合规。每次都要重复解释"我们用 Manager 模式"、"Logic 层不能引用 UnityEngine"。

**2. API 幻觉** -- AI 猜测 API 的存在和用法，生成的代码调用了不存在的方法或使用了错误的参数签名，编译不通过。

**3. 知识碎片化** -- 项目规则散落在口头约定、代码注释、文档角落中。不同 AI 会话之间无法共享上下文，同一个错误反复出现。

**4. 经验不积累** -- AI 在上一次犯过的错不会被记住，下一次还会犯。团队成员的纠正和反馈没有沉淀，知识体系停留在初始状态。

CostFlow 的解决方式：

- **冷启动**：从项目真实代码中提取架构知识，生成结构化的 Skill 文件，让 AI 在首次会话就能加载正确的上下文。
- **自我进化**：通过记录每次执行的 trace，自动识别反复出现的模式，提议改进并写入知识体系，形成"使用 - 记录 - 分析 - 改进"的闭环。

---

## 核心设计

### 冷启动

**安装即走**：通过 bootstrap 扫描项目结构，自动生成 Skill、Agent 和项目规则到 `.claude/` 目录。初始化完成后，项目由 `.claude/` 驱动，`.castflow/` 进入休眠。

**真实代码驱动**：所有生成的 Skill 内容（架构规则、代码示例、常见陷阱）都从项目实际代码中扫描提取，不是空模板。

### 渐进式信息披露

每个 Skill 采用四文件结构，AI 按需加载，避免一次性灌入过多上下文：

| 文件 | 何时加载 | 内容 |
|------|---------|------|
| SKILL.md | 首次接触该模块 | 架构概览、快速查询表 |
| EXAMPLES.md | 需要写代码时 | 真实代码示例、API 用法 |
| SKILL_MEMORY.md | 生成代码前 | 硬性规则、常见陷阱 |
| ITERATION_GUIDE.md | 迭代 Skill 时 | 修改规则、文件职责 |

Skill 内部还支持 `modules/` 子目录，按任务关键词路由加载相关子模块，进一步控制上下文粒度。

### 自我进化

**执行记录**：每次完成有实际产出的任务后，AI 自动将执行摘要追加到 `.claude/traces/trace.md`，包括使用的 Skill、修改的文件、重试信息和用户纠正。

**模式识别**：用户通过 `origin evolve` 触发分析。origin-evolve skill 从 trace 中寻找三类模式：

- **失败模式**：同一步骤反复重试、用户反复纠正同一问题
- **效率模式**：Skill 组合规律、Sub-agent 使用规律
- **知识缺口**：任务匹配不到 Skill、SKILL_MEMORY 未覆盖的陷阱

**提议与应用**：每个发现的模式生成结构化提议（含证据、收益、风险），用户审批后写入正确的归属文件。经验自动沉淀到知识体系中。

### 职责分层

| 层级 | 文件 | 管什么 |
|------|------|--------|
| 工作流 | CLAUDE.md | API 验证流程、Skill 使用规范、执行记录规则 |
| 架构 | architect-skill | 分层架构、设计模式、约束规则 |
| 质量 | debug-skill / profiler-skill | 边界检查、性能红线 |
| 模块 | programmer-*-skill | 模块级 API、规则、陷阱 |
| 编排 | code-pipeline-skill | 多模块协作时的工序流转 |
| 进化 | origin-evolve | 执行记录分析、经验提炼、知识改进 |

**可移植**：通过 git submodule 引入，不侵入项目代码。支持 Unity/C#、React/TS、Go 等技术栈。

---

## 安装与初始化

### 第一步：引入框架

```bash
git submodule add <costflow仓库地址> .castflow
git submodule update --init
```

### 第二步：初始化

在 AI 助手（Cursor、Claude Code CLI 等）中输入：

```
bootstrap castflow
```

AI 会自动完成以下工作：

1. **扫描** - 检测项目的技术栈、命名规范、项目规模
2. **逐个确认** - 依次介绍每个 Skill 的用途，你决定是否生成
3. **并行分析** - 为每个确认的 Skill 启动独立的分析任务，从项目代码中提取真实内容
4. **组装验证** - 生成完整的框架文件，验证规范合规

整个过程你只需要回答确认问题，不需要手动创建或编辑任何文件。

### 初始化完成后的文件结构

```
项目根目录/
  CLAUDE.md                             # 项目全局规则（含执行记录规则）
  .claude/
    skills/
      SKILL_RULE.md                     # Skill 规范（来自 core）
      GLOBAL_SKILL_MEMORY.md            # 运行时协议（来自 core）
      code-pipeline-skill/              # 工作流编排（来自 core）
      skill-creator/                    # Skill 创建工具（来自 core）
      origin-evolve/                    # 自我进化（来自 core）
      architect-skill/                  # 项目架构约束（从项目分析生成）
      debug-skill/                      # 边界检测（可选，从项目分析生成）
      profiler-skill/                   # 性能诊断（可选，从项目分析生成）
    agents/
      requirement-analysis-agent.md     # 需求分析（来自 core）
      integration-matching-agent.md     # 集成匹配（来自 core）
      pipeline-verify-agent.md          # 集成验收（来自 core）
    scripts/
      pipeline_merge.py                 # Pipeline Step 3 汇总脚本（来自 core）
    templates/
      programmer.template/              # 模块 Skill 模板
      programmer.template.md            # 模块 Agent 模板
    traces/                             # 执行记录（gitignore）
  .castflow/                             # 进入休眠
```

**从这一刻起，项目自给自足。** 日常开发完全由 `.claude/` 和 `CLAUDE.md` 驱动。

---

## 创建模块 Skill

初始化只生成项目级 Skill（架构/调试/性能）。模块级 Skill（如建筑系统、NPC 系统）由你按需创建：

```
为建筑系统生成 skill

分析 Assets/Scripts/NPC/ 目录，生成模块 skill
```

AI 会：
1. 确认模块 ID 和名称
2. 启动独立 agent 扫描该模块的代码（分析 + 生成闭环）
3. 从项目真实代码中提取架构、API、规则和陷阱
4. 使用 `.claude/templates/` 中的模板生成模块 Skill（4 个文件）

每个模块 Skill 包含 4 个文件（架构概览 + 代码示例 + 硬性规则 + 迭代指南），内容全部来自项目分析，不是空模板。

---

## 日常使用

### 直接使用 Skill 和 Agent

简单任务不需要走 pipeline，直接使用：

```
帮我在建筑系统里加一个批量升级功能

用 debug-skill 检查这段代码的边界条件
```

### 使用 Code Pipeline

需要多模块协作时，使用 code-pipeline 编排：

```
code_pipeline 实现用户交易系统
```

Pipeline 提供从需求拆分到验收交付的标准化工序：

1. **Step 1** - 需求分析与 API 声明
2. **Step 2** - 约束同步与蓝图生成（可选）
3. **Step 3** - 模块实现（可并行，Sub-agent 隔离上下文）
4. **Step 4** - 信息匹配（验证 API 调用与声明的一致性）
5. **Step 5** - 集成验收（GO / GO-WITH-CAUTION / NO-GO）
6. **Step 6-8** - TODO 补全、边界测试、性能诊断（可选）
7. **Step 9** - 完成与清理

Sub-agent 的启动基于上下文压力评估，目的是防止上下文爆炸和注意力分散，而不是为了并行加速。简单功能由主 agent 直接处理。

### 迭代已有的 Skill

| 文件 | 职责 | 何时修改 |
|------|------|---------|
| SKILL.md | 模块架构概览、核心类关系 | 架构变化时 |
| EXAMPLES.md | 代码示例、API用法 | 新增 API 或用法时 |
| SKILL_MEMORY.md | 硬性规则、常见陷阱 | 发现新约束时 |
| ITERATION_GUIDE.md | 迭代触发条件 | Skill 定位变化时 |

---

## 自我进化

### 执行记录

每次 AI 完成有实际产出的任务后，自动将执行摘要追加到 `.claude/traces/trace.md`。这是全局行为，无论是通过 pipeline、直接使用 skill 还是普通开发都会记录。纯咨询对话不记录。

### 触发分析

当 trace 积累到一定量后：

```
origin evolve
```

AI 会读取 origin-evolve skill，按流程分析 trace 并生成提议。

### 提议与审批

每个提议包含：

- **现象**：引用具体的 trace 条目作为证据
- **建议变更**：具体写入什么内容、写到哪个文件
- **预期收益**：减少多少重试率、覆盖什么知识缺口
- **潜在风险**：是否可能过度约束

用户逐个审批。批准后，变更写入正确的归属文件：

| 模式类型 | 写入位置 |
|---------|---------|
| 单 Skill 特有的经验 | 该 Skill 的 SKILL_MEMORY.md |
| 代码模式/用法 | 该 Skill 的 EXAMPLES.md |
| Skill 发现性改进 | 该 Skill 的 SKILL.md 元数据 |
| 跨 Skill 的交叉规则 | .claude/rules/ |
| 项目全局约定 | 建议用户添加到 CLAUDE.md |

### 进化循环

```
使用（带着现有知识工作）
  -> 记录（自动追加 trace）
    -> 分析（origin evolve 识别模式）
      -> 提议（结构化改进方案）
        -> 审批（用户确认）
          -> 改进（写入知识体系）
            -> 使用（带着新知识工作）
```

---

## 框架升级

```bash
git submodule update --remote .castflow
```

然后在 AI 助手中输入：

```
bootstrap 更新核心
```

AI 会同步核心文件到 `.claude/`，不覆盖项目专属文件。已有 CLAUDE.md 按语义去重策略合并。已积累的 Skill Memory 和 traces 不受影响。

---

## 文件归属

| 分类 | 谁管理 | 如何更新 |
|------|--------|---------|
| `.castflow/` 所有文件 | CostFlow 仓库 | `git submodule update` |
| `CLAUDE.md` | 项目团队 | 直接编辑（castflow 段由初始化管理） |
| `.claude/skills/` 项目 Skill | 项目团队 + 进化系统 | 直接编辑、AI 生成、evolve 追加 |
| `.claude/scripts/` | CostFlow 框架 | `bootstrap 更新核心` |
| `.claude/templates/` | CostFlow 框架 | `bootstrap 更新核心` |
| `.claude/agents/` | 项目团队 | 直接编辑 |
| `.claude/skills/` 核心文件 | CostFlow 框架 | `bootstrap 更新核心` |
| `.claude/traces/` | 自动生成 | AI 自动追加，evolve 分析后标记已处理 |
| `.claude/rules/` | 进化系统 | evolve 提议，用户审批后生成 |

**原则**：不要手动编辑 `.castflow/` 里的文件（会被 submodule update 覆盖）。所有定制都在 `.claude/` 和 `CLAUDE.md` 中进行。

---

## 技术细节

以下内容面向框架开发者和高级用户。

### 目录结构

```
.castflow/
  bootstrap.py                          # 确定性文件生成器（Python 3.6+）
  core/                                 # 核心文件
    SKILL_RULE.md                       #   Skill 四文件结构规范
    GLOBAL_SKILL_MEMORY.md              #   运行时核心协议
    agents/                             #   核心 Agent（需求分析/集成匹配/验收）
    skills/
      code-pipeline-skill/              #   含 config/pipeline_protocol.md 扩展协议
      skill-creator/                    #   Skill 创建/迭代工具
      bootstrap-skill/                  #   初始化流程定义（AI 读取此 Skill 执行初始化）
      origin-evolve/                    #   自我进化（trace 分析 + 提议生成）
  scripts/
    pipeline_merge.py                   #   Pipeline Step 3 并行输出汇总
  templates/                            #   生成模板（含 {{占位符}} 和条件段）
```

### bootstrap.py

AI 在初始化过程中生成中间产物（`bootstrap-output/manifest.json` + `content/`），然后调用 `bootstrap.py` 确定性执行文件生成。用户不需要接触这些中间文件。

```bash
python .castflow/bootstrap.py                      # 执行全量生成
python .castflow/bootstrap.py --dry-run            # 预览操作
python .castflow/bootstrap.py --validate           # 验证 .claude/ 规范
python .castflow/bootstrap.py --skill architect    # 增量生成单个 skill
python .castflow/bootstrap.py --agent building     # 按需生成模块 agent
```

### pipeline_merge.py

Pipeline Step 3 并行 agent 各自输出到 `temp/pipeline-output/{module_id}.md`，主 agent 完成后调用此脚本将各模块的 SUMMARY 部分汇总到 PIPELINE_CONTEXT.md，详情留在原文件中供后续步骤按需查阅。

```bash
python .claude/scripts/pipeline_merge.py              # 执行汇总
python .claude/scripts/pipeline_merge.py --dry-run    # 预览操作
```

### CLAUDE.md 合并策略

当项目已有 CLAUDE.md 时，bootstrap 会按以下策略处理：

- **有 boundary marker**：castflow 段更新，项目段保留
- **无 boundary marker**（首次迁移）：按 `## ` 标题拆分为节，逐节语义去重（SequenceMatcher > 50% 判为重复），仅保留真正独有的内容追加到项目段
- 所有场景都会创建 `.migrate-backup` 备份

### 自我进化机制

CostFlow 的进化能力由三部分组成：

1. **Trace 记录** -- CLAUDE.md 中的全局规则，任何有实际产出的任务完成后自动追加到 `.claude/traces/trace.md`
2. **origin-evolve skill** -- 分析 trace 中的失败模式、效率模式和知识缺口，生成结构化提议
3. **归属写入** -- 批准的提议按规则写入正确的文件（SKILL_MEMORY / EXAMPLES / .claude/rules/ / CLAUDE.md）

进化系统遵循三个原则：

- **证据驱动**：每个提议必须引用至少 2 条具体 trace 作为证据
- **正确归属**：变更写入正确的归属文件，单 Skill 模式归该 Skill，跨 Skill 模式归 `.claude/rules/`
- **追加不覆盖**：写入已有文件时仅追加，不修改已有内容
