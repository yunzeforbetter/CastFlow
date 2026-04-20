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
  CLAUDE.md                             # 项目全局规则（框架段 + 项目段）
  .claude/
    skills/                             # Skill 文件（core 同步 + 项目按需生成）
      SKILL_ITERATION.md                #   Skill 四文件格式规范
      GLOBAL_SKILL_MEMORY.md            #   运行时核心协议
      code-pipeline-skill/              #   核心 skill：多模块协作工序
      skill-creator/                    #   核心 skill：Skill 生成工具
      origin-evolve/                    #   核心 skill：自我进化引擎
      <项目生成>/                        #   bootstrap 生成的项目级 skill
      programmer-<模块>-skill/           #   日常按需生成的模块 skill
    hooks/                              # trace 采集脚本
      trace-collector.py                #   编辑事件采集 + 修正检测
      trace-flush.py                    #   五维评分 + trace 生成 + compaction
    agents/                             # code-pipeline 调用的分析 agent
      requirement-analysis-agent.md
      integration-matching-agent.md
      pipeline-verify-agent.md
    templates/                          # Skill / Agent / CLAUDE 生成模板
      CLAUDE.template.md
      agents/programmer.template.md
      skills/{programmer,architect,debug,profiler}.template/
    scripts/                            # 框架工具脚本
      pipeline_merge.py                 #   pipeline Step 3 输出聚合
    traces/                             # 执行记录（建议 gitignore）
      trace.md                          #   trace 条目累积（Hook 写入）
      weights.json                      #   评分模型自校准结果（运行时生成）
      limits.json                       #   compaction 阈值（可选覆盖默认值）
      limits.README.md                  #   阈值字段说明
    rules/                              # 进化系统生成的跨模块规则
    settings.json                       # Claude Code hook 配置（增量合并）
  .cursor/
    hooks.json                          # Cursor hook 配置（增量合并）
  CastFlow/                             # 框架源码（进入休眠，仅通过 git pull 更新）
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

### Skill 迭代（冷启动后）

bootstrap 只生成**项目级** Skill（分层架构、全局规则、核心工作流）。模块级和专项 Skill 在日常使用中**按需增量创建**，交互流程与 `skill-creator` 完全一致：你只需用自然语言说"为 X 生成 skill"，AI 会自动完成代码扫描、信息提炼、四文件生成。**这是项目知识体系持续扩张的主要渠道**。

#### 触发方式

```
为建筑系统生成 skill
分析 Assets/Scripts/NPC/ 目录，为这个模块生成 skill
为项目里的网络协议层创建一个 skill
帮我创建一个安全审查的 skill
针对 UI 性能优化场景做一个 skill
```

以上任何一种表述都会激活 `skill-creator`，不需要记忆特殊命令。Skill 存放位置统一为 `.claude/skills/<skill-name>/`。

#### 两类 Skill，两条路径

| 类型 | 示例 | 模板 | 内容来源 |
|------|------|------|---------|
| 功能模块 Skill | `programmer-building-skill`、`programmer-npc-skill` | `.claude/templates/programmer.template/` | 扫描模块真实代码 |
| 专项职责 Skill | `security-review`、`ui-perf-checker` | 无模板，按 `SKILL_ITERATION.md` 规范 | 用户描述 + AI 参考资料 |

功能模块 Skill 使用模板填充，结构统一、命名规范；专项职责 Skill 由 AI 按规范直接创建四文件，灵活度更高。两者都在 `.claude/` 内部完成闭环，不依赖 `CastFlow/` 源码目录。

#### AI 执行流程（对齐 skill-creator）

以"为建筑系统生成 skill"为例：

```
1. 意图确认  -- AI 询问：目标目录？关键接口？Skill 触发词？预期输出形式？
2. 代码扫描  -- 并行 grep/read 模块真实文件，提取接口、数据模型、常用 API、陷阱样本
3. 模板填充  -- 复制 programmer.template，替换占位符，生成四文件草案
4. 用户审阅  -- 展示 SKILL.md 大纲和关键规则，用户确认或要求调整
5. 写入      -- .claude/skills/programmer-<module>-skill/{SKILL,EXAMPLES,SKILL_MEMORY,ITERATION_GUIDE}.md
6. 验证      -- python CastFlow/.castflow/bootstrap.py --validate 检查格式合规
```

