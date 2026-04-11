# CostFlow

一套可移植的 AI 辅助开发框架。从项目代码中提取架构知识，生成结构化的 Skill 体系，并通过 Hook 自动采集执行数据驱动知识进化，让 AI 助手从第一天就深度理解你的项目，且越用越好。

---

## 解决什么问题

AI 助手在大型项目中常见的四个问题：

**1. 架构遗忘** -- AI 不了解项目的分层架构、通信方式、设计模式，生成的代码风格不一致、架构不合规。每次都要重复解释"我们用 Manager 模式"、"Logic 层不能引用 UnityEngine"。

**2. API 幻觉** -- AI 猜测 API 的存在和用法，生成的代码调用了不存在的方法或使用了错误的参数签名，编译不通过。

**3. 知识碎片化** -- 项目规则散落在口头约定、代码注释、文档角落中。不同 AI 会话之间无法共享上下文，同一个错误反复出现。

**4. 经验不积累** -- AI 在上一次犯过的错不会被记住，下一次还会犯。团队成员的纠正和反馈没有沉淀，知识体系停留在初始状态。

CostFlow 的解决方式：

- **冷启动**：从项目真实代码中提取架构知识，生成结构化的 Skill 文件，让 AI 在首次会话就能加载正确的上下文。
- **自我进化**：通过 Hook 脚本自动采集执行 trace（零 token），AI 补充语义分类，origin-evolve 按分类聚合分析并提议改进，形成闭环。

---

## 核心设计

### 冷启动

**安装即走**：通过 bootstrap 扫描项目结构，自动生成 Skill、Agent 和项目规则到 `.claude/` 目录。初始化完成后，项目由 `.claude/` 驱动，CostFlow 进入休眠。

**真实代码驱动**：所有生成的 Skill 内容（架构规则、代码示例、常见陷阱）都从项目实际代码中扫描提取，不是空模板。

**跨平台**：bootstrap.py 自动检测项目根目录，支持 CostFlow 作为子目录或 submodule 引入。Cursor 和 Claude Code 均可使用。

### 渐进式信息披露

每个 Skill 采用四文件结构，AI 按需加载，避免一次性灌入过多上下文：

| 文件 | 何时加载 | 内容 |
|------|---------|------|
| SKILL.md | 首次接触该模块 | 架构概览、快速查询表 |
| EXAMPLES.md | 需要写代码时 | 真实代码示例、API 用法 |
| SKILL_MEMORY.md | 生成代码前 | 硬性规则、常见陷阱 |
| ITERATION_GUIDE.md | 迭代 Skill 时 | 修改规则、文件职责 |

### 自我进化

**两层数据采集**：

| 层 | 谁采集 | 采集什么 | 成本 |
|----|--------|---------|------|
| Hook 脚本 | 自动 | 修改的文件、涉及模块、时间戳 | 零 token |
| AI 规则 | 任务结束时 | 任务类型、用户纠正、使用的 Skill | 少量 token |

**四维 Trace 分类**：

```
<!-- TRACE status:pending -->
timestamp: 2026-04-11T15:30:00Z
type: bugfix                        <- AI 补充
correction: minor                   <- AI 补充（进化触发的关键信号）
modules: [Building, Hero]           <- Hook 自动推断
skills: [programmer-building-skill] <- AI 补充
files_modified: [...]
file_count: 5
<!-- /TRACE -->
```

**分类驱动的智能提醒**：不是简单的"10 条就提醒"，而是：
- pending >= 10 条，或
- 含用户纠正的条目 >= 3 条（纠正记录最有提炼价值）

**模式识别与提议**：`origin evolve` 按分类聚合分析：
- correction: major 反复出现 -> 高优先级提议
- 同一 module 反复被 bugfix -> 该模块规则缺失
- module 组合反复出现 -> 模块关联性发现

### 职责分层

| 层级 | 文件 | 管什么 |
|------|------|--------|
| 工作流 | CLAUDE.md | API 验证流程、Skill 使用规范、执行记录规则 |
| 架构 | architect-skill | 分层架构、设计模式、约束规则 |
| 质量 | debug-skill / profiler-skill | 边界检查、性能红线 |
| 模块 | programmer-*-skill | 模块级 API、规则、陷阱 |
| 编排 | code-pipeline-skill | 多模块协作时的工序流转 |
| 进化 | origin-evolve + hooks | 执行记录采集、分析、经验提炼 |

**可移植**：支持 Unity/C#、React/TS、Go 等技术栈。支持 Cursor 和 Claude Code。

---

## 安装与初始化

### 第一步：引入框架

作为子目录引入：

