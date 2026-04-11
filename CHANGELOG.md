# Changelog

## Unreleased

### bootstrap.py

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