关键约束（来自 `SKILL_ITERATION.md` 和 `CLAUDE.md` 的 P0 规则）：

- 所有 API、类名、符号必须从真实代码提取，**禁止幻觉**
- `SKILL_MEMORY.md` 的硬性规则必须带 `Anchors:` 字段列出代码符号（origin-evolve 用它做锚点验证和 Retire 判断）
- 四文件各司其职，不重复承载内容（渐进式信息披露）
- 无 emoji、无日期、无版本号（SKILL_ITERATION 硬性约束）

#### 与自我进化的关系

Skill 体系通过**两个互补渠道**持续演进：

| 渠道 | 做什么 | 何时触发 | 粒度 |
|------|-------|---------|------|
| 人工创建 (skill-creator) | 从零生成整个 Skill | 新模块、新职责出现时 | 文件级 |
| 自我进化 (origin-evolve) | 在已有 Skill 上追加/合并/退休**规则** | 日常累积 trace 达到阈值时 | 规则级 |

skill-creator 建骨架，origin-evolve 丰血肉。新模块进场用前者快速覆盖，长期使用中出现的微观规则由后者从真实 trace 中提炼。两者共享同一套文件格式和 Anchors 机制。

---

## 自我进化

### 数据采集

两层协作，分工明确：

| 层 | 谁采集 | 采集什么 | 成本 |
|----|--------|---------|------|
| Hook 脚本 | 自动（每次编辑 + 会话结束） | 文件路径、行数、编辑次数、修正检测 | 零 token |
| AI 规则 | 任务结束时 | 任务类型（type）、使用的 Skill（skills） | 少量 token |

```
编辑代码文件 -> collector 记录路径/行数/编辑次数/修正标记 -> buffer
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
validated: _                       <- flush 注入 / pipeline 结果
pipeline_run_id: _                 <- code_pipeline 运行时自动填充
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
| `expired` | 验证窗口已过期 | origin-evolve Step 0 |
| `invalid` | pipeline 已放弃 | origin-evolve Step 0 |

**validated** — 用户验证信号（影响 evolve 优先级和 compaction 保护）：

| 值 | 含义 | 来源 |
|---|------|------|
| `_` | 未验证 | 默认 |
| `true` | 用户接受 | flush 注入 |
| `false` | 用户拒绝（P0 优先） | flush 注入 |
| `pending-pipeline` | 等待 pipeline 结果 | code_pipeline 驱动时自动设置 |
| `invalid` | pipeline 已放弃 | 过期转换 |

**correction** — 修正信号：

| 值 | 含义 | 来源 |
|---|------|------|
| `_` | 无修正 | Hook 默认 |
| `auto:minor` | 1-2 次 AI 自我修正 | collector 自动检测 |
| `auto:major` | 3+ 次 AI 自我修正 | collector 自动检测 |
| `minor` / `major` | 人工标记 | AI 补充或用户指定 |

### Trace Compaction

随着持续使用，`trace.md` 会不断增长。flush 内置四级自动压缩机制：

| 级别 | 触发条件 | 策略 | 保护 |
|------|---------|------|------|
| Level 0 | 每次 flush | 清理过期的 `PROCESSED` / `COMPACTED` 审计行 | -- |
| Level 1 | entries > compact_max_entries | 移除超过 `entry_expire_days` 的低分条目 | validated 条目不移除 |
| Level 2 | Level 1 后仍超标 | 移除超过 `level2_age_days` 且 score < `level2_score_threshold` 的条目 | validated 条目不移除 |
| Level 3 | Level 2 后仍超标 | 移除所有 score < `level3_score_threshold` 的条目 | 每模块保留 top N（`keep_top_n_per_module`） |

阈值可通过 `traces/limits.json` 配置。validated 条目（`true` / `false` / `pending-pipeline`）在 Level 1-3 中均受保护不被移除——这些条目携带用户反馈信号，是进化系统最有价值的数据。

### 进化触发与执行

evolve-reminder 规则在每次新会话开始时静默检查 `trace.md`：

| 条件 | 阈值 | 原因 |
|------|------|------|
| pending 条目数 | >= 5 | 普通 trace 需要足够样本量 |
| 含修正信号的条目数 | >= 3 | 修正记录信息密度极高，3 条即可形成模式 |

满足任一条件时提醒用户运行 `origin evolve`。origin-evolve 永远不会自动执行。

**origin-evolve 执行步骤**：

1. 读取 pending 条目，按 correction > score > edit_count 排序
2. 六类模式识别：修正模式 / 模块热点 / 知识缺口 / 复杂度集中 / 语义漂移 / IDP 缺失
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
  README.md                               # 本文件
  CHANGELOG.md                            # 版本变更记录
  LICENSE                                 # 开源协议
  .castflow/                              # 框架源码（初始化后休眠，按 CORE_DIR_COPIES 同步到 .claude/）
    bootstrap.py                          #   确定性文件生成器（Python 3.6+，零依赖）
    core/
      GLOBAL_SKILL_MEMORY.md              #     运行时核心协议（所有 skill 共享）
      SKILL_ITERATION.md                  #     Skill 四文件格式规范 + 迭代规则
      agents/                             #     code-pipeline 使用的分析型 agent（3 个）
      hooks/                              #     trace 采集生产脚本（2 个）
      skills/                             #     核心 skill（4 个：bootstrap / code-pipeline / origin-evolve / skill-creator）
      traces/                             #     默认阈值配置（limits.json + 说明文档）
    scripts/                              #   框架工具脚本
    templates/                            #   Skill/Agent/CLAUDE 生成模板（bootstrap 拷贝后供 skill-creator 使用）
  test/                                   # 测试套件（与 .castflow/ 同级，不被 bootstrap 分发）
    hooks/                                #   trace 流水线测试（134 tests）
    origin-evolve/                        #   origin-evolve 规范暴力验证
```

