# Changelog

本文件记录 CastFlow 的用户可见变更。版本号遵循语义化：破坏性工作流 = 主版本，新能力 = 次版本，修复与收口 = 补丁。

---

## 2.0.0 — 2026-09-18

**CastFlow 2.0：从「对话装架 + 9 步流水线 + 给编辑打分」升级为「GUI 操作系统 + 一份 skill 真源 + memory 账本」。**

**改造原因：AI 本身已经更强、也更敏感。** 1.x 用过密的规则、编排和打分去管早期模型；放到今天，这些约束占用上下文、把「建议」变成仪式，反而限制判断力。2.0 不是在 1.x 上叠功能，而是按现行模型能力做减法：拆掉昂贵、易误召回、或没有加载入口的子系统，只留项目特有的硬护栏。

日常路径收成四步：向导拷文件 → 可选让 AI 按逻辑功能生成模块 skill → 按模块写代码 → 纠正时写 memory，审批后变成规则。

### 新旧对照

| | 1.x | 2.0 |
|--|-----|-----|
| 你怎么装上 | 对 AI 说 `bootstrap castflow`，回答语言/模块，模型代跑命令 | 双击 `castflow.bat` 或 `manager.py launch`；CastFlow 可在工程外 |
| 知识写在哪 | 每个宿主一份 `.claude/skills`、`.grok/skills`、`.cursor/skills`… | `.castflow-runtime/skills/` 真源；只投影 Claude 与 Codex 发现路径 |
| 模块从哪来 | `manager.py scan` 按目录和文件数切 | 无 Python 扫描器。AI 按逻辑功能粗扫，宿主多选；框架树硬排除 |
| 一次生成几个 | 每批最多 3 个并行子代理 | **一次一个**：落队列、清上下文、validate/sync、标 done |
| 跨模块功能怎么做 | `code-pipeline-skill` Step 1–9 + 三个专用 agent | 直接调各 `programmer-*-skill`。pipeline 退役，sync 清残留 |
| 经验怎么进仓库 | 五维评分（F/D/K/S/E）盯编辑 buffer，纯改代码也会产 trace | 只快照你写的 memory。没写 memory = 本会话不记账 |
| 相近规则怎么合并 | 模型在 skill 正文里发明 Jaccard | `manager.py homology` 一批算连通分量；阈值不写进 evolve skill |
| AI 写代码前读什么 | 报备约束清单、Grep 至少两次、执行模式命名 | 三协议：先证后用、约束覆盖抄来的代码、范围不够就先问 |
| 装错了怎么办 | 手删 `.claude/` | GUI 回退 / `unseed`；工程源码不动 |
| 进化不想用 | 文档里说可以关，路径分散 | 向导或 `evolve on\|off`：卸 hook 与 origin-evolve，traces 保留 |

### 这版真正变好的地方

1. **冷启动不再消耗对话。** 语言、适配器、进化、是否扫描，都在 GUI 完成。Agent 只负责一件事：请你打开向导；勾选扫描时再执行你粘贴的 `/goal`。装架与内容生产解耦，失败可 `unseed`。
2. **一份真源，宿主不再重复召回。** 过去 Grok/Cursor 再拷一棵 skill 树，同一 skill 会被扫两次。现在只联 `.claude/skills` 与 `.agents/skills`；兼容残留会被 sync 清掉。投影目录由托管 `.gitignore` 整目录忽略，Windows junction 不再误入库、切分支不再坏。
3. **模块划分跟产品走，不跟文件夹走。** 删掉 `scan.py` 和「没有 `.cs` / `Assets/Scripts` 就拒绝」。AI 在当前会话按公开类型和生命周期归类，你在多选框里勾；`util`/`test`/`editor` 默认不勾但仍看得见。CastFlow 自己永远不是模块。
4. **生成质量优先于吞吐。** 并行子代理会把扫描碎片和三份 SKILL 正文同时塞进上下文。2.0 强制：选中短卡落盘 → 丢掉未选项 → 一次读一张卡写一个 skill → validate 通过才标 done。architect/debug/profiler 同样一次一个。
5. **进化原料变成「你明确说过的话」。** 五维评分把「改了多少行」当成「学到了什么」，噪声大、校准还要再烧一轮。schema:4 只嵌 memory 全文；`feedback` 单条即可成案，其它类型要 homology 簇 ≥ 2。纯代码会话零条目。
6. **Merge 是确定性算法，不是散文。** `_homology.py` 用 slug / 同 skill / Anchors Jaccard≥0.5 做并查集。evolve 禁止自己发明阈值，禁止一对一开 Python 进程。
7. **协议按现行模型能力收口，不再用过密规则绑住更强的模型。** 敏感模型会把报备清单、Grep 次数、执行模式命名当成不可跳过的仪式。`GLOBAL_SKILL_MEMORY` 只留三协议；未验证 API 只给该调用标 TODO，不再停掉整份补丁。`SKILL_ITERATION` 去掉恐吓段、不可执行的 bash 剧本、和 `validate.py` 打架的字数。description 漏召回好过误召回。
8. **框架是插件，不是绑架。** 进化可关。CastFlow 可放另一盘。工厂仓拒绝把自身当成目标项目。`update-framework` 刷新核心、不动项目 skill。
9. **长任务有单独的打包器。** `goal-loop-creator` 把演进需求打成可恢复 Goal Loop 包（`RUN_PROMPT.md` + 独立 run state），自己不调用 `/goal`，也不和模块扫描抢路径。

