# Changelog

## Unreleased

### code-pipeline-skill 与执行层（真源 `.castflow/core/`）

- **why（改造原因）**: **功能与模块拆成多波次并行时**，旧编排缺少逐步「给—读—写—交」的合同化收口，易出现 **互相等待、依赖未显式闭合的编排死锁**；通过 Step 调度卡、Handoff / merge / result signal 的明确契约与脚本侧 fail-closed，每步有唯一产物与前进条件，避免无限挂起。
- **why**: 修复 pipeline 对 **公共 agents、templates 等 shared 模块的浸染**——非 pipeline 场景不应被迫携带工序特例；shared 仅保留通用契约，pipeline 专用语义不再写入其正文。
- **why**: 将编排门禁 **收拢到 `code-pipeline-skill` 自身**（`config/*`、四件套与架构页），以 **复合 Skill（复合编排组件）** 存在：独立演进编排语义，**不升格为框架根**，也不绑架全局 agent/skill 定义。
- **design**: 将 `code-pipeline-skill` 明确为**复合编排组件**（非框架根）：执行期合同与读写路径集中在 `config/pipeline_protocol.md`；shared agents / templates 保持 orchestrator 无关本体，pipeline 专用消费方式不写入其正文。
- **feat**: `config/pipeline_protocol.md` 增加 **Step 调度卡**（给 / 读 / 写 / 交 / 不足兜底）；`SKILL_MEMORY.md` **规则 0**：调度各 Step 时必须附带对应调度卡，禁止只喊「执行 Step N」。
- **feat**: Handoff 与快速路径：`L0`（`No-Handoff Rationale`）与 `L1+`（`Handoff Draft` / Freeze）在 `handoff_protocol` 与 Step 1 骨架中对齐；复杂系统下 `NeedsSubpipeline` 仅允许显式 `sub-pipeline` 派发行。
- **docs**: `SKILL.md` 恢复 **可执行入口**：场景入口、AI 读取顺序、Step 1–9 **工作流总览**（每步解决什么问题、产物、下一步出口）、最小运行心智模型；YAML `description` 补充步骤语义便于路由。
- **docs**: `EXAMPLES.md` 增补 **`pipeline_run_id` → trace → result signal → Step 9 清理** 闭环示例与标准模式最小节奏表；导航表链到 F/G 节。
- **docs**: `ITERATION_GUIDE.md` 增加**防回归**：禁止 `SKILL.md` 退化为「仅 Step 表格 + 外链协议」；协议变更影响 run_id / signal / 归并时须同步示例闭环。
- **fix**: `core/scripts/pipeline_merge.py`：Step 3 输出须含唯一 `PIPELINE_SUMMARY` / `PIPELINE_DETAIL` 标记；检测 **Parent Summary** 误入模块文件则 fail-closed；`PIPELINE_CONTEXT.md` / `PIPELINE_INDEX.md` 使用 **受控 merge 块** 幂等替换，避免重复 append 污染上下文。
- **fix**: `core/hooks/trace-flush.py`：消费 `.pending_pipeline_result.json` 前 **校验** `pipeline_run_id` / `result` / `finalized`；`GO-WITH-CAUTION` + `finalized=false` 保持 `pending-pipeline` 直至最终验收；非法或不完整信号 **不删除文件** 并记日志；实现 `pending-pipeline` 与 `validated:_` 不确定条目的**过期**处理（与 `traces/README.md` 中 limits 字段一致）。
- **docs**: `core/traces/README.md` 补充对 `finalized` 与 component-owned pending 的说明。
- **note**: 模块实现侧术语统一为 **模块配对执行单元**（`programmer-<module>-agent` + 同模块 `programmer-<module>-skill`）；示例中派发表使用 `programmer-m*-agent` 等形式，避免与泛化 `programmer-ui-agent` 混淆。

### CastFlow结构调整