### 文件清单

下面按目录逐一说明每个文件的职责。

#### 根目录

| 文件 | 职责 |
|------|------|
| `README.md` | 框架使用文档（本文件） |
| `CHANGELOG.md` | 按版本记录功能变更和修复 |
| `LICENSE` | 开源协议 |

#### `.castflow/bootstrap.py`

确定性文件生成器。单文件 Python 3.6+ 脚本，零外部依赖。职责：

- 向上查找项目根（识别 `.claude/` 或创建新的）
- 将 `core/` 下指定目录按 `CORE_DIR_COPIES` 复制到 `<项目根>/.claude/`
- 合并 `CLAUDE.md`（有/无 boundary marker 两种策略，自动备份）
- 合并 `settings.json`（Claude Code）和 `hooks.json`（Cursor），保留项目原有 hook
- 支持 `--dry-run` / `--validate` / `--skill <name>` / `--project-root <path>` 等参数

#### `.castflow/core/`

| 文件 | 职责 |
|------|------|
| `GLOBAL_SKILL_MEMORY.md` | 跨 skill 通用规则（API 验证最高优先级、学习→匹配→应用流程、命名规范、`.meta` 管理等） |
| `SKILL_ITERATION.md` | Skill 四文件结构规范（SKILL / EXAMPLES / SKILL_MEMORY / ITERATION_GUIDE 的分工）+ 验收清单 + 硬性约束（无 emoji、无日期、无临时文档） |

#### `.castflow/core/agents/`

code-pipeline 调用的专项分析 agent，每个是一份 prompt 定义。

| 文件 | 职责 |
|------|------|
| `requirement-analysis-agent.md` | Pipeline Step 1：拆分需求、识别功能模块、输出可验证的接口清单 |
| `integration-matching-agent.md` | Pipeline Step 2：检查并行模块间的接口一致性、命名对齐、耦合点 |
| `pipeline-verify-agent.md` | Pipeline 验收阶段：对代码实现做集成一致性和质量复核 |

#### `.castflow/core/hooks/`

生产 hook 脚本，由 Cursor / Claude Code 在编辑事件和会话结束时通过 stdin JSON 触发。

| 文件 | 职责 |
|------|------|
| `trace-collector.py` | 每次文件编辑被调用：记录路径、行数、编辑次数，保存 new_string 快照，通过相似度对比检测 AI 自我修正 |
| `trace-flush.py` | 会话结束被调用：读取 buffer，执行五维评分（F/D/K/S/E），达标则写入 `trace.md`；同时执行四级 compaction、审计行清理、被动通知检查 |