```bash
# 方式 1：git submodule
git submodule add <costflow仓库地址> CostFlow

# 方式 2：直接克隆
git clone <costflow仓库地址> CostFlow
```

CostFlow 不要求放在项目根目录下的 `.castflow/`，放在任意子目录均可。bootstrap.py 会自动向上查找项目根目录（通过 `.claude/` 或 `.git/` 定位）。

### 第二步：初始化

在 AI 助手（Cursor、Claude Code 等）中输入：

```
bootstrap castflow
```

AI 会自动完成以下工作：

1. **扫描** - 检测项目的技术栈、命名规范、项目规模
2. **逐个确认** - 依次介绍每个 Skill 的用途，你决定是否生成
3. **并行分析** - 为每个确认的 Skill 启动独立的分析任务，从项目代码中提取真实内容
4. **组装验证** - 生成完整的框架文件，验证规范合规
5. **配置 Hooks** - 生成跨平台的 trace 自动采集 hook

整个过程你只需要回答确认问题，不需要手动创建或编辑任何文件。

### 初始化完成后的文件结构

```
项目根目录/
  CLAUDE.md                             # 项目全局规则
  .claude/
    skills/                             # Skill 文件
      SKILL_RULE.md                     #   Skill 规范（来自 core）
      GLOBAL_SKILL_MEMORY.md            #   运行时协议（来自 core）
      code-pipeline-skill/              #   工作流编排（来自 core）
      skill-creator/                    #   Skill 创建工具（来自 core）
      origin-evolve/                    #   自我进化（来自 core）
      architect-skill/                  #   项目架构约束（从项目分析生成）
      debug-skill/                      #   边界检测（可选）
      profiler-skill/                   #   性能诊断（可选）
    hooks/                              # 跨平台 trace 采集脚本
      trace-collector.py                #   文件编辑时自动采集
      trace-flush.py                    #   Agent 结束时汇总与分类
    agents/                             # Agent 定义
    scripts/                            # 工具脚本
    templates/                          # 生成模板
    traces/                             # 执行记录（gitignore）
    settings.json                       # Claude Code hook 配置
    rules/                              # 进化系统生成的规则
  .cursor/
    hooks.json                          # Cursor hook 配置
    rules/                              # Cursor 规则
  CostFlow/                             # 框架源码（进入休眠）
```

---

## 创建模块 Skill

初始化只生成项目级 Skill（架构/调试/性能）。模块级 Skill 由你按需创建：

```
为建筑系统生成 skill

分析 Assets/Scripts/NPC/ 目录，生成模块 skill
```

AI 会：
1. 确认模块 ID 和名称
2. 启动独立 agent 扫描该模块的代码
3. 从项目真实代码中提取架构、API、规则和陷阱
4. 生成模块 Skill（4 个文件）

---

## 日常使用

### 直接使用 Skill

简单任务不需要走 pipeline：

```
帮我在建筑系统里加一个批量升级功能

用 debug-skill 检查这段代码的边界条件
```

### 使用 Code Pipeline

需要多模块协作时：

```
code_pipeline 实现用户交易系统
```

Pipeline 提供从需求拆分到验收交付的标准化工序（Step 1-9），包括需求分析、并行实现、API 匹配验证、集成验收等环节。

### 迭代已有的 Skill

| 文件 | 职责 | 何时修改 |
|------|------|---------|
| SKILL.md | 模块架构概览 | 架构变化时 |
| EXAMPLES.md | 代码示例、API用法 | 新增 API 或用法时 |
| SKILL_MEMORY.md | 硬性规则、常见陷阱 | 发现新约束时 |
| ITERATION_GUIDE.md | 迭代触发条件 | Skill 定位变化时 |

---

## 自我进化

### Trace 自动采集

Hook 脚本在每次文件编辑和 Agent 结束时自动运行，零 token 消耗：

```
Agent 编辑 .cs 文件
  -> trace-collector.py 记录到 buffer（过滤 .meta/.asset 等）
Agent 结束
  -> trace-flush.py 汇总 buffer，推断模块，写入 trace.md
AI 补充语义
  -> 替换 type/correction/skills 占位符
```

**准入条件**：修改的 .cs 文件 >= 2 个才会记录 trace，排除琐碎的单文件修改。

### 跨平台 Hook 支持

同一套 Python 脚本，两份平台配置：

| 平台 | 配置文件 | 文件编辑事件 | Agent 结束事件 |
|------|---------|------------|--------------|
| Cursor | `.cursor/hooks.json` | afterFileEdit | stop |
| Claude Code | `.claude/settings.json` | PostToolUse(Write) | Stop |