### Added

- **管理器与 GUI**：`.castflow/manager.py` + `manager/`。`launch` / `setup` / `unseed` / `update-framework` / `seed` / `sync` / `skills` / `retire` / `activate` / `update` / `evolve` / `queue` / `handoff` / `flush` / `homology` / `validate` / `status` / `ui`。stdlib HTTP 控制台：未装架四步向导，装架后「框架 / Skills / 队列」。
- **`castflow.bat`**：纯 ASCII（避免 cmd.exe 代码页拆中文）；文件夹选择器；CastFlow 不必住在工程里；跨盘 hook 写绝对路径。
- **`.castflow-runtime/`**：目标项目里唯一的 CastFlow 目录。skill / memory / traces / protocols / config 真源，加上 hooks、manager、`module-catalog.md`。不再 vendor 一份 `.castflow/`。`skills-state.json` 记住退役，后续 sync 遵守且不复活。
- **模块 skill loop-engine**：`MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` + `rules/module-catalog.md`。勾选后默认提示词一行：`/goal 读取并按照 …MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md 执行`。
- **`unseed`**：卸 runtime 与投影（含项目里的 manager），不删工程源码。CastFlow 仓的 `.castflow/` 不动。
- **homology**：`core/hooks/_homology.py` 与 `manager.py homology`（stdin JSON → 连通分量）。
- **`goal-loop-creator` 升为核心 skill（长任务转换系统）**：冷启动自动 seed 并在向导/Skills 页标注。把需求编译成 AI 可跑的 loop-engine 长任务包（Goal Loop Package，INTAKE→HANDOFF）。产物在 `loop-engine/packages/`，不进 skill 真源，不执行 `/goal`。
- **投影 gitignore**：sync 在项目根写入稳定块，忽略 `.claude/skills/` `.agents/skills/` `.grok/skills/` `.cursor/skills/` 整目录；已跟踪路径 `git rm --cached`。
- **工厂仓保护**：对 CastFlow 仓库本身 seed/sync/setup 拒绝，并删除误留的 runtime / 适配器树 / 根 CLAUDE.md。
- **description 形状检查**：`validate.py` 限制长度（programmer 280 / 其它 240）、`NOT` 最多一次、拒绝 `when-to-use` 等额外 YAML 键、拒绝 pushy 扩词。

### Changed

