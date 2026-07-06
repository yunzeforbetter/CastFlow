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
| 经验不积累 | 上一次犯过的错，下一次照犯不误 | Hook 零 token 快照你写的 auto-memory（`feedback`/`project`/`reference`）→ trace 成为 memory 账本 → `origin-evolve-skill` 蒸馏为规则提议 → 用户审批写入 Skill |

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

`code_pipeline 实现 X` 触发 **9 步**标准流水：**Step 1** 需求拆分与 API 声明（`requirement-analysis-agent`）→ **Step 2** 约束同步与 Handoff 冻结（同 agent，按需）→ **Step 3** 各模块实现（**模块配对执行单元**：`programmer-<module>-agent` + 同模块 skill）→ **Step 4** 依赖闭合（`integration-matching-agent`）→ **Step 5** 覆盖验收与 verdict（`pipeline-verify-agent`）→ **Step 6** 补全 `CompletableBlocks`（按需）→ **Step 7/8** 调试与性能（可选）→ **Step 9** 收尾与 `pipeline_run_id` 清理。编排合同与 Step 调度卡见装架产物 `skills/code-pipeline-skill/config/pipeline_protocol.md`；AI 入口见同目录 `SKILL.md`。

### 4. 自我进化：零 token 采集 + memory 快照账本 + 人在回路

经验原料的**唯一**捕获路径是 **auto-memory 快照**（schema:4）。你在返工、被纠正、被下硬约束时本来就会写 auto-memory —— trace-collector 的 Hook 在你写入 `~/.claude/projects/<slug>/memory/` 时自动把这些 memory 全文快照进 `trace.md`。评分、buffer、IDP 三套子系统已**全部退役**：Hook 不再解析代码编辑、不再打分、不再要求 AI 手填经验字段。

- `feedback` / `project` / `reference` 三类 memory 被快照；`user` 类型（个人画像）被过滤，不进 git
- 纯代码会话（没写任何 memory）不产生任何 trace 条目——账本只记"学到了什么"，不记"改了多少行"
- 蒸馏推迟到 `origin evolve` 统一做：`origin-evolve-skill` 读 trace 里的 `<!-- MEMORY -->` 快照、识别模式、生成 Append/Merge/Retire 提议，**用户审批后才写入** Skill

一次真实纠正 → 一条 `feedback` memory → 一次快照 → 一条规则提议，全程 AI 零额外动作。

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
│   │   │   └── validated-protocol.md      #   接受/拒绝信号判定（T3）
│   │   ├── skills/                        # 3 个核心 skill（随装架拷贝到 .claude/skills/）
│   │   │   ├── code-pipeline-skill/       #   多模块协作 9 步工序 + pipeline_protocol
│   │   │   │   └── scripts/
│   │   │   │       └── pipeline_merge.py  #     pipeline Step 3 并行输出聚合
│   │   │   ├── origin-evolve-skill/       #   读 trace、识别模式、生成 Append/Merge/Retire 提议
│   │   │   └── skill-creator/             #   Skill 生成/迭代/eval/benchmark 全套工具链
│   │   ├── agents/                        # code-pipeline 调用的 3 个分析型 agent prompt
│   │   │   ├── requirement-analysis-agent.md
│   │   │   ├── integration-matching-agent.md
│   │   │   └── pipeline-verify-agent.md
│   │   ├── hooks/                         # 生产 Hook 脚本（跨平台）
│   │   │   ├── trace-collector.py         #   auto-memory 写入采集（命中 memory 目录即全文快照，user 类型过滤）
│   │   │   └── trace-flush.py             #   会话结束 → 有快照才写 trace.md + 三级龄期 compaction
│   │   ├── templates/                     # 装架后供 skill-creator 使用的创作资产
│   │   │   ├── AUTHORING_GUIDE.md         #   Skill 创作元规范（四份域 README 的共享上游）
│   │   │   ├── agents/programmer.template.md
│   │   │   └── skills/programmer.template/   # 模块 skill 四件套模板 + 域 README
│   │   └── traces/                        # 默认阈值与字段契约（分发到 .claude/traces/）
│   │       ├── config/
│   │       │   ├── limits.json            #   compaction 阈值 / 过期天数 / 保护参数
│   │       │   └── hooks.config.json      #   memory 目录匹配正则（适配 autoMemoryDirectory 重定向）
│   │       └── README.md                  #   schema:4 字段契约 + limits / hooks.config 说明
│   │
│   └── bootstrap-assets/                  # 仅在冷启动期间使用的资产（不进 .claude/）
│       └── skill-templates/               #   architect / debug / profiler 的四件套模板 + 域 README
│           ├── architect.template/
│           ├── debug.template/
│           └── profiler.template/
│
└── test/                                  # 框架自身回归测试（不被 bootstrap 分发，149 tests）
    ├── hooks/                             # 107 tests：memory 快照采集、compaction、365 天生产模拟（共享 _trace_harness）
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
│   ├── protocols/                         # validated 单份 T3 协议
│   ├── agents/                            # code-pipeline 调用的 3 个分析 agent
│   ├── hooks/                             # trace-collector.py + trace-flush.py
│   ├── templates/                         # AUTHORING_GUIDE + programmer.template + agent 模板
│   ├── traces/                            # trace.md（memory 账本）/ config/limits.json / config/hooks.config.json
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