#### `.castflow/core/skills/`

4 个核心 skill。每个都是 `SKILL.md` + `EXAMPLES.md` + `SKILL_MEMORY.md` + `ITERATION_GUIDE.md` 四文件结构（详见 `SKILL_ITERATION.md`）。

| Skill | 职责 | 附加资源 |
|-------|------|---------|
| `bootstrap-skill/` | 框架初始化器。`bootstrap castflow` 的行为定义：扫描项目、确认 skill、并行分析代码、生成文件、验证 | -- |
| `code-pipeline-skill/` | 多模块协作工序。从需求分析到验收交付的 Step 1-9 标准流程 | `config/pipeline_protocol.md`（Pipeline 协议）、`config/defaults.json`、`config/params.schema.json` |
| `origin-evolve/` | 自我进化引擎。读取 trace、识别模式、生成知识改动提议（Append / Merge / Retire） | -- |
| `skill-creator/` | Skill 生成和迭代工具。日常用户创建新 skill 的标准入口 | `agents/{analyzer,comparator,grader}.md`、`scripts/*.py`（eval 运行、benchmark 聚合、skill 打包、描述优化等 7 个工具脚本）、`eval-viewer/`、`references/schemas.md`、`assets/` |

#### `.castflow/core/traces/`

| 文件 | 职责 |
|------|------|
| `limits.json` | trace-flush 的 compaction 阈值、过期天数、评分保护参数等运行时默认值 |
| `limits.README.md` | 每个字段的含义与调参建议 |

#### `.castflow/scripts/`

| 文件 | 职责 |
|------|------|
| `pipeline_merge.py` | code-pipeline Step 3 调用：聚合多个并行 agent 的输出到 `PIPELINE_CONTEXT.md`，保留原始详情文件供后续步骤按需读取 |

#### `.castflow/templates/`

bootstrap 将模板同步到 `.claude/templates/`，供 skill-creator 生成模块 skill 时复制填充。

| 模板 | 用途 |
|------|------|
| `CLAUDE.template.md` | 项目根 `CLAUDE.md` 的框架段模板（bootstrap 首次生成时使用） |
| `agents/programmer.template.md` | 为功能模块生成专属 programmer agent 时的模板 |
| `skills/programmer.template/` | 功能模块 skill 模板（最常用）。四文件占位符，skill-creator 扫描模块代码后填充 |
| `skills/architect.template/` | 架构层 skill 模板（分层约束、设计模式） |
| `skills/debug.template/` | 调试检查清单 skill 模板（边界条件、资源泄漏） |
| `skills/profiler.template/` | 性能检查 skill 模板（性能红线、Profiler 指引） |

每个 skill 模板都包含 `SKILL.template.md` / `EXAMPLES.template.md` / `SKILL_MEMORY.template.md` / `ITERATION_GUIDE.template.md` 四个占位文件。

#### `test/` — 测试套件