- **rewrite**: 全面重写 `CastFlow/README.md`，与当前仓库真实布局及工作流对齐：定位与四层闭环（冷启动装架 / 渐进式披露 / 多模块编排 / 自我进化）、**端到端案例**（submodule 集成 → `bootstrap castflow` Phase 0–6 → 模块 skill → `code_pipeline` → `origin evolve` → 核心更新）、CastFlow 与用户项目双树目录、**全量文件清单**（`bootstrap-skill/`、`installer/`、`core/`、`bootstrap-assets/`、`test/` 及装架产物职责表）、T1–T4 时点摘要、trace / 五维评分 / 四级 compaction / `origin-evolve-skill` 执行流、CLI 与测试命令。
- **docs**: 明确 **装架与内容生产解耦**：`python .castflow/bootstrap.py` 仅 **Phase A**（同步 `.claude/` 核心、合并根 `CLAUDE.md`、分发 `.claude/templates/`），**不**生成项目级 skill 正文；`architect-skill` / `debug-skill` / `profiler-skill` / `programmer-*-skill` 在 **bootstrap-skill Phase 5** 由主 agent 发「一段话手话」、子代理以 **`skill-creator` 为主路径**落盘，替代旧文档中「安装器从 `content/` 合并生成 skill」的流程描述。
- **docs**: 目录与命名对齐：`CastFlow/bootstrap-skill/` 为顶层 AI 初始化器（`.claude/` 尚不存在时由宿主加载）；`.castflow/bootstrap.py` 为薄入口，实现位于 `.castflow/installer/`；冷启动专用模板在 `.castflow/bootstrap-assets/skill-templates/`（**不分发**到 `.claude/`）；`CLAUDE.template.md` 位于 `.castflow/core/`；创作元规范 `AUTHORING_GUIDE.md` 位于 `.castflow/core/templates/`；自我进化 skill 文档与装架产物统一为 **`origin-evolve-skill`**。
- **docs**: CLI 与交互：`--claude-md-only`、`--templates-only`、`--agent <module>`、`--init-manifest` + `--language`、`--claude-md-harness`（1/2/3）、`--project-root` / 备份相关开关；**已移除** `--skill`、`--strict-content` 及任何 Phase B / 安装器写 skill 正文的叙述；清单 canonical 名为 `bootstrap-output/cf_manifest.json`。
- **docs**: 移除或替换过时锚点：不再以 `CORE_FILE_COPIES` / `CORE_DIR_COPIES` 等内部常量名为用户文档主索引；`CLAUDE.md` 框架段已去掉 `framework_rules` / `project_rules` 占位链路，README 侧与 `CLAUDE.template.md` 及 bootstrap-skill Phase 3 一致（命名约定写入 `naming_conventions` / 项目段）。

### Bootstrap 清单文件名

- **change**: CastFlow 初始化清单 canonical 文件名为 `bootstrap-output/cf_manifest.json`（避免与 Unity `Packages/manifest.json` 等混淆）。仍可读旧版 `bootstrap-output/manifest.json` 并提示迁移。

### 跨平台编码一致性修复

- **fix(P0)**: 剥离全部 18 个模板文件的 UTF-8 BOM（`CLAUDE.template.md`、`agents/programmer.template.md`、`skills/*.template/*.template.md`）。原模板在 Windows 记事本等工具保存时被写入 `\xef\xbb\xbf` BOM，虽然 `bootstrap.py` 的 `read_file` 用 `utf-8-sig` 能剥离，但模板被 `shutil.copy2` 复制或被其他工具链直接读取时仍会把 BOM 当作内容解析，在部分终端/编辑器下显示为乱码。
- **fix(P1)**: `scripts/aggregate_benchmark.py` 中 5 处 `open()` 调用未显式指定 `encoding`：在中文 Windows（默认 cp936/GBK）上读写含中文的 JSON/Markdown 会触发 `UnicodeDecodeError` 或生成 GBK 编码的输出文件。统一改为 `encoding="utf-8"`，写入增加 `newline="\n"` 与 `ensure_ascii=False`，保证跨平台一致。
- **fix(P1)**: `test/hooks/test_evolution.py` 与 `test/hooks/test_365day_simulation.py` 中 4 处 `open(..., "w")` 补齐 `encoding="utf-8", newline="\n"`。
- **verify**: 全仓扫描确认已无文本模式 `open()` 缺失 `encoding=`，全部模板与生成文件均为纯 UTF-8（无 BOM），Windows/Linux/macOS 下 bootstrap 产出的 `CLAUDE.md` 与各 skill 文件字节一致。