触发 9 步工序：需求分析 agent 拆模块与 API →（可选）约束冻结 → 各模块 **配对执行单元** 并行实现 → `pipeline_merge.py` 将 Step 3 摘要归并到 `PIPELINE_CONTEXT.md` → 集成匹配 agent 做依赖闭合 → `pipeline-verify-agent` 验收与 verdict →（按需）补全与重跑闭合 → 收尾。 **非常适合完整系统开发**

### 步骤 5 — 自主进化（零干预采集，人在回路审批）

一周里你被纠正过几次，每次都顺手写了一条 `feedback` auto-memory。Hook 已把它们快照进 `trace.md`。新会话打开时，`evolve-reminder` 规则静默检查并提示：

```
检测到 8 条 pending 条目（其中 5 条含 feedback 快照），建议运行: origin evolve
```

用户输入 `origin evolve`：

1. 读 trace，只保留 `pending`，排除尚未定案的 `validated:pending-pipeline` 候选
2. 识别模式：`feedback` 快照本身就是用户给的显式规则（单条即足以成案），同一 skill/主题的多条快照合并为一条连贯规则
3. 生成提议（写入前 grep 校验快照声明是否仍与当前代码一致）：
   - **Append** 一条 `programmer-xxx-skill/SKILL_MEMORY.md` 规则：*批量升级必须复用 `xxxx`，禁止直接调 `xx`*，Anchors = `[class:xx, method:xxx]`
   - **Retire** 一条旧规则（grep 验证其 Anchors 在代码中已不存在）
   - **Merge** 两条锚点 Jaccard ≥ 0.5 的重复规则
4. 用户逐个审批（可拒绝，拒绝会记录 `EVOLVE_REJECTION` 避免重复提议）
5. 写入 `.skillmanager/.skills/`，原 trace 条目替换为一行 `<!-- PROCESSED ts:... entries:N proposals:M -->`

下次会话：新规则生效，AI 不再重复犯这一类错。

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
| `protocols/validated-protocol.md` | 用户接受/拒绝信号判定与写入规则（T3-FEEDBACK） |
| `skills/code-pipeline-skill/` | 多模块协作 9 步工序（复合组件）。含 `SKILL.md`（工作流总览）、`config/pipeline_protocol.md`（含 Step 调度卡）、`config/handoff_protocol.md`、`architecture/*.md`（复杂系统）、`EXAMPLES.md` + `examples/*`、`scripts/pipeline_merge.py`、`config/defaults.json` + `config/params.schema.json` |
| `skills/origin-evolve-skill/` | 自我进化引擎。读 trace 里的 memory 快照、蒸馏为规则、生成 Append/Merge/Retire 提议，走用户审批 |
| `skills/skill-creator/` | Skill 生成与迭代工具链。含 `agents/{analyzer,comparator,grader}.md`、`scripts/` 7 个工具（eval 运行、benchmark 聚合、打包、描述优化等）、`eval-viewer/`、`references/schemas.md` |
| `agents/requirement-analysis-agent.md` | Pipeline **Step 1 / Step 2**：需求拆分、API 声明、（可选）约束同步与蓝图冻结 |
| `agents/integration-matching-agent.md` | Pipeline **Step 4**：依赖闭合验证（Dependency Closure Report） |
| `agents/pipeline-verify-agent.md` | Pipeline **Step 5**：Done Criteria 与 Module/Global Verdict、result signal |
| `hooks/trace-collector.py` | PostToolUse(Write/Edit) 被调用。只采集 auto-memory 写入：命中 `~/.claude/projects/<slug>/memory/` 时读全文、过滤 `user` 类型、按 slug 存入 `.trace_memory_snapshots`（LRU 上限）；`memory_dir_pattern` 从 `traces/config/hooks.config.json` 加载 |
| `hooks/trace-flush.py` | 会话结束被调用。读 `.trace_memory_snapshots` → 有快照才写入 `trace.md`（`<!-- MEMORY -->` 子块嵌入，schema:4）→ 三级龄期 compaction → 经验资产受保护。含 `--selftest` 子命令 |
| `templates/AUTHORING_GUIDE.md` | Skill 创作元规范（四份域 README 的共享上游）。包含项目勘察清单、反风格检查、Rubric |
| `templates/agents/programmer.template.md` | 为功能模块生成专属 programmer agent 时的 prompt 模板 |
| `templates/skills/programmer.template/` | 模块 skill 四件套模板 + 域 README（最常用，会被分发到 `.claude/templates/`） |
| `skills/code-pipeline-skill/scripts/pipeline_merge.py` | code-pipeline **Step 3** 调用：从各模块 `temp/pipeline-output/*.md` 提取 `PIPELINE_SUMMARY`，写入 `PIPELINE_CONTEXT.md` 内受控归并块（幂等替换）；缺标记或混入 `Parent Summary` 时 fail-closed |
| `traces/config/limits.json` | compaction 阈值、过期天数、保护参数的运行时默认值 |
| `traces/config/hooks.config.json` | Hook 外部化配置：`memory_dir_pattern`（识别 auto-memory 目录的正则）。**仅在 `autoMemoryDirectory` 被重定向到非标准路径时才需修改** |
| `traces/README.md` | schema:4 字段契约 + `<!-- MEMORY -->` 子块格式 + limits/hooks.config 全字段说明 |

