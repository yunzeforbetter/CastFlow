# CastFlow

一套可移植的 AI 辅助开发框架。从项目代码中提取架构知识，生成结构化的 Skill 体系，并通过 Hook 自动采集执行数据驱动知识进化，让 AI 助手从第一天就深度理解你的项目，且越用越好。

---

## 解决什么问题

AI 助手在大型项目中常见的四个问题：

**1. 架构遗忘** -- AI 不了解项目的分层架构、通信方式、设计模式，生成的代码风格不一致、架构不合规。

**2. API 幻觉** -- AI 猜测 API 的存在和用法，生成的代码调用了不存在的方法，编译不通过。

**3. 知识碎片化** -- 项目规则散落在口头约定、代码注释、文档角落中。不同 AI 会话之间无法共享上下文，同一个错误反复出现。

**4. 经验不积累** -- AI 在上一次犯过的错不会被记住，下一次还会犯。团队的纠正和反馈没有沉淀。

CastFlow 的解决方式：

- **冷启动**：从项目真实代码中提取架构知识，生成结构化的 Skill 文件，让 AI 在首次会话就能加载正确的上下文。
- **自我进化**：通过 Hook 自动采集执行 trace（零 token），五维评分模型智能筛选，origin-evolve 聚合分析并提议改进，形成闭环。

---

## 核心设计

### 冷启动

**安装即走**：通过 bootstrap 扫描项目结构，自动生成 Skill、Agent 和项目规则到 `.claude/` 目录。初始化完成后，项目由 `.claude/` 驱动，CastFlow 进入休眠。

**真实代码驱动**：所有 Skill 内容（架构规则、代码示例、常见陷阱）都从项目实际代码中扫描提取，不是空模板。

**跨平台**：支持 Cursor 和 Claude Code。bootstrap.py 自动检测项目根目录，支持 CastFlow 作为子目录或 submodule 引入。

### 渐进式信息披露

每个 Skill 采用四文件结构，AI 按需加载：

| 文件 | 何时加载 | 内容 |
|------|---------|------|
| SKILL.md | 首次接触该模块 | 架构概览、快速查询表 |
| EXAMPLES.md | 需要写代码时 | 真实代码示例、API 用法 |
| SKILL_MEMORY.md | 生成代码前 | 硬性规则、常见陷阱 |
| ITERATION_GUIDE.md | 迭代 Skill 时 | 修改规则、文件职责 |

### 自我进化