### 测试套件目录调整

- **change**: Hooks 相关测试从 `.castflow/core/hooks/` 迁移至 `CastFlow/test/hooks/`（与 `.castflow/` 同级）；`bootstrap.py` 仅向用户项目分发生产脚本 `trace-collector.py` / `trace-flush.py`，不再随 `core/hooks/` 复制测试文件。
- **change**: `verify_redesign.py` 置于 `CastFlow/test/origin-evolve/`，用于 origin-evolve 规范确定性部分的暴力验证；测试通过 `_HOOKS_DIR` 引用 `.castflow/core/hooks/` 中的真实脚本。

### origin-evolve 压缩优化

- **change**: 四个 Skill 文件（SKILL.md / EXAMPLES.md / SKILL_MEMORY.md / ITERATION_GUIDE.md）整体压缩 37% 行数、33% 字符、29% 词数，去除冗余表述，保留全部核心规则。
- **change**: SKILL.md 中 pending 最小条目阈值从 10 降至 5，与 passive trigger 阈值对齐。
- **change**: EXAMPLES.md 从 9 个示例合并为 5 个，移除重复说明。
- **change**: SKILL_MEMORY.md 合并 Rule 5 与 Rule 7，重新编号，check-list 改为内联格式。

### trace-flush.py 健壮性修复

- **fix(P0)**: `apply_pipeline_result()` 中 `result_str` 变量作用域 bug——JSON 解析失败走 fallback 时 `result_str` 未初始化，导致 `UnboundLocalError`。
- **feat(P1)**: compaction Level 1-3 保护 validated 条目（`true` / `false` / `pending-pipeline`），防止用户反馈信号被自动清理。
- **feat(P1)**: 新增 Level 0 阶段——每次 compact 时清理过期的 `PROCESSED` / `COMPACTED` 审计行（`processed_expire_days` 可配）。
- **feat(P2)**: Level 3 compaction 新增 `keep_top_n_per_module` 逻辑，保证每个模块至少保留 N 条最高分条目，防止低频模块的 trace 被全部清除。
- **fix(P2)**: compact 后清理连续空行（3+ 换行压缩为 2 换行），防止反复 append/compact 导致文件膨胀。

### trace-collector.py 语言扩展

- **feat(P2)**: `TRACKED_EXTENSIONS` 从仅 `.cs` 扩展至 18 种主流语言（.ts/.tsx/.js/.jsx/.py/.go/.java/.kt/.rs/.swift/.cpp/.c/.h/.hpp/.lua/.rb/.dart）。

### 测试套件

- **feat**: `test/hooks/test_evolution.py`（84 tests）——基础单元测试，覆盖 collector 采集、buffer 格式、flush 评分、compaction 四级策略、validated 保护、审计行过期、空行清理、被动通知等全部核心路径。
- **feat**: `test/hooks/test_100day_simulation.py`（27 tests）——模拟 100 天连续生产环境，验证 trace 条目在持续 append + compact 下保持有界、模块多样性保留、审计行正确过期、空行不累积。
- **feat**: `test/hooks/test_365day_simulation.py`（23 tests）——模拟 365 天生产环境，含工作日/周末活跃度差异、季度模块焦点漂移、混合会话类型（feature / bugfix / pipeline / trivial chat）、内存知识库模型（规则提取 / 合并 / 退休 / 拒绝记忆），全面验证自进化闭环。
- **feat**: `test/origin-evolve/verify_redesign.py`——origin-evolve 规范确定性部分暴力验证（诊断计数、归因、Append/Merge/Retire、Jaccard 边界、容量策略）。

---

### Rename: CostFlow -> CastFlow

- **breaking**: 项目更名为 CastFlow，README 及所有面向用户的文档统一使用新名称。

### Rename: SKILL_RULE.md -> SKILL_ITERATION.md

