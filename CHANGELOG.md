# Changelog

## Unreleased

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
- **feat**: 智能提醒阈值：pending >= 10 条或含用户纠正的条目 >= 3 条时触发提醒，纠正记录优先触发分析。
- **feat**: 平台配置适配：`.cursor/hooks.json`（Cursor）和 `.claude/settings.json`（Claude Code）分别生成，引用同一套脚本。
- **feat**: 会话启动提醒规则：`.cursor/rules/evolve-reminder.mdc` 和 `.claude/rules/evolve-reminder.md`。

### CLAUDE.md 模板

- **change**: `## 执行记录` 从"AI 全量构造 trace"改为"补充式"——Hook 自动创建条目，AI 仅替换 `type`/`correction`/`skills` 占位符，降低遗忘风险和 token 消耗。
- **remove**: 移除 `## Bootstrap 触发` 段落。

### README.md

- **rewrite**: 自我进化章节重写，反映两层数据采集架构（Hook 零 token + AI 补充）和四维分类体系。
- **update**: 安装方式更新，说明支持子目录引入和 `--project-root` 参数。
- **update**: 文件结构图新增 `.claude/hooks/`、`.claude/settings.json`、`.cursor/hooks.json`。
- **update**: 技术细节新增 Hook 脚本协议说明和 bootstrap.py 项目根检测逻辑。