### `.castflow/bootstrap-assets/` — 仅冷启动使用

`skill-templates/{architect,debug,profiler}.template/` 各含四份 `*.template.md` + 一份 `README.md`（域说明）。这些模板 **不被安装器分发到 `.claude/`**，由 Phase 5 的子代理在执行 `skill-creator` 时直接读取填充。

### `test/` — 框架自身回归测试（不分发）

| 文件 | 覆盖 | 规模 |
|------|------|------|
| `hooks/_trace_harness.py` | 共享测试基座：`make_trace_block` / `TraceTestBase` / hyphen-module 导入（被下列 hook 测试复用） | — |
| `hooks/test_evolution.py` | collector 采集、buffer 格式、flush 评分、compaction 四级、validated 保护、审计行过期、空行清理 | 84 tests |
| `hooks/test_365day_simulation.py` | 365 天生产模拟：工作日/周末、季度漂移、混合会话、知识库生命周期、有界压缩、模块多样性 | 23 tests |
| `bootstrap/test_bootstrap.py` | installer 包：占位符替换、strict 模式、CLAUDE.md 三策略、hook config 幂等合并、BackupSession、LRU 轮换 | 42 tests |
| `origin-evolve/verify_redesign.py` | origin-evolve 规范确定性部分暴力验证：诊断计数、归因树、Append/Merge/Retire、Jaccard 边界、容量策略 | ~7000 次断言 |

---

## 渐进式信息披露（T1-T4）

命名约定 `T<序号>-<动词>`，权威源为项目根 `CLAUDE.md`「使用Skill的分层加载」段（always-applied，自动注入）。

| 时点 | 触发 | AI 主动读什么 |
|------|------|--------------|
| **T1-PREPARE** | 写代码前 | `GLOBAL_SKILL_MEMORY.md` 协议 1/2 + 目标 skill 的 `SKILL_MEMORY.md` + 按需 `EXAMPLES.md` 章节 |
| **T2-EXECUTE** | 代码生成中 | `GLOBAL_SKILL_MEMORY.md` 协议 3（探索深度判定） |
| **T3-FEEDBACK** | 用户反馈 | `protocols/validated-protocol.md` |
| **T4-MAINTAIN** | 创建/修改 skill 结构 | `SKILL_ITERATION.md` + 目标 skill 的 `ITERATION_GUIDE.md` |

时点不强制串行。四文件职责隔离是硬约束：代码示例只放 EXAMPLES、硬性规则只放 SKILL_MEMORY、导航和定位放 SKILL、演进规则放 ITERATION_GUIDE。

---

## 自我进化详解

### 数据采集（Hook 零 token，只快照 auto-memory）

```
模型写 auto-memory (~/.claude/projects/<slug>/memory/*.md)
   │  PostToolUse: Write/Edit/MultiEdit
   ▼
trace-collector：命中 memory 目录 → 读全文 → type==user 过滤 → 按 slug 存入 .trace_memory_snapshots
   │  Stop
   ▼
trace-flush：本会话有快照才写 trace.md（纯代码会话不产生条目）；每份快照嵌为 <!-- MEMORY --> 子块
```

**代码编辑不再采集、不再打分。** 采集的唯一对象是 auto-memory 写入，`user` 类型（个人画像）被过滤不进 git。

| 平台 | 配置文件 | 采集事件 | 结束事件 |
|------|---------|---------|---------|
| Cursor | `.cursor/hooks.json` | `afterFileEdit` | `stop` |
| Claude Code | `.claude/settings.json` | `PostToolUse(Write/Edit/MultiEdit)` | `Stop` |