- **breaking**: `SKILL_RULE.md` 重命名为 `SKILL_ITERATION.md`，更准确反映其"创建和迭代规范"的定位。
- **change**: bootstrap.py 文件拷贝映射更新。
- **change**: 所有引用（17 个 CastFlow 源文件）全部更新。

### Trace 五维评分模型

- **feat**: 评分模型从"文件数阈值"升级为"五维加权评分"（F/D/K/S/E），准入判断从二元变为连续评分。
- **feat**: K 维度三档分级：Interface=1.0, Implementation=0.6, Base=0.3。
- **feat**: E 维度（编辑密度），捕获同一文件反复修改的困难迭代行为。
- **feat**: buffer 格式 `path|lines|edits|flags`，向后兼容旧格式。
- **feat**: 自动修正检测：collector 对比前后编辑内容，标记 R 标志。flush 自动填充 correction 字段（`auto:minor` / `auto:major`）。
- **feat**: 自校准反馈闭环：flush 读取 `traces/weights.json`，权重和阈值可由 origin-evolve 微调。
- **feat**: hooks 源码移入 `.castflow/core/hooks/`，bootstrap 统一分发。
- **feat**: bootstrap 增量合并 hook 配置到已有的 `.cursor/hooks.json` 和 `.claude/settings.json`，不覆盖原有 hook。

### 知识生命周期管理

- **breaking**: SKILL_ITERATION.md 中 SKILL_MEMORY 条目格式新增 Anchors 和 Related 字段。
- **feat**: SKILL_MEMORY 支持三种写入操作：Append（追加）、Merge（合并）、Retire（退休标记 `[RETIRED]`）。
- **feat**: Anchors 字段记录代码符号锚点，origin-evolve 通过 grep 验证符号是否存在，驱动 Retire 操作。
- **feat**: Related 字段记录关联引用，Merge 时识别候选，Retire 时标记需要连带审查的条目。
- **feat**: 容量治理：写入前检查目标文件字数，超标时强制先 Merge/Retire 腾出空间。
- **feat**: 所有 4 套 ITERATION_GUIDE 模板增加容量治理规则引用。

### origin-evolve 重构

- **change**: SKILL.md 执行流程新增 Step 3 写入前治理（归属决策树 + 操作类型判定 + 容量检查 + 锚点验证）。
- **change**: SKILL_MEMORY.md Rule 2 从抽象归属规则升级为两步决策树（先定 Skill，再定文件）。
- **change**: SKILL_MEMORY.md Rule 3 从 append-only 重写为三种操作（Append/Merge/Retire）。
- **feat**: EXAMPLES.md 新增 Example 7/8/9（复杂度集中检测 + Merge 操作 + Retire 容量治理）。

### 模块 Skill 创建流程

- **change**: 模块 Skill 创建从调用 `bootstrap.py --skill` 改为 `.claude/` 内部闭环：AI 直接读取 `.claude/templates/programmer.template/` 模板并生成。
- **feat**: 区分功能模块 Skill（使用 programmer 模板）和通用职责 Skill（不使用模板，按 SKILL_ITERATION.md 直接创建）。
- **remove**: 不再依赖 `bootstrap-output/content/` 中间产物。

### CLAUDE.md 模板

- **change**: 执行记录段从"AI 全量构造 trace"改为"Hook 自动 + AI 补充"模式。
- **remove**: 旧版手动评分的进化提示逻辑。

---

### 语言选择 (i18n)

- **feat**: 初始化/更新时支持语言选择，默认中文。用户可指定任意语言标识（如 en/ja/ko），影响 Agent 生成的 content 内容语言。
- **feat**: manifest.json 新增 `language` 字段，默认 `"zh"`。
- **feat**: 4 个 Agent prompt（architect/debug/profiler/module）注入 `{LANGUAGE}` 指令，控制 Agent 生成内容的语言。
- **feat**: Phase 2 补充信息收集增加语言选择步骤。
- **design**: 模板固定文本保持中文不变，语言切换仅通过 Agent prompt 控制生成内容。避免双语模板的维护成本。

### bootstrap-skill (prompt + 模板)