详见[测试套件](#测试套件)章节。不被 bootstrap.py 分发，仅用于 CastFlow 框架自身的回归验证。

| 文件 | 覆盖范围 |
|------|---------|
| `test/hooks/test_evolution.py` | collector 采集 / buffer 格式 / flush 评分 / compaction 四级策略 / validated 保护 / 审计行过期 / 空行清理 / 被动通知（84 tests） |
| `test/hooks/test_100day_simulation.py` | 100 天持续 append + compact 的有界性、模块多样性、混合会话类型（27 tests） |
| `test/hooks/test_365day_simulation.py` | 365 天生产模拟：工作日/周末差异、季度焦点漂移、知识库生命周期、Step 0 状态过期转换（23 tests） |
| `test/origin-evolve/verify_redesign.py` | origin-evolve 规范确定性部分的暴力验证：诊断计数、归因决策树、Append/Merge/Retire 分支、Jaccard 边界、容量策略（~7000 次断言） |

### bootstrap.py

```bash
python CastFlow/.castflow/bootstrap.py                      # 全量生成
python CastFlow/.castflow/bootstrap.py --dry-run             # 预览
python CastFlow/.castflow/bootstrap.py --validate            # 验证规范
python CastFlow/.castflow/bootstrap.py --skill architect     # 增量生成单个 skill
python CastFlow/.castflow/bootstrap.py --project-root /path  # 指定项目根
```

项目根目录检测：从脚本位置向上查找 `.claude/`，首次初始化自动创建。

### 测试套件

所有测试集中存放于 `CastFlow/test/`（与 `.castflow/` 同级），**不会被 `bootstrap.py` 分发到用户项目**。零外部依赖（仅 Python 标准库 `unittest`）。每次运行在临时目录中创建隔离环境，不影响项目数据。

```bash
cd CastFlow/test/hooks

# Windows（使用 py launcher）
py test_evolution.py                            # 运行并丢弃数据
py test_evolution.py --keep-data               # 运行并保留数据到 test-output/evolution/
py test_100day_simulation.py --keep-data       # 运行并保留数据到 test-output/100day/
py test_365day_simulation.py --keep-data       # 运行并保留数据到 test-output/365day/
py -m unittest discover -s . -p "test_*.py"   # 运行全部 134 tests

# origin-evolve 规范暴力验证（确定性部分）
cd ../origin-evolve
py verify_redesign.py                           # ~7000 次断言，~1 秒

# macOS / Linux（将 py 替换为 python3）
python3 test_365day_simulation.py --keep-data
```

`--keep-data` 说明：
- 每次运行前**自动清理**上次保留的数据
- 每个测试用例的数据保存到 `test-output/{suite}/{TestClass}__{test_name}/traces/`，包含 `trace.md`、`limits.json` 等完整文件
- 不影响项目的真实 `.claude/traces/` 数据

| 测试套件 | 覆盖范围 |
|---------|---------|
| `test_evolution.py` | collector 采集、buffer 格式、flush 评分、compaction 四级策略、validated 保护、审计行过期、空行清理、被动通知 |
| `test_100day_simulation.py` | 持续 append + compact 有界性、模块多样性保留、混合会话类型（chat / pipeline / Q&A） |
| `test_365day_simulation.py` | 工作日/周末活跃度差异、季度模块焦点漂移、知识库生命周期（规则提取 / 合并 / 退休 / 拒绝记忆）、Step 0 状态过期转换 |

**测试范围说明**：测试验证的是**数据管道的机械正确性**，确保 trace 数据在长期持续写入和压缩下不会损坏、不会无限膨胀、不会丢失关键信号。

| 层级 | 是否覆盖 | 说明 |
|------|---------|------|
| Python 函数正确性 | 是 | 评分公式、compaction 逻辑、状态转换等核心函数均直接调用真实代码 |
| 数据格式与流转 | 是 | trace 条目的写入、读取、解析、压缩全链路使用真实 `trace.md` 文件 |
| Hook 事件触发 | 否 | 平台（Cursor / Claude Code）通过 stdin JSON 触发 Hook，测试中直接调用函数替代 |
| origin-evolve AI 分析 | 否 | 模式识别、提议生成、写入 Skill 是 AI 行为，模拟测试中使用简化的模式检测函数替代 |
| 用户审批交互 | 否 | 人在回路的审批环节无法自动化测试 |

### CLAUDE.md 合并策略

- **有 boundary marker**：框架段更新，项目段保留
- **无 boundary marker**：按 `## ` 标题逐节语义去重（>50% 相似判为重复），仅追加独有内容
- 所有场景创建备份

### 备份与回滚

每次 `bootstrap.py` 在 `merge_mode: full` 下覆盖任何已有文件前，会把原件复制到**集中会话目录**：

```
.claude/.backups/<YYYY-MM-DD_HH-MM-SS>/
    .claude/
        agents/requirement-analysis-agent.md
        skills/code-pipeline-skill/...
        ...
```

备份保留原始的相对路径结构，回滚时可直接 `robocopy`/`rsync` 拷回。

**轮换策略**：默认保留最近 3 次会话，更早的自动删除。

**相关 CLI 选项**：

| 选项 | 作用 |
|------|------|
| `--no-backup` | 跳过备份（git 用户） |
| `--backup-keep N` | 保留最近 N 次（默认 3） |
| `--clean-backups` | 删除所有备份会话并退出 |

**自动行为**：
- 首次使用新版 bootstrap 会**一次性清理**旧版散落的 `.bak` 文件/目录
- 自动向 `.claude/.gitignore` 追加 `.backups/` 条目（若缺失），防止误提交