不是简单的日志记录，而是一套从信号采集到知识写入的完整闭环：Hook 自动采集编辑行为 -> 五维评分筛选有价值的会话 -> origin-evolve 识别模式并提议改进 -> 用户审批后写入知识体系 -> 评分模型自校准。详见[自我进化](#自我进化-1)章节。

### 职责分层

| 层级 | 文件 | 管什么 |
|------|------|--------|
| 工作流 | CLAUDE.md | API 验证流程、Skill 使用规范、执行记录规则 |
| 架构 | architect-skill | 分层架构、设计模式、约束规则 |
| 质量 | debug-skill / profiler-skill | 边界检查、性能红线 |
| 模块 | programmer-*-skill | 模块级 API、规则、陷阱 |
| 编排 | code-pipeline-skill | 多模块协作时的工序流转 |
| 进化 | origin-evolve + hooks | 执行记录采集、评分、分析、经验提炼 |

---

## 安装与初始化

### 引入框架

```bash
# 方式 1：git submodule
git submodule add <castflow仓库地址> CastFlow

# 方式 2：直接克隆
git clone <castflow仓库地址> CastFlow
```

CastFlow 放在任意子目录均可。bootstrap.py 会自动向上查找项目根目录。

### 初始化

在 AI 助手中输入：

```
bootstrap castflow
```

AI 自动完成：扫描项目 -> 逐个确认 Skill -> 并行分析代码 -> 生成框架文件 -> 配置 Hooks。

### 初始化后的文件结构

```
项目根目录/
  CLAUDE.md                             # 项目全局规则
  .claude/
    skills/                             # Skill 文件（core + 项目生成）
      SKILL_ITERATION.md               #   Skill 创建与迭代规范
      GLOBAL_SKILL_MEMORY.md            #   运行时核心协议
    hooks/                              # trace 采集脚本
      trace-collector.py
      trace-flush.py
    templates/                          # Skill 生成模板（创建模块 Skill 时使用）
      programmer.template/
    agents/                             # Agent 定义
    traces/                             # 执行记录（gitignore）
      trace.md                          #   trace 条目累积
      weights.json                      #   评分模型自校准（运行时生成）
    settings.json                       # Claude Code hook 配置
    rules/                              # 进化系统生成的规则
  .cursor/
    hooks.json                          # Cursor hook 配置
  CastFlow/                             # 框架源码（进入休眠）
```

---

## 日常使用

### 直接使用 Skill

```
帮我在建筑系统里加一个批量升级功能

用 debug-skill 检查这段代码的边界条件
```

### 使用 Code Pipeline

```
code_pipeline 实现用户交易系统
```

Pipeline 提供从需求拆分到验收交付的标准化工序（Step 1-9）。

### 创建 Skill

初始化只生成项目级 Skill。模块和通用 Skill 按需创建：

```
为建筑系统生成 skill                     # 功能模块 -> 使用 programmer 模板
分析 Assets/Scripts/NPC/ 目录，生成模块 skill  # 功能模块 -> 使用 programmer 模板
帮我创建一个安全审查的 skill               # 通用职责 -> 不使用模板，AI 按规范直接创建
```

功能模块 Skill 使用 `.claude/templates/programmer.template/` 模板，在 `.claude/` 内部完成闭环，不依赖 CastFlow 目录。通用职责 Skill 由 AI 按 SKILL_ITERATION.md 规范直接创建四文件。

---

## 自我进化

### 数据采集

两层协作，分工明确：

| 层 | 谁采集 | 采集什么 | 成本 |
|----|--------|---------|------|
| Hook 脚本 | 自动（每次编辑 + 会话结束） | 文件路径、行数、编辑次数、修正检测 | 零 token |
| AI 规则 | 任务结束时 | 任务类型（type）、使用的 Skill（skills） | 少量 token |

```
编辑 .cs 文件 -> collector 记录路径/行数/编辑次数/修正标记 -> buffer
会话结束     -> flush 读取 buffer，五维评分，达标则写入 trace.md
AI 补充      -> 替换 type/skills 占位符
```

同一套 Python 脚本（零外部依赖），通过 stdin JSON 适配两个平台：

| 平台 | 配置文件 | 编辑事件 | 结束事件 |
|------|---------|---------|---------|
| Cursor | `.cursor/hooks.json` | afterFileEdit | stop |
| Claude Code | `.claude/settings.json` | PostToolUse(Write) | Stop |

bootstrap 会自动将 trace hook 增量合并到已有配置中，不覆盖项目原有的其他 hook。

### 五维评分模型

评分模型是进化系统的核心引擎，决定哪些会话值得被记录和分析。

```
score = F * 1.0 + D * 0.5 + K * 1.5 + S * 0.5 + E * 0.8

准入阈值: score >= 1.5    理论范围: 0 ~ 4.3
```

| 维度 | 含义 | 计算 | 为什么重要 |
|------|------|------|-----------|
| F (File Count) | 修改文件数 | min(files / 3, 1.0) | 多文件修改 = 更高的记录价值 |
| D (Module Spread) | 模块分散度 | min(modules / 2, 1.0) | 跨模块操作往往涉及架构决策 |
| K (Critical Path) | 关键路径等级 | 三档分级（见下） | 架构影响力梯度 |
| S (Change Scale) | 改动规模 | min(lines / 50, 1.0) | 大规模改动更可能有价值 |
| E (Edit Intensity) | 编辑密度 | min(edits / 5, 1.0) | 反复修改 = 困难迭代，最值得记录 |

**K 维度三档分级**：

| 等级 | 匹配模式 | k 值 | 典型文件 |
|------|---------|------|---------|
| 接口 | `I[A-Z].*Manager.cs` 等 | 1.0 | IBuildingManager.cs |
| 实现 | `*Manager.cs`, `*Handler.cs`, `*Controller.cs` 等 | 0.6 | BuildingManager.cs |
| 基础 | `*Base.cs` | 0.3 | ManagerBase.cs |

**设计原则**：各维度独立饱和（`min(raw/threshold, 1.0)`），避免单一极端值主导。E 维度区分"1 个文件改 15 次"（困难调试，值得记录）和"15 个文件各改 1 次"（批量操作，价值较低）。

**典型场景**：

| 场景 | 总分 | 结果 |
|------|------|------|
| 1 Manager, 8 edits, 5 lines | 2.33 | 录入 |
| IBuildingManager 重构 | 2.92 | 录入 |
| 1 Data 文件 debug 改 15 次 | 1.88 | 录入 |
| 新功能 4 文件跨 2 模块 | 3.70 | 录入 |
| Typo 修复 1 config 1 line | 0.75 | 拒绝 |
| 单 Panel 改 1 行 | 0.75 | 拒绝 |

### 自动修正检测

collector 在每次编辑时保存 new_string 快照。下一次编辑同一文件时，如果 old_string 与上次的 new_string 高度相似（>60%），判定为 AI 在修正自己的输出，标记 `R` 标志。flush 汇总后自动填充 correction 字段。

这是进化系统最有价值的信号——AI 犯错并自我修正的地方，恰恰是知识体系最需要补充规则的地方。

### Trace 条目与状态机

每条 trace 由 Hook 自动生成：

```
<!-- TRACE status:pending -->
timestamp: 2026-04-13T10:00:00Z
type: _                            <- AI 补充
correction: auto:minor             <- Hook 自动检测
modules: [Building, Queue]         <- Hook 从路径推断
skills: []                         <- AI 补充
files_modified: [...]
file_count: 3
lines_changed: 80
edit_count: 12
score: 3.50
<!-- /TRACE -->
```

**status** — 分析状态流转：

| 状态 | 含义 | 谁设置 |
|------|------|--------|
| `pending` | 等待 origin-evolve 分析 | Hook 写入时 |
| `processed` | 已分析完毕 | origin-evolve 标记 |

**correction** — 修正信号：

| 值 | 含义 | 来源 |
|---|------|------|
| `_` | 无修正 | Hook 默认 |
| `auto:minor` | 1-2 次 AI 自我修正 | collector 自动检测 |
| `auto:major` | 3+ 次 AI 自我修正 | collector 自动检测 |
| `minor` / `major` | 人工标记 | AI 补充或用户指定 |

### 进化触发与执行

evolve-reminder 规则在每次新会话开始时静默检查 `trace.md`：

| 条件 | 阈值 | 原因 |
|------|------|------|
| pending 条目数 | >= 10 | 普通 trace 需要足够样本量 |
| 含修正信号的条目数 | >= 3 | 修正记录信息密度极高，3 条即可形成模式 |

满足任一条件时提醒用户运行 `origin evolve`。origin-evolve 永远不会自动执行。

**origin-evolve 执行步骤**：

1. 读取 pending 条目，按 correction > score > edit_count 排序
2. 四维模式识别：修正模式 / 模块热点 / 知识缺口 / 复杂度集中
3. 生成提议（含写入前治理）：
   - 归属决策（决策树确定目标 Skill 和目标文件）
   - 操作类型（Append / Merge / Retire）
   - 容量检查（超标则先 Retire 腾空间）
   - 锚点验证（grep 代码检查 Anchors 是否存在）
4. 用户逐个审批，批准则执行写入，拒绝则记录避免重复
5. 标记 `status:processed`
6. 可选：校准 `weights.json`

**知识生命周期**：进化不是单纯追加数据。每条规则携带 Anchors（代码符号锚点）和 Related（关联引用），支持三种操作：

| 操作 | 条件 | 效果 |
|------|------|------|
| Append | 新模式，无语义重叠 | 追加新条目 |
| Merge | 新模式与已有条目锚点重叠 | 合并扩展已有条目（展示 diff） |
| Retire | Anchors 中的代码符号已不存在 | 标记 `[RETIRED]`，AI 跳过但内容保留 |

### 自校准反馈闭环

评分模型的权重和阈值存储在 `traces/weights.json`（首次使用无需此文件，自动回退默认值）。origin-evolve 在 Step 6 中可微调：

- 对比有效 trace 和无效 trace 的各维度分布差异
- 某维度在有效 trace 中偏高 -> 权重 +5~10%
- 准入率偏高/偏低 -> 调整 threshold
- 单次幅度不超过 10%，权重范围 0.2~3.0，阈值范围 1.0~3.0

随着项目使用积累，权重逐渐收敛到最优。

**完整生命周期**：

```
编辑文件 -> collector 采集 -> buffer
                                |
会话结束 -> flush 五维评分 -> trace.md (pending)
                                |
新会话 -> evolve-reminder 检查 -> 达标则提醒
                                |
用户执行 origin evolve -> 模式识别 -> 提议 -> 审批 -> 写入 Skill
                                                         |
                                            校准 weights.json (可选)
                                                         |
                                    下次会话: 新知识 + 优化后的评分模型
```

---

## 框架升级

```bash
cd CastFlow && git pull  # 或 git submodule update --remote
```

然后在 AI 助手中输入 `bootstrap castflow`。核心文件同步到 `.claude/`，不覆盖项目专属文件。

---

## 文件归属

| 分类 | 谁管理 | 如何更新 |
|------|--------|---------|
| `CastFlow/` | CastFlow 仓库 | `git pull` |
| `CLAUDE.md` | 项目团队 | 直接编辑（框架段由 bootstrap 管理） |
| `.claude/skills/` | 项目团队 + 进化系统 | 直接编辑、AI 生成、evolve 追加 |
| `.claude/hooks/` | CastFlow 框架 | bootstrap 生成 |
| `.claude/traces/` | Hook + evolve | 不手动编辑 |
| `.claude/rules/` | 进化系统 | evolve 提议，用户审批后生成 |

不要手动编辑 `CastFlow/.castflow/` 里的文件（会被更新覆盖）。所有定制在 `.claude/` 和 `CLAUDE.md` 中进行。

---

## 技术细节

### CastFlow 目录结构

```
CastFlow/
  .castflow/
    bootstrap.py                        # 确定性文件生成器（Python 3.6+）
    core/
      SKILL_ITERATION.md              #   Skill 创建与迭代规范
      GLOBAL_SKILL_MEMORY.md            #   运行时核心协议
      agents/                           #   核心 Agent
      hooks/                            #   trace 采集脚本源码
        trace-collector.py              #     编辑事件采集 + 修正检测
        trace-flush.py                  #     五维评分 + trace 生成
      skills/                           #   核心 Skill
    scripts/                            #   工具脚本
    templates/                          #   生成模板
  README.md
  LICENSE
```

### bootstrap.py

```bash
python CastFlow/.castflow/bootstrap.py                      # 全量生成
python CastFlow/.castflow/bootstrap.py --dry-run             # 预览
python CastFlow/.castflow/bootstrap.py --validate            # 验证规范
python CastFlow/.castflow/bootstrap.py --skill architect     # 增量生成单个 skill
python CastFlow/.castflow/bootstrap.py --project-root /path  # 指定项目根
```

项目根目录检测：从脚本位置向上查找 `.claude/`，首次初始化自动创建。

### CLAUDE.md 合并策略

- **有 boundary marker**：框架段更新，项目段保留
- **无 boundary marker**：按 `## ` 标题逐节语义去重（>50% 相似判为重复），仅追加独有内容
- 所有场景创建备份