- **fix**: architect SKILL.md 模板移除 3 个大型占位符（`CONSTRAINT_RULES_SUMMARY`、`CONSTRAINT_QUERY_TABLE`、`PATTERN_QUERY_TABLE`），SKILL.md 回归"导航文档"定位，字数从 1754 降至 < 800 警戒线内。
- **fix**: architect EXAMPLES.md 模板新增 Part 1 "约束规则速查表"，承接从 SKILL.md 移出的速查表数据。
- **fix**: architect/debug/profiler 三套 SKILL_MEMORY 模板添加 SKILL_RULE 约束注释，明确禁止代码块、目标字数、条目数量限制。
- **fix**: 三个 Agent prompt（architect/debug/profiler）注入 SKILL_RULE 关键约束：文件字数上限、代码块禁令、Emoji 禁令、文件职责隔离规则。修复了 Agent 因缺少约束信息而生成过大内容的问题。
- **remove**: 移除冗余的 `constraint_query_table.md` 和 `pattern_query_table.md` content 文件，其内容与 `constraint_rules_summary` 高度重复。

### bootstrap.py

- **change**: `build_architect_placeholders` 移除 `CONSTRAINT_QUERY_TABLE` 和 `PATTERN_QUERY_TABLE` 两个占位符映射（6 个 content 文件替代原来的 8 个）。
- **fix**: `find_project_root` 不再假设 `.castflow/` 在项目根目录下。支持 CostFlow 作为子目录引入（如 `project/CostFlow/.castflow/`）。通过两轮遍历策略定位项目根：先找 `.claude/`，首次初始化时自动在 CostFlow 父目录创建 `.claude/`。
- **fix**: 新增 `find_harness_dir()` 函数，将"项目根目录"与"框架目录"解耦。所有模板/核心文件读取改为从脚本自身位置定位，不再依赖 `project_root + ".castflow"` 拼接。
- **feat**: 新增 `--project-root` 参数，允许显式指定项目根目录。
- **fix**: CLAUDE.md 模板移除 `## Bootstrap 触发` 段落（用过即知，不需要占空间）。

### code-pipeline-skill

- **fix**: EXAMPLES.md 中 Agent 命名从 `implementer-{module}` 统一修正为 `programmer-{module}-agent`，与 SKILL.md 定义一致（5 处）。
- **fix**: SKILL_MEMORY.md 中 `implementer agent` 引用修正为 `programmer-{module}-agent`（2 处）。

### origin-evolve + hooks（新增）

- **feat**: 新增跨平台 trace 自动采集系统（`.claude/hooks/`），Cursor 和 Claude Code 共用同一套 Python 脚本。
  - `trace-collector.py`: 文件编辑时自动记录，过滤 `.meta/.asset/.prefab` 等非代码文件，去重后追加到 buffer。
  - `trace-flush.py`: Agent 结束时汇总 buffer，自动推断 modules（从路径中提取 `Modules/XXX/`），准入过滤（.cs >= 2 个），生成含分类占位符的 trace 条目。
- **feat**: 四维 trace 分类体系：`type`（任务类型）、`correction`（用户纠正）、`modules`（涉及模块，自动推断）、`skills`（使用的 Skill）。Hook 脚本填充 modules，AI 按 CLAUDE.md 规则补充其余三个维度。
- **feat**: 智能提醒阈值：pending >= 5 条或含修正信号的条目 >= 3 条时触发提醒，纠正记录优先触发分析。（早期文档曾写 10，已与 evolve-reminder / origin-evolve-skill 对齐为 5。）
- **feat**: 平台配置适配：`.cursor/hooks.json`（Cursor）和 `.claude/settings.json`（Claude Code）分别生成，引用同一套脚本。
- **feat**: 会话启动提醒规则：`.cursor/rules/evolve-reminder.mdc` 和 `.claude/rules/evolve-reminder.md`。

### CLAUDE.md 模板

- **change**: `## 执行记录` 从"AI 全量构造 trace"改为"补充式"——Hook 自动创建条目，AI 仅替换 `type`/`correction`/`skills` 占位符，降低遗忘风险和 token 消耗。
- **remove**: 移除 `## Bootstrap 触发` 段落。
