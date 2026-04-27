# CastFlow

> **让 AI 助手从第一天就深度理解你的项目，并且越用越懂。**

CastFlow 是一套可移植、可演进、零成本采集的 **AI 协同开发操作系统**。它把"AI 助手不理解项目"这个行业难题，拆解成 **冷启动装架 → 渐进式信息披露 → 多模块编排 → 自我进化** 四层闭环，全部由项目真实代码驱动，不依赖任何大模型供应商、不占用任何运行时 token。

一次装架，终身进化。

---

## 目录

- [解决什么问题](#解决什么问题)
- [核心设计理念](#核心设计理念)
- [项目结构总览](#项目结构总览)
- [端到端案例：从集成到自主进化](#端到端案例从集成到自主进化)
- [文件清单（每个文件的作用）](#文件清单每个文件的作用)
- [渐进式信息披露（T1-T4）](#渐进式信息披露t1-t4)
- [自我进化详解](#自我进化详解)
- [命令参考](#命令参考)
- [升级与回滚](#升级与回滚)
- [测试套件](#测试套件)

---

## 解决什么问题

AI 助手进入大型项目常见的四种失控：

| 问题 | 症状 | CastFlow 的治法 |
|------|------|----------------|
| 架构遗忘 | 生成的代码风格不一致、越过分层、绕过 Manager | `architect-skill` 从真实代码提取分层规则，T1-PREPARE 时点强制加载 |
| API 幻觉 | 调用了不存在的方法、方法签名错乱、编译不通过 | P0 规则：EXAMPLES.md → 用户指导 → Grep 至少两次真实使用，均未命中则 TODO |
| 知识碎片化 | 规则散落在口头约定、PR 评论、隐藏文档里，跨会话无法共享 | 四件套 Skill（SKILL/EXAMPLES/SKILL_MEMORY/ITERATION_GUIDE），文件即知识 |
| 经验不积累 | 上一次犯过的错，下一次照犯不误 | Hook 零 token 采集编辑 trace → 五维评分筛选 → `origin-evolve-skill` 生成规则提议 → 用户审批写入 Skill |

它是一套 **把项目知识变成可执行、可验证、可迭代的代码资产** 的AI工程框架。

---

## 核心设计理念

### 1. 冷启动即可用：装架与生产解耦

`python .castflow/bootstrap.py` 只做一件事 —— **装架**（Phase A）：把核心协议、元规范、模板、Hook、agent 定义同步到 `.claude/`，生成项目根 `CLAUDE.md`。**不生成任何项目级 Skill 正文**。

项目级 Skill（architect / debug / profiler / programmer-\<模块\>）由 **bootstrap-skill** 作为 AI skill 驱动，经 **子代理并行 + `skill-creator` 主路径** 按需生成。这样：

- 安装器保持确定性（纯 Python，零依赖，可重入，`--dry-run` 可预览）
- 内容生产保持创造性（AI 扫描真实代码，由 `AUTHORING_GUIDE.md` 约束产出质量）
- 两者在 `SKILL_ITERATION.md` 元规范下同频

### 2. 渐进式信息披露：时点驱动加载

Skill 内容不会在每次调用时全量入上下文。按 **T1-PREPARE / T2-EXECUTE / T3-FEEDBACK / T4-MAINTAIN** 四个行为时点分层加载：写代码前读一份、生成中按需补一份、反馈时记一份、迭代 skill 时另读一份。命名与映射的权威源是项目根 `CLAUDE.md`。

### 3. 多模块编排：code-pipeline 工序流

`code_pipeline 实现 X` 触发 9 步标准流水：需求分析 → 集成匹配 → 并行实现 → 验收复核。每个 Step 有专属 agent（`requirement-analysis-agent` / `integration-matching-agent` / `pipeline-verify-agent`），跨模块并行而不丢上下文。

### 4. 自我进化：零 token 采集 + 五维评分 + 人在回路

Hook 每次编辑时自动记录 `path|lines|edits|flags`（修正检测用 `SequenceMatcher.ratio()` 对比前后编辑，相似度 > 60% 打 R 标）。会话结束跑五维评分 `score = F·1.0 + D·0.5 + K·1.5 + S·0.5 + E·0.8`，超过阈值的会话进入 `trace.md`。`origin-evolve-skill` 读 trace、识别六类模式、生成 Append/Merge/Retire 提议，**用户审批后才写入** Skill。评分权重还会根据有效/无效 trace 的维度分布做自校准（`traces/weights.json`）。

整个闭环对用户仅两步：**批准提议** + **运行 `origin evolve`**。

---

## 项目结构总览

```
CastFlow/
├── README.md                              # 本文件
├── CHANGELOG.md                           # 按版本变更记录
├── LICENSE
├── bootstrap-skill/                       # 【顶层 AI skill】框架初始化器，
│   │                                      # 由 "bootstrap castflow" 触发，驱动装架与 project skill 生成
│   ├── SKILL.md                           #   Phase 0-6 工作流、语言门禁、模板路径
│   ├── EXAMPLES.md                        #   Phase 0/2/3 对外话术、manifest 示例、核心更新对话
│   ├── SKILL_MEMORY.md                    #   规则 1-9（语言门禁、占位符实值化、shell pipe 禁令等）
│   └── ITERATION_GUIDE.md                 #   迭代本 skill 的规范
│
├── .castflow/                             # 框架源码（装架后休眠，仅随 git pull 更新）
│   ├── bootstrap.py                       # 薄包装器，委托到 installer/
│   │
│   ├── installer/                         # 装架引擎（纯 Python 3.6+，零依赖）
│   │   ├── cli.py                         #   CLI 解析 + 主流程编排
│   │   ├── paths.py                       #   项目根 / harness 目录查找（支持 submodule 任意深度）
│   │   ├── backup.py                      #   BackupSession 会话目录式备份 + LRU 轮换
│   │   ├── io_ops.py                      #   safe_write / safe_copy_file / safe_copy_dir
│   │   ├── templates.py                   #   {{PLACEHOLDER}} 替换 + conditional block
│   │   ├── placeholders.py                #   各类占位符字典构建（已精简：安装器不再负责 skill 正文）
│   │   ├── hook_config.py                 #   .cursor/hooks.json 与 .claude/settings.json 幂等合并
│   │   ├── claude_merge.py                #   CLAUDE.md 三策略合并（1=换模板 / 2=保留 / 3=增量）
│   │   ├── validate.py                    #   Skill 规范验证（无 emoji / 无日期 / 无残留占位符 / 字数）
│   │   ├── manifest.py                    #   bootstrap-output/cf_manifest.json 读写
│   │   └── generate.py                    #   Phase A 全量 + Phase A 子集（--claude-md-only / --templates-only）
│   │
│   ├── core/                              # 被装架同步到 .claude/ 的核心内容
│   │   ├── CLAUDE.template.md             #   项目根 CLAUDE.md 的框架段模板（时点定义唯一权威源）
│   │   ├── GLOBAL_SKILL_MEMORY.md         #   跨 skill 运行时协议 1/2/3
│   │   ├── SKILL_ITERATION.md             #   Skill 四文件元规范 + Anchors 格式 + 容量治理
│   │   ├── protocols/
│   │   │   ├── idp-protocol.md            #   Intent Declaration Protocol（T2 按需）
│   │   │   └── validated-protocol.md      #   接受/拒绝信号判定（T3）
│   │   ├── skills/                        # 3 个核心 skill（随装架拷贝到 .claude/skills/）
│   │   │   ├── code-pipeline-skill/       #   多模块协作 9 步工序 + pipeline_protocol
│   │   │   ├── origin-evolve-skill/       #   读 trace、识别模式、生成 Append/Merge/Retire 提议
│   │   │   └── skill-creator/             #   Skill 生成/迭代/eval/benchmark 全套工具链
│   │   ├── agents/                        # code-pipeline 调用的 3 个分析型 agent prompt
│   │   │   ├── requirement-analysis-agent.md
│   │   │   ├── integration-matching-agent.md
│   │   │   └── pipeline-verify-agent.md
│   │   ├── hooks/                         # 生产 Hook 脚本（跨平台）
│   │   │   ├── trace-collector.py         #   编辑事件采集 + 自我修正检测（LRU 50 文件快照）
│   │   │   └── trace-flush.py             #   会话结束 → 五维评分 → trace.md + 四级 compaction
│   │   ├── templates/                     # 装架后供 skill-creator 使用的创作资产
│   │   │   ├── AUTHORING_GUIDE.md         #   Skill 创作元规范（四份域 README 的共享上游）
│   │   │   ├── agents/programmer.template.md
│   │   │   └── skills/programmer.template/   # 模块 skill 四件套模板 + 域 README
│   │   ├── scripts/
│   │   │   └── pipeline_merge.py          #   pipeline Step 3 并行输出聚合
│   │   └── traces/                        # 默认阈值与字段契约（分发到 .claude/traces/）
│   │       ├── config/
│   │       │   ├── limits.json            #   compaction 阈值 / 过期天数 / 保护参数
│   │       │   └── hooks.config.json      #   追踪扩展名 / 通用目录段 / 模块推断正则（跨语言适配入口）
│   │       └── README.md                  #   trace 字段契约 + limits / hooks.config 说明
│   │
│   └── bootstrap-assets/                  # 仅在冷启动期间使用的资产（不进 .claude/）
│       └── skill-templates/               #   architect / debug / profiler 的四件套模板 + 域 README
│           ├── architect.template/
│           ├── debug.template/
│           └── profiler.template/
│
└── test/                                  # 框架自身回归测试（不被 bootstrap 分发，176+ tests）
    ├── hooks/                             # 134 tests：评分、compaction、100 天 / 365 天模拟
    ├── bootstrap/                         # 42 tests：installer 包单元测试
    └── origin-evolve/                     # ~7000 次断言：origin-evolve 规范暴力验证
```

### 装架后用户项目的结构

```
项目根目录/
├── CLAUDE.md                              # 项目全局规则（框架段 + 项目段，增量合并）
├── .claude/
│   ├── skills/
│   │   ├── GLOBAL_SKILL_MEMORY.md         # T1/T2 运行时协议
│   │   ├── SKILL_ITERATION.md             # Skill 四文件元规范
│   │   ├── code-pipeline-skill/           # 【核心】多模块工序
│   │   ├── origin-evolve-skill/           # 【核心】自我进化引擎
│   │   ├── skill-creator/                 # 【核心】Skill 生成工具（含 eval/benchmark）
│   │   ├── architect-skill/               # 【项目级，Phase 5 生成】
│   │   ├── debug-skill/                   # 【可选，Phase 2 勾选才生成】
│   │   ├── profiler-skill/                # 【可选，Phase 2 勾选才生成】
│   │   └── programmer-<模块>-skill/       # 【按需生成】
│   ├── protocols/                         # idp / validated 两份按需协议
│   ├── agents/                            # code-pipeline 调用的 3 个分析 agent
│   ├── hooks/                             # trace-collector.py + trace-flush.py
│   ├── templates/                         # AUTHORING_GUIDE + programmer.template + agent 模板
│   ├── traces/                            # trace.md / weights.json / config/limits.json / config/hooks.config.json
│   ├── rules/                             # origin-evolve 生成的跨模块规则
│   └── settings.json                      # Claude Code hook 配置（增量合并）
├── .cursor/
│   └── hooks.json                         # Cursor hook 配置（增量合并）
└── CastFlow/                              # 框架源码（submodule，进入休眠）
```

---

## 端到端案例：从集成到自主进化

### 步骤 1 — 集成（30 秒）

```bash
git submodule add https://github.com/yunzeforbetter/CastFlow.git
```

**CastFlow 最好放置在与.claude目录同级的位置**

### 步骤 2 — 冷启动（约 5 分钟，AI 主导）

在 Cursor / Claude Code 中输入：

```
bootstrap castflow
```

AI 加载 `CastFlow/bootstrap-skill/SKILL.md` 并按 Phase 0-6 执行：

| Phase | 动作 | 结果 |
|-------|------|------|
| 0 | **语言门禁** — 输出 zh/en/ja/ko/other 菜单，等用户回复 | `manifest.language = zh` |
| 1 | 扫描 `Assets/Scripts/`、Unity 版本、命名约定 | 内部知识 |
| 2 | 询问 **debug / profiler** 是否启用（单独消息） | `optional_skills` |
| 3 | 确认命名规范（单独消息，可补充团队约定） | `content/claude/naming_conventions.md` |
| 4 | **装架** — `python .castflow/bootstrap.py`（**Phase A**：.claude/ 核心 + 根 CLAUDE.md + templates/） | `.claude/` 就绪 |
| 5 | **Phase 5 子代理并行**：主 agent 对每个项目级 skill 发一段话（任务 + 必读 `SKILL_ITERATION.md` + `AUTHORING_GUIDE.md` + 域 README + 模板 + 占位符实值 + 语言），子代理用 **skill-creator** 扫描真实代码、填模板、落盘到 `.claude/skills/<name>/` | `architect-skill/`（+ 可选 `debug-skill/` / `profiler-skill/`） |
| 6 | `python .castflow/bootstrap.py --validate` 校验规范，清理 `bootstrap-output/` | 冷启动完成 |

此时项目已拥有完整的 Skill 骨架 + Hook 配置。`.cursor/hooks.json` 与 `.claude/settings.json` 已增量合并，Hook 开始静默采集。

**如果出现搜寻不到的情况，可以显示告诉ai助手CastFlow的完整路径并让它启用 bootstrap castflow**

### 步骤 3 — 为xx模块生成 Skill（按需增量）

```
为xx系统生成 skill
```

触发 `skill-creator`（不需要记忆命令，自然语言即可）：AI 会自动完成代码扫描、信息提炼、四文件生成。**这是项目知识体系持续扩张的主要渠道**。

### 步骤 4 — 日常使用：Skill + Pipeline

**单 skill 调用**（自然语言描述匹配元数据自动加载）：

```
帮我在xx系统里加一个批量升级功能
```

**多模块编排**：

```
code_pipeline 实现用户交易系统
```

触发 9 步工序：需求分析 agent 拆接口 → 集成匹配 agent 对齐命名 → 并行子 agent 各自实现（每个模块带自己的 skill）→ `pipeline_merge.py` 聚合 → `pipeline-verify-agent` 验收。 **非常适合完整系统开发**

### 步骤 5 — 自主进化（零干预采集，人在回路审批）

一周后，`trace.md` 累积了 30 多条 pending 条目，其中 5 条含 `correction:auto:major` 标记（Hook 自动检测到的 AI 反复修正）。新会话打开时，`evolve-reminder` 规则静默检查并提示：

```
检测到 5 条 pending 条目含修正信号，建议运行: origin evolve
```

用户输入 `origin evolve`：

1. 读 trace，`validated:false` P0、修正条目 P1/P2 排序
2. 识别六类模式（修正聚簇 / 模块热点 / 复杂度集中 / 跨 skill 锚点重叠 / 知识缺口 / IDP 缺失）
3. 生成提议：
   - **Append** 一条 `programmer-xxx-skill/SKILL_MEMORY.md` 规则：*批量升级必须复用 `xxxx`，禁止直接调 `xx`*，Anchors = `[class:xx, method:xxx]`
   - **Retire** 一条旧规则（grep 验证其 Anchors 在代码中已不存在）
   - **Merge** 两条锚点 Jaccard ≥ 0.5 的重复规则
4. 用户逐个审批（可拒绝，拒绝会记录 `EVOLVE_REJECTION` 避免重复提议）
5. 写入，原 trace 条目替换为一行 `<!-- PROCESSED ts:... entries:N proposals:M -->`
6. 可选：对比有效/无效 trace 的 F/D/K/S/E 分布，单维度权重微调 5-10% 写入 `weights.json`

下次会话：新规则 + 校准后的评分模型同时生效。AI 不再重复犯这一类错。

### 步骤 6 — 框架升级

```bash
cd CastFlow && git pull
```

然后在 AI 中再次输入 `bootstrap castflow`，它会走 **核心更新** 工作流：复用 `manifest.language`，对比 `.castflow/core/` 与项目 `.claude/` 差异，仅更新元规范、核心 skill、protocols、templates，**项目级 skill 与 CLAUDE.md 项目段完全保留**。

---

## 文件清单（每个文件的作用）

### `CastFlow/bootstrap-skill/` — 顶层 AI skill（框架初始化器）

与其他 skill 的区别：它在 **.claude/ 尚未存在** 时就要运行，因此驻留在 CastFlow 源码内，由用户在 AI 助手中通过自然语言触发。

| 文件 | 作用 |
|------|------|
| `SKILL.md` | Phase 0-6 工作流定义、两种工作流（全量初始化 / 核心更新）、Phase 5 一段话手话规范与占位符表 |
| `EXAMPLES.md` | Phase 0/2/3 对外话术模板、`cf_manifest.json` 字段示例、模块 skill 对话范例 |
| `SKILL_MEMORY.md` | 9 条硬性规则：语言门禁、manifest 识别、占位符必须实值化、禁止 shell pipe 写文件等 |
| `ITERATION_GUIDE.md` | 本 skill 自身的演进规则 |

### `.castflow/bootstrap.py` + `installer/` — 装架引擎

`bootstrap.py` 是薄包装器。真实实现全在 `installer/` 包（11 个模块），所有 I/O 可 `--dry-run`、可备份、可 `--validate`。

| 模块 | 作用 |
|------|------|
| `cli.py` | 参数解析 + 主流程调度。支持 `--claude-md-only` / `--templates-only` / `--agent` / `--init-manifest` / `--language` / `--claude-md-harness`（三策略）/ `--project-root` / `--no-backup` / `--backup-keep` / `--clean-backups` |
| `paths.py` | 双路径解耦：`find_project_root` 向上查 `.claude/`（首次初始化时自动创建）；`find_harness_dir` 锚定 `.castflow/` 本体 |
| `backup.py` | `BackupSession` 会话目录备份（`.claude/.backups/<timestamp>/`），LRU 保留 N 次（默认 3），自动清理旧 `.bak` 散文件，自动追加 `.gitignore` 条目 |
| `io_ops.py` | 三件套写入：`safe_write` / `safe_copy_file` / `safe_copy_dir`。统一带 `merge_mode` + `dry_run` + `backup` |
| `templates.py` | `{{PLACEHOLDER}}` 替换（`strict=True` 未知 key 直接 fail）+ `<!-- if:tech -->` 条件块处理 |
| `placeholders.py` | 精简后仅构建 CLAUDE.md / agent 所需占位符字典；不再构建 architect/debug/profiler/programmer 的 skill 内容占位符（这些改由 skill-creator 子代理负责） |
| `hook_config.py` | Cursor `hooks.json` 与 Claude Code `settings.json` 的幂等增量合并，不覆盖项目已有 hook |
| `claude_merge.py` | CLAUDE.md 三策略：1=整段换模板（旧段备份）/ 2=保留当前 / 3=增量合并（模板新段 + 把项目段多出来的行追加进来）。非 TTY 默认 3，TTY 交互提示 |
| `validate.py` | Skill 规范验证：无 emoji、无日期、无残留 `{{KEY}}`、字数预算（代码块除外） |
| `manifest.py` | `bootstrap-output/cf_manifest.json`（canonical 名）读写 + 迁移老版 `manifest.json` 提示 |
| `generate.py` | `generate_all`（Phase A 全量）+ `run_phase_a_subset`（--claude-md-only / --templates-only）+ `generate_agent`（`--agent <module>`） |

### `.castflow/core/` — 被同步到 `.claude/` 的框架内容

| 文件/目录 | 作用 |
|-----------|------|
| `CLAUDE.template.md` | 项目根 `CLAUDE.md` 的框架段模板。**时点定义（T1-T4）的唯一权威源** |
| `GLOBAL_SKILL_MEMORY.md` | 跨 skill 运行时协议：协议 1（API 物理验证）、协议 2（学习后约束对齐）、协议 3（执行模式检测） |
| `SKILL_ITERATION.md` | Skill 四文件元规范：各文件职责隔离、Anchors/Related 格式、容量治理阈值、硬性约束清单 |
| `protocols/idp-protocol.md` | Intent Declaration Protocol 写入规则（T2-EXECUTE 按需） |
| `protocols/validated-protocol.md` | 用户接受/拒绝信号判定与写入规则（T3-FEEDBACK） |
| `skills/code-pipeline-skill/` | 多模块协作 9 步工序。含 `config/pipeline_protocol.md` + `config/defaults.json` + `config/params.schema.json` |
| `skills/origin-evolve-skill/` | 自我进化引擎。读 trace、识别六类模式、生成 Append/Merge/Retire 提议，走用户审批 |
| `skills/skill-creator/` | Skill 生成与迭代工具链。含 `agents/{analyzer,comparator,grader}.md`、`scripts/` 7 个工具（eval 运行、benchmark 聚合、打包、描述优化等）、`eval-viewer/`、`references/schemas.md` |
| `agents/requirement-analysis-agent.md` | Pipeline Step 1：拆需求、识别模块、输出可验证接口清单 |
| `agents/integration-matching-agent.md` | Pipeline Step 2：并行模块的接口一致性、命名对齐、耦合点检查 |
| `agents/pipeline-verify-agent.md` | Pipeline 验收：集成一致性与质量复核 |
| `hooks/trace-collector.py` | 每次文件编辑被调用。记录路径/行数/编辑次数；保存 `new_string` 快照（LRU 50）；用 `SequenceMatcher.ratio()` 检测 AI 自我修正标记 `R`；`tracked_extensions` / `excluded_extensions` 从 `traces/config/hooks.config.json` 加载 |
| `hooks/trace-flush.py` | 会话结束被调用。读 buffer → 五维评分 F/D/K/S/E → 达标写入 `trace.md`（`schema:N` 版本头）→ 四级 compaction（Level 0 清审计行 / L1 过期低分 / L2 中期低分 / L3 每模块保留 top N）→ validated 条目受保护。含 `--selftest` 子命令 |
| `templates/AUTHORING_GUIDE.md` | Skill 创作元规范（四份域 README 的共享上游）。包含项目勘察清单、反风格检查、Rubric |
| `templates/agents/programmer.template.md` | 为功能模块生成专属 programmer agent 时的 prompt 模板 |
| `templates/skills/programmer.template/` | 模块 skill 四件套模板 + 域 README（最常用，会被分发到 `.claude/templates/`） |
| `scripts/pipeline_merge.py` | code-pipeline Step 3 调用：聚合并行 agent 输出到 `PIPELINE_CONTEXT.md`（临时文件，pipeline 结束即删） |
| `traces/config/limits.json` | compaction 阈值、过期天数、保护参数的运行时默认值 |
| `traces/config/hooks.config.json` | Hook 外部化配置：`tracked_extensions`（18 种主流语言）、`excluded_extensions`、`generic_dir_segments`、`module_dir_pattern`。**修改此文件即可适配非 Unity/C# 项目，无需改 Python** |
| `traces/README.md` | trace 字段契约 + `schema:N` 版本规则 + limits/hooks.config 全字段说明 + Go/React 适配示例 |

### `.castflow/bootstrap-assets/` — 仅冷启动使用

`skill-templates/{architect,debug,profiler}.template/` 各含四份 `*.template.md` + 一份 `README.md`（域说明）。这些模板 **不被安装器分发到 `.claude/`**，由 Phase 5 的子代理在执行 `skill-creator` 时直接读取填充。

### `test/` — 框架自身回归测试（不分发）

| 文件 | 覆盖 | 规模 |
|------|------|------|
| `hooks/test_evolution.py` | collector 采集、buffer 格式、flush 评分、compaction 四级、validated 保护、审计行过期、空行清理 | 84 tests |
| `hooks/test_100day_simulation.py` | 100 天持续 append+compact 有界性、模块多样性 | 27 tests |
| `hooks/test_365day_simulation.py` | 365 天生产模拟：工作日/周末、季度漂移、混合会话、知识库生命周期 | 23 tests |
| `bootstrap/test_bootstrap.py` | installer 包：占位符替换、strict 模式、CLAUDE.md 三策略、hook config 幂等合并、BackupSession、LRU 轮换 | 42 tests |
| `origin-evolve/verify_redesign.py` | origin-evolve 规范确定性部分暴力验证：诊断计数、归因树、Append/Merge/Retire、Jaccard 边界、容量策略 | ~7000 次断言 |

---

## 渐进式信息披露（T1-T4）

命名约定 `T<序号>-<动词>`，权威源为项目根 `CLAUDE.md`「使用Skill的分层加载」段（always-applied，自动注入）。

| 时点 | 触发 | AI 主动读什么 |
|------|------|--------------|
| **T1-PREPARE** | 写代码前 | `GLOBAL_SKILL_MEMORY.md` 协议 1/2 + 目标 skill 的 `SKILL_MEMORY.md` + 按需 `EXAMPLES.md` 章节 |
| **T2-EXECUTE** | 代码生成中 | `GLOBAL_SKILL_MEMORY.md` 协议 3 + 按需 `protocols/idp-protocol.md` |
| **T3-FEEDBACK** | 用户反馈 | `protocols/validated-protocol.md` |
| **T4-MAINTAIN** | 创建/修改 skill 结构 | `SKILL_ITERATION.md` + 目标 skill 的 `ITERATION_GUIDE.md` |

时点不强制串行。四文件职责隔离是硬约束：代码示例只放 EXAMPLES、硬性规则只放 SKILL_MEMORY、导航和定位放 SKILL、演进规则放 ITERATION_GUIDE。

---

## 自我进化详解

### 两层数据采集（Hook 零 token + AI 微量补充）

```
编辑文件 → trace-collector 记录 path|lines|edits|flags → buffer
会话结束 → trace-flush 读 buffer → 五维评分 → 达标写 trace.md (pending)
任务结束 → AI 仅替换 type / skills 占位符
```

| 平台 | 配置文件 | 编辑事件 | 结束事件 |
|------|---------|---------|---------|
| Cursor | `.cursor/hooks.json` | `afterFileEdit` | `stop` |
| Claude Code | `.claude/settings.json` | `PostToolUse(Write)` | `Stop` |

### 五维评分模型

```
score = F·1.0 + D·0.5 + K·1.5 + S·0.5 + E·0.8    准入 score ≥ 1.5
```

| 维度 | 含义 | 计算 | 价值 |
|------|------|------|------|
| F — File Count | 修改文件数 | `min(files/3, 1.0)` | 多文件 = 更值得记录 |
| D — Module Spread | 模块分散度 | `min(modules/2, 1.0)` | 跨模块 = 架构决策 |
| K — Critical Path | 关键路径等级 | 接口 1.0 / 实现 0.6 / 基础 0.3 | 架构影响力梯度 |
| S — Change Scale | 改动规模 | `min(lines/50, 1.0)` | 大改更可能有价值 |
| E — Edit Intensity | 编辑密度 | `min(edits/5, 1.0)` | 反复修改 = 困难迭代，最值得记录 |

**各维度独立饱和**：1 个文件改 15 次（E 高）≠ 15 个文件各改 1 次（F 高）。防止批量操作假装高价值。

### Trace 条目与状态机

```
<!-- TRACE status:pending schema:1 -->
timestamp: 2026-04-13T10:00:00Z
type: _                  ← AI 补充
correction: auto:minor   ← Hook 自动检测（SequenceMatcher.ratio > 0.6）
validated: _             ← flush 注入 / pipeline 驱动
pipeline_run_id: _
modules: [Building, Queue]
skills: []               ← AI 补充
files_modified: [...]
file_count: 3
lines_changed: 80
edit_count: 12
score: 3.50
<!-- /TRACE -->
```

`status`：`pending` → `processed` / `expired` / `invalid`
`validated`：`_` / `true` / `false`（P0） / `pending-pipeline` / `invalid`
`correction`：`_` / `auto:minor` / `auto:major` / `minor` / `major`

### 四级 Compaction

| 级 | 触发 | 策略 | 保护 |
|----|------|------|------|
| L0 | 每次 flush | 清理过期 PROCESSED/COMPACTED 审计行 | — |
| L1 | entries > `compact_max_entries` | 移除超过 `entry_expire_days` 的低分 | `validated` 条目 |
| L2 | L1 后仍超标 | 移除 `age > level2_age_days` 且 `score < level2_score_threshold` | `validated` 条目 |
| L3 | L2 后仍超标 | 移除 `score < level3_score_threshold` | 每模块保留 top N（`keep_top_n_per_module`） |

`validated` 条目（`true` / `false` / `pending-pipeline`）携带用户反馈信号，**L1-L3 全部受保护**。

### origin-evolve 执行流

evolve-reminder 规则检测到 `pending ≥ 5` 或含修正信号的条目 `≥ 3` 时提醒用户。`origin-evolve-skill` 永远不会自动执行。

```
Step 1 Read & Triage（schema 门控 + 诊断计数 + P0-P4 排序 + `.trace_lock`）
Step 2 Identify Patterns（六类模式，要求 3+ 证据）
Step 3 Generate Proposals（归属决策树 + Append/Merge/Retire + 容量检查 + Anchors grep 验证）
Step 4 User Approval（逐个，可拒绝并记录 EVOLVE_REJECTION）
Step 5 Write & Mark Processed（原子写 + 审计行替换）
Step 6 Calibrate（可选，单维度 5-10% 微调 weights.json）
```

**Anchors 精确格式**：`[kind:path-hint:symbol]`，`kind ∈ {class, method, field, api, pattern}`。
示例：`[class:Building/BuildingManager, method:Building/BuildingFunc:OnUpgrade, pattern:EventArgs.Create]`。旧格式 `[BuildingManager, OnUpgrade]` 仍向后兼容。

### 自校准闭环

```
编辑 → 采集 → 评分 → trace (pending)
       ↓
提醒 → origin evolve → 模式 → 提议 → 审批 → 写入 Skill
                                         ↓
                                   校准 weights.json（可选）
                                         ↓
                                   下次会话：新知识 + 优化模型
```

---

## 命令参考

### AI 触发词（日常使用）

| 触发词 | 动作 |
|--------|------|
| `bootstrap castflow` | 首次初始化 / 核心更新（由 bootstrap-skill 分流） |
| `为 X 系统生成 skill` / `分析 Assets/Scripts/X/ 为这个模块创建 skill` | 触发 skill-creator 生成功能模块 skill |
| `帮我创建一个 X 的 skill` | 触发 skill-creator 生成自由格式 skill |
| `code_pipeline 实现 X` | 触发多模块 9 步工序 |
| `origin evolve` | 运行自我进化分析 |

### `bootstrap.py` CLI

```bash
python .castflow/bootstrap.py                      # Phase A 全量装架
python .castflow/bootstrap.py --dry-run            # 预览，不写入
python .castflow/bootstrap.py --validate           # 验证 .claude/skills/ 规范
python .castflow/bootstrap.py --claude-md-only     # 仅更新根 CLAUDE.md
python .castflow/bootstrap.py --templates-only     # 仅刷新 .claude/templates/
python .castflow/bootstrap.py --agent <module>     # 增量生成 programmer-<module>-agent
python .castflow/bootstrap.py --project-root /path # 显式指定项目根
python .castflow/bootstrap.py --claude-md-harness 3  # CLAUDE.md 合并策略（1/2/3）
python .castflow/bootstrap.py --init-manifest --language zh  # 非交互生成缺省 manifest
python .castflow/bootstrap.py --no-backup          # 跳过备份（git 用户）
python .castflow/bootstrap.py --backup-keep 5      # 保留最近 5 次备份
python .castflow/bootstrap.py --clean-backups      # 清空所有备份并退出

# Hook 独立健康检查（不依赖真实 hook 事件）
python .claude/hooks/trace-flush.py --selftest
```

CLI 的关键移除：
- **移除 `--skill`**：易与"生成 skill"混淆；Phase 5 项目级 skill 改走子代理 + skill-creator
- **移除 `--strict-content`**：安装器不再做内容合并，无需此开关
- **移除 Phase B**：`generate_all` 只跑 Phase A

### 文件归属速查

| 分类 | 管理方 | 更新方式 |
|------|--------|---------|
| `CastFlow/` | CastFlow 仓库 | `git pull` / submodule update |
| `CLAUDE.md` 框架段 | bootstrap | 装架时合并（三策略） |
| `CLAUDE.md` 项目段 | 项目团队 | 直接编辑 |
| `.claude/skills/*` 核心 skill | CastFlow 框架 | 装架同步 |
| `.claude/skills/*` 项目 skill | 项目团队 + 进化系统 | skill-creator 创建 / origin-evolve 追加 |
| `.claude/hooks/` | CastFlow 框架 | 装架生成 |
| `.claude/traces/` | Hook + evolve | 不手动编辑 |
| `.claude/rules/` | 进化系统 | evolve 提议，用户审批后生成 |

不要手动编辑 `CastFlow/.castflow/`（会被 `git pull` 覆盖）。所有定制在 `.claude/` 与 `CLAUDE.md` 项目段完成。

---

## 升级与回滚

```bash
cd CastFlow && git pull
# 然后在 AI 中输入 bootstrap castflow（会走核心更新工作流）
```

**备份机制**：`merge_mode: full` 覆盖任意已有文件前，原件复制到会话目录：

```
.claude/.backups/<YYYY-MM-DD_HH-MM-SS>/
    .claude/
        agents/requirement-analysis-agent.md
        skills/code-pipeline-skill/...
```

保留原始相对路径结构，回滚直接 `robocopy` / `rsync` 拷回即可。默认保留最近 3 次会话，更早自动删除。首次使用新版会一次性清理旧版散落的 `.bak` 文件并追加 `.backups/` 到 `.claude/.gitignore`。

---

## 测试套件

所有测试集中在 `CastFlow/test/`（与 `.castflow/` 同级，**不被 bootstrap 分发**），零外部依赖（仅 `unittest`）。每次运行在临时目录创建隔离环境，不影响项目数据。

```bash
# Hook 流水线（134 tests）
cd CastFlow/test/hooks
py test_evolution.py
py test_evolution.py --keep-data          # 保留到 test-output/evolution/
py test_100day_simulation.py --keep-data
py test_365day_simulation.py --keep-data
py -m unittest discover -s . -p "test_*.py"

# installer 包（42 tests）
cd CastFlow/test/bootstrap
py test_bootstrap.py

# 全量（176 tests）
cd CastFlow
py -m unittest discover -s test -p "test_*.py"

# origin-evolve 规范暴力验证（~7000 断言，~1 秒）
cd CastFlow/test/origin-evolve
py verify_redesign.py

# macOS / Linux：将 py 替换为 python3
```

**测试覆盖层级**：

| 层级 | 是否覆盖 | 说明 |
|------|---------|------|
| Python 函数正确性 | 是 | 评分公式、compaction 逻辑、状态转换等直接调用真实代码 |
| 数据格式与流转 | 是 | trace 条目的写/读/解析/压缩全链路用真实 `trace.md` 文件 |
| Hook 事件触发 | 否 | Cursor/Claude Code 通过 stdin JSON 触发 Hook，测试中直接调用函数替代 |
| origin-evolve AI 分析 | 否 | 模式识别是 AI 行为，测试中用简化检测函数替代 |
| 用户审批交互 | 否 | 人在回路无法自动化 |

测试的使命是 **保证数据管道的机械正确性**：在长期持续写入和压缩下不会损坏、不会无限膨胀、不会丢失关键信号。AI 侧的质量由 Skill 元规范 + `validate.py` + 人在回路共同保障。

---

## LICENSE

见 [LICENSE](./LICENSE)。