- **冷启动主路径** = GUI（拷文件）。`bootstrap-skill` 已删除；下次 sync / 打开 manager 会清掉已装项目残留。
- **Skill 发现**只投影 Claude + Codex。Grok/Cursor 扫这两处；sync 清掉 `.grok/skills` / `.cursor/skills` 里的 CastFlow 副本。Hook JSON 与 evolve-reminder 仍按适配器开关写。
- **模块发现**改为会话内 AI 流程（粗扫 → 多选必须停 → 落卡 → 一次一个）。GUI 不再列出脚本扫描结果。
- **日常工作**改为直接调用模块 skill。生成写入 runtime，禁止写适配器镜像。
- **进化采集**改为 schema:4 memory 快照。主路径 `.castflow-runtime/memory/`；Claude `~/.claude/projects/<slug>/memory/` 仅为可选 inbound。`user` 类型过滤。
- **origin-evolve**：合格条件改为 `feedback+ok` 或同源 ≥ 2；`validated` 不授权；一批 homology；业务规则不写 `.claude/rules/`。
- **GLOBAL_SKILL_MEMORY**：只保留三协议。同文件豁免仅限已写出的同一符号且同一签名；Grep 命中不是证据。与根规则冲突时根规则赢。不可逆才等确认。
- **SKILL_ITERATION**：四角色仍是标准，链路需要时可有非 markdown 附件（必须有指针）。体积 warning 走 `manager.py validate`。EXAMPLES 从仓库复制热路径，不要求「完整 using 清单」。
- **compaction**：纯龄期；经验资产（有快照或 `validated:true`）永不自动删。
- **根规则**只从 `ROOT_RULES.template.md` 注入 `CLAUDE.md` / `AGENTS.md`。
- **控制台**：未装架只显示向导；装架后三页。框架页「从 CastFlow 源更新并同步」= `update-framework`。
- **测试布局**：hooks 测试在 `test/hooks/`；新增 `test/manager/`、`test/hooks/test_homology.py`、`test/skills/`；入口 `test/run_all.py`。
- **目标项目只留 `.castflow-runtime/`**：冷启动把 manager、hooks、`module-catalog.md`、ROOT_RULES 模板写入 runtime，不再 vendor `.castflow/`。项目命令是 `python .castflow-runtime/manager.py`。
- **Skill 停用是本机名单**：`.castflow-runtime/skills-disabled.json`（gitignore）。未列入则激活。打开 manager 自动刷新投影。

### Removed

- `.castflow/core/skills/code-pipeline-skill/` 以及 `requirement-analysis` / `integration-matching` / `pipeline-verify` agent。sync 清已装项目残留。trace-flush 不再消费 pipeline result；遗留 `pending-pipeline` 标 invalid。
- `.castflow/manager/scan.py`、`manager.py scan`、`/api/scan`、`/api/preview-scan`。
- 五维评分、编辑 buffer、IDP、`traces/weights.json`、评分自校准（原 evolve Step 6）。
- `.castflow/core/templates/skills/programmer.template/`、`templates/agents/programmer.template.md`、`--templates-only`、`--agent`。安装器不再分发 `.claude/templates/`。
- `.castflow/core/templates/AUTHORING_GUIDE.md`（与 SKILL_ITERATION 重复，Rubric 从未被代码执行）。
- `.castflow/core/skills/skill-forge/`。创建走 skill-creator；冷启动禁止评测环。
- `.castflow/core/CLAUDE.template.md`、`.castflow/installer/placeholders.py`。
- bootstrap CLI：`--skill`、`--strict-content`、Phase B。
- `.castflow/bootstrap.py` 以及 installer 的 1.x Phase A 入口（`cli.py` / `generate.py` / `backup.py` / `manifest.py` / `hook_config.py` / `claude_merge.py` / `templates.py` / `io_ops.py` / `paths.py`）。校验只留 `installer/validate.py`，由 `manager.py validate` 调用。
- 向 `.grok/skills` / `.cursor/skills` 写入 CastFlow skill。
- `.castflow/bootstrap-assets/skill-templates/`（architect/debug/profiler 域模板）。召回句内联进 `SKILL_ITERATION.md`。
- 顶层 `bootstrap-skill/`。冷启动只走 `castflow.bat` / `manager.py launch`。

### Fixed

- 投影进 Git / Windows junction 当普通目录入库后切分支损坏：gitignore 整目录 + `git rm --cached`。
- `castflow.bat` UTF-8 中文在 cmd.exe 下被拆成非法命令，并误把 CastFlow 自身当项目根。
- 勾选扫描却把 `CastFlow/` `.castflow/` runtime / 适配器树当成业务模块。
- 模块 skill description 写成 skill-creator 自由创作的 pushy 扩词（「即使没点名也要用」）。
- bootstrap / manager 文档仍把已删除的 `scan` 写成现行命令。
- 模板 UTF-8 BOM、Windows 默认编码下 `open()` 无 `encoding=`（跨平台读写中文）。