### Trace 条目结构（schema:4）

```
<!-- TRACE status:pending schema:4 -->
timestamp: 2026-07-03T13:00:00Z
type: feedback
validated: _
pipeline_run_id: _
memory_snapshots: 1
<!-- MEMORY slug:observablelist-ordered-insert type:feedback -->
description: ObservableList 有序插入必须用 Insert 不能用 Add
---
ObservableList 有序插入必须用 Insert(index) 不能用 Add()。
Why: Add 永远追加到末尾，列表顺序会错。
How to apply: 需要按指定位置插入时用 Insert(index, item) 并做边界检查。
<!-- /MEMORY -->
<!-- /TRACE -->
```

| 字段 | 写入方 | 含义 |
|------|--------|------|
| `status` | hook 写 `pending`，evolve 改其他 | `pending` → `processed` / `expired` / `invalid` |
| `type` | hook | 快照主导类型（`feedback` > `project` > `reference`） |
| `validated` | hook | `_` / `true` / `false` / `pending-pipeline` / `invalid` |
| `pipeline_run_id` | hook | code-pipeline 运行标记（可选） |
| `memory_snapshots` | hook | 嵌入的 MEMORY 子块数量 |

每个 MEMORY 子块是 memory 文件的逐字副本（超 8KB 截断，标 `truncated:1`）。旧 schema:1-3 条目可能仍带已退役字段（`score`/`modules`/`correction`/`lesson` 等），origin-evolve 读到不报错但不依赖，随 compaction 龄期自然淘汰。

### 三级龄期 Compaction

评分退役后，压缩改为纯龄期驱动。带 memory 快照或 `validated:true` 的**经验资产条目永不自动删除**，只有纯骨架条目会被淘汰。

| 级 | 触发 | 策略 | 保护 |
|----|------|------|------|
| L0 | 每次 flush | 清理过期 PROCESSED 审计行 | — |
| L1 | — | 移除 `validated:invalid` 骨架条目 | 经验资产 |
| L2 | entries/size 超阈值 | 移除 `age > level2_age_days` 的非资产骨架 | 经验资产 + in-flight pipeline |
| L3 | L2 后仍超标 | 移除 `age > level3_age_days` 的溢出条目 | 始终保留最近 `keep_recent_n`（默认 20）条 |

阈值见 `traces/config/limits.json`：`compact_max_entries`(80) / `compact_max_size_kb`(100) / `level2_age_days`(14) / `level3_age_days`(7) / `keep_recent_n`(20)。

### origin-evolve 执行流

evolve-reminder 规则检测到 `pending ≥ passive_trigger_threshold`（默认 10）时提醒用户。`origin-evolve-skill` 永远不会自动执行。

```
Step 1 Read & Triage（schema 门控：接受 1-4 / 保留 pending / 排除 pending-pipeline / `.trace_lock`）
Step 2 Identify Patterns（feedback 快照即用户显式规则，单条足以成案；同主题多条合并）
Step 3 Generate Proposals（归属决策树 + Append/Merge/Retire + 容量检查 + Anchors grep 验证）
Step 4 User Approval（逐个，可拒绝并记录 EVOLVE_REJECTION）
Step 5 Write & Mark Processed（写入 .skillmanager/.skills/ + 审计行替换）
```

评分权重自校准（原 Step 6）已随评分子系统退役——schema:4 无维度可调。若快照本身失焦（如大量低价值 `project` 快照），属 hook/config 问题（`memory_dir_pattern`），交用户处理而非在此校准。

**Anchors 精确格式**：`[kind:path-hint:symbol]`，`kind ∈ {class, method, field, api, pattern}`。
示例：`[class:Building/BuildingManager, method:Building/BuildingFunc:OnUpgrade, pattern:EventArgs.Create]`。旧格式 `[BuildingManager, OnUpgrade]` 仍向后兼容。

### 闭环

```
返工/纠正/下硬约束 → 你写 feedback auto-memory → Hook 快照进 trace (pending)
       ↓
提醒 → origin evolve → 蒸馏快照 → 提议 → 审批 → 写入 Skill
                                         ↓
                                   下次会话：新知识生效，不再重复犯错
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
**如果出现python指令无效果，观察是不是未配置环境变量，或者直接使用py -3 来替代**

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
# Hook 流水线（107 tests）
cd CastFlow/test/hooks
py test_evolution.py
py test_evolution.py --keep-data          # 保留到 test-output/evolution/
py test_365day_simulation.py --keep-data
py -m unittest discover -s . -p "test_*.py"

# installer 包（42 tests）
cd CastFlow/test/bootstrap
py test_bootstrap.py

# 全量（149 tests）
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