脚本通过 stdin JSON 交互，自动处理两个平台的字段差异。

### 触发分析

当 trace 积累到阈值（10 条 pending 或 3 条含用户纠正），AI 会在会话开始时提醒：

```
origin evolve
```

origin-evolve 按四维分类聚合分析，生成结构化提议，用户逐个审批后写入对应文件。

### 进化循环

```
使用（带着现有知识工作）
  -> Hook 自动采集 trace（零 token）
    -> AI 补充语义分类（少量 token）
      -> 阈值提醒 origin evolve
        -> 分类聚合分析，生成提议
          -> 用户审批，写入知识体系
            -> 使用（带着新知识工作）
```

---

## 框架升级

```bash
# 更新 CostFlow 源码
cd CostFlow && git pull  # 或 git submodule update --remote
```

然后在 AI 助手中输入：

```
bootstrap castflow
```

AI 会同步核心文件到 `.claude/`，不覆盖项目专属文件。已有 CLAUDE.md 按语义去重策略合并。

---

## 文件归属

| 分类 | 谁管理 | 如何更新 |
|------|--------|---------|
| `CostFlow/` 所有文件 | CostFlow 仓库 | `git pull` / `git submodule update` |
| `CLAUDE.md` | 项目团队 | 直接编辑（框架段由 bootstrap 管理） |
| `.claude/skills/` 项目 Skill | 项目团队 + 进化系统 | 直接编辑、AI 生成、evolve 追加 |
| `.claude/hooks/` | CostFlow 框架 | bootstrap 生成，脚本可自定义 |
| `.claude/traces/` | Hook 自动生成 | 不手动编辑 |
| `.claude/rules/` | 进化系统 | evolve 提议，用户审批后生成 |

**原则**：不要手动编辑 `CostFlow/.castflow/` 里的文件（会被更新覆盖）。所有定制都在 `.claude/` 和 `CLAUDE.md` 中进行。

---

## 技术细节

### CostFlow 目录结构

```
CostFlow/
  .castflow/
    bootstrap.py                        # 确定性文件生成器（Python 3.6+）
    core/                               # 核心文件
      SKILL_RULE.md                     #   Skill 四文件结构规范
      GLOBAL_SKILL_MEMORY.md            #   运行时核心协议
      agents/                           #   核心 Agent
      skills/
        code-pipeline-skill/            #   工作流编排
        skill-creator/                  #   Skill 创建/迭代工具
        bootstrap-skill/                #   初始化流程定义
        origin-evolve/                  #   自我进化
    scripts/
      pipeline_merge.py                 #   Pipeline Step 3 并行输出汇总
    templates/                          #   生成模板（含占位符和条件段）
  README.md
  LICENSE
```

### bootstrap.py

AI 在初始化过程中生成中间产物（`bootstrap-output/manifest.json` + `content/`），然后调用 bootstrap.py 确定性执行文件生成。

```bash
python CostFlow/.castflow/bootstrap.py                      # 执行全量生成
python CostFlow/.castflow/bootstrap.py --dry-run             # 预览操作
python CostFlow/.castflow/bootstrap.py --validate            # 验证 .claude/ 规范
python CostFlow/.castflow/bootstrap.py --skill core          # 同步核心文件
python CostFlow/.castflow/bootstrap.py --skill claude        # 生成/合并 CLAUDE.md
python CostFlow/.castflow/bootstrap.py --skill architect     # 增量生成单个 skill
python CostFlow/.castflow/bootstrap.py --project-root /path  # 显式指定项目根目录
```

**项目根目录检测**：bootstrap.py 从脚本位置向上查找 `.claude/` 目录。首次初始化时 `.claude/` 不存在，会在 CostFlow 的父目录自动创建。也可通过 `--project-root` 显式指定。

### CLAUDE.md 合并策略

当项目已有 CLAUDE.md 时，bootstrap 会按以下策略处理：

- **有 boundary marker**：框架段更新，项目段保留
- **无 boundary marker**（首次迁移）：按 `## ` 标题拆分为节，逐节语义去重（SequenceMatcher > 50% 判为重复），仅保留真正独有的内容追加到项目段
- 所有场景都会创建备份

### Hook 脚本协议

两个平台的 Hook 脚本协议一致（stdin 读 JSON，stdout 写 JSON），通过同一套 Python 脚本适配：

- `trace-collector.py`：过滤 `.cs` 文件，去重后追加到 `.trace_buffer`
- `trace-flush.py`：从路径推断 modules，生成含分类占位符的 trace 条目，准入过滤后写入 `trace.md`

脚本使用 Python 3.6+ 标准库，零外部依赖。