### 升级注意（1.x → 2.0）

1. `git pull` 后在目标项目跑 `python .castflow-runtime/manager.py update-framework`（或 GUI 框架页）。框架源仍在 CastFlow 仓；项目只有 `.castflow-runtime/`。
2. 项目 skill 正文应在 `.castflow-runtime/skills/`。若只存在于适配器树，先拷进 runtime 再 sync。
3. 不要再调用 `code_pipeline` / `manager.py scan` / `bootstrap.py`。
4. 纠正请写 `.castflow-runtime/memory/`（`type: feedback`），不要指望改代码行数触发进化。
5. 旧 trace（schema 1–3）可留着，evolve 忽略退役字段，compaction 会自然淘汰骨架。
6. 若曾提交 `.claude/skills` 等投影，下一次 sync 会从索引移除，工作树联接保留。

---

## 1.x 归档

以下为 2.0 之前已落地、现已吸收或被 2.0 取代的记录，保留以便对照。不再单独标 Unreleased。

### 1.x 装架与多工具（已被 2.0 管理器吸收）

- Skill 真源最初设计为 runtime，再投影到四个宿主；2.0 收成 Claude + Codex 两棵发现树。
- 可视化控制台、进化开关、`retire` / `update` / `sync`、HTTP `/api/skills*` 在 1.x 末期引入，2.0 补齐 `activate` / `unseed` / `homology` / `validate` / 文件夹选择器。
- 冷启动曾是 seed → **scan** → ui → generate；2.0 删除 scan，勾选改为复制 `/goal`。
- 清单 canonical 名 `bootstrap-output/cf_manifest.json`（避免与 Unity `Packages/manifest.json` 混淆），仍可读旧 `manifest.json`。
- `find_project_root` / `find_harness_dir` 解耦：支持 CastFlow 作为子目录；`--project-root`。
- CLAUDE.md 三策略合并；BackupSession LRU；hook 配置幂等增量合并。
- i18n：manifest `language`，默认中文；模板固定中文，生成内容语言由 prompt 控制。
- 项目更名 CostFlow → CastFlow；`SKILL_RULE.md` → `SKILL_ITERATION.md`。

### 1.x 进化（评分模型，2.0 已退役）

- 五维加权评分 F/D/K/S/E；K 三档；E 编辑密度；buffer `path|lines|edits|flags`。
- 自动修正检测（R 标志）；`weights.json` 自校准。
- collector 扩展 18 种语言后缀；非代码资源过滤。
- SKILL_MEMORY 增加 Anchors / Related；Append / Merge / Retire；容量治理。
- origin-evolve 归属决策树；pending 提醒阈值与 evolve-reminder 对齐。
- compaction L0–L3、validated 保护、审计行过期、空行清理。
- `apply_pipeline_result()` 的 `result_str` 未初始化（已随 pipeline 一起成为历史）。

这些采集与打分路径在 2.0 由 memory 快照账本替代。字段若仍出现在旧 `trace.md` 里，只随龄期淘汰，新写入不再产生。

### 1.x pipeline（2.0 已删除）

- `code-pipeline-skill` 曾作为复合编排组件：Step 调度卡、Handoff L0/L1、`pipeline_merge.py` fail-closed、`pending-pipeline` 信号。
- 设计动机是多波次并行时的合同化收口。实践中浸染 shared agent、和模块 skill 抢入口，且日常改一个系统并不需要 9 步。
- 2.0 删除该 skill 与三个 agent；日常改动走模块 skill。

### 1.x 测试

- `test/hooks/test_evolution.py`、`test_365day_simulation.py`（及已移除的 100 天套件）、`test/bootstrap/test_bootstrap.py`、`test/origin-evolve/verify_redesign.py`。
- hooks 测试从 `.castflow/core/hooks/` 迁到 `CastFlow/test/hooks/`，bootstrap 不再分发测试文件。
- 2.0 在此基础上增加 manager / homology / GLOBAL_SKILL_MEMORY 契约测试，并由 `test/run_all.py` 串起来。
