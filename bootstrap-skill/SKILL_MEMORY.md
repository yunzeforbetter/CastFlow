# bootstrap-skill-memory - 初始化硬性规则

**本文档的性质**：硬性约束（必须遵守）。约束全量初始化和核心更新。

---

### 规则 1：不覆盖已有文件

**定义**：生成文件前必须检查目标路径是否已有文件。已有文件不覆盖，除非用户明确要求。

**检查清单**：
- [ ] 是否检查了 CLAUDE.md 是否已存在？
- [ ] 是否检查了 .claude/skills/ 下是否有同名 skill？
- [ ] 是否检查了 .claude/agents/ 下是否有同名 agent？
- [ ] 已有文件是否跳过或提示用户？

---

### 规则 2：生成文件必须符合 SKILL_ITERATION.md

**定义**：所有生成的 Skill 文件必须通过 SKILL_ITERATION.md 的规范检查。

**检查清单**：
- [ ] 每个 skill 目录恰好 4 个 .md 文件？
- [ ] SKILL.md 有 YAML 元数据（name + description）？
- [ ] 无 Emoji 和特殊符号？
- [ ] 无日期/版本标记？

---

### 规则 3：模板占位符必须全部替换

**定义**：生成文件中不能残留未替换的模板占位符。

**检查清单**：
- [ ] 搜索 `{{` 确认无残留占位符？
- [ ] 所有 MODULE_ID / MODULE_DISPLAY_NAME 等都已替换？

---

### 规则 4：参考路径必须真实存在

**定义**：生成的 EXAMPLES.md 中引用的文件路径和类名必须在项目中真实存在。

**检查清单**：
- [ ] 是否用 Grep/Find 验证了参考路径？
- [ ] 不确定的引用是否标注了 TODO？

---

### 规则 5：Phase 0 语言询问门禁（最高优先级）

**定义**：bootstrap-skill 触发后，主 agent 的**第一条对外消息必须是 Phase 0 语言询问**——使用 SKILL.md 给定的标准话术，列出 5 个语言选项。在用户回复前，禁止做任何项目扫描、文件读取、文件写入。

**违反此规则视为执行失败**，无论生成结果质量如何。

**强制顺序**：
1. **Phase 0**：发出语言询问 -> 等待用户回复 -> 归一化为 ISO 639-1 代码 -> 回显确认（"已选 English (en)，开始扫描..."）
2. **Phase 1**：项目扫描（技术栈、命名规范、模块）
3. **Phase 2**：可选 Skill 确认（debug / profiler 一条消息内列完，一次回复；architect 固定生成、不询问）
4. **Phase 3**：命名规范与框架规则（单独一条消息，须在 Phase 2 之后）
5. **Phase 4**：写 `cf_manifest.json` 与 `content/claude/`，并执行**仅** `python .castflow/bootstrap.py`（安装器 Phase A 装架，拷核心与模板；**不**用脚本生成 project 级 skill 正文）
6. **Phase 5**：装架后 `skill-creator` 可加载。主 agent 一段手话：任务 + 语言 + 实值占位符；**必读**按 `.castflow/core/skills/SKILL_ITERATION.md` 中「必读资料栈」（源在 `.castflow/core/`、`bootstrap-assets/`，非手搓 `.claude/` 路径当「源」）。产出仍在**项目** `.claude/skills/<name>/`；**不**枚举四文件名；**禁止** `bootstrap.py` 代写 project skill
7. **Phase 6**：`bootstrap.py --validate` 与清理 `bootstrap-output/`（验证可用脚本）

**交互频次约束**（减少用户点击负担）：
- Phase 2 **不允许**逐个 skill 提问；可选 skill（debug/profiler）必须在一条消息内列完让用户一次回复
- 违反示例：先问 "debug 要吗？" 等回复 -> 再问 "profiler 要吗？" 等回复（每多一次来回都是一次不必要的用户中断）

**门禁规则**：
- Phase 0 未完成 -> 不得进入 Phase 1
- Phase 2 或 Phase 3 未确认 -> 不得进入 Phase 4
- 不得在任何用户确认与 manifest 落盘之前执行 `bootstrap.py` 的**装架**；Phase 4 的 `python .castflow/bootstrap.py` 须在 manifest 与 `content/claude/` 就绪后执行
- 冷启动 Phase 5：须经 **子代理 + skill-creator** 在 `.claude/skills/` 下生成；`bootstrap.py` 仅做装架（与可选 `--claude-md-only` / `--templates-only`），不生成 project/模块 skill

**唯一例外**（仍需主 agent 显式说明）：
- 用户在触发指令同一句话已指定语言：复述确认（"已识别语言：English (en)，确认继续？"）后再进入 Phase 1
- 核心更新模式且 `bootstrap-output/cf_manifest.json` 已存在：直接复用 manifest.language，但需告知用户"复用已有配置 language=xxx"

**检查清单**：
- [ ] 主 agent 触发后的**第一条消息**是否是语言询问？（不是"开始扫描"、不是 Phase 1 输出）
- [ ] 询问话术是否包含了 5 个选项（zh/en/ja/ko/其他）？
- [ ] 用户回答是否归一化为 ISO 639-1 代码？（"用英文" -> `en`，不是 `用英文`）
- [ ] 归一化后是否给用户回显确认？
- [ ] 是否等待了 Phase 2、Phase 3 各自的用户回应？
- [ ] cf_manifest.json 写入时 language 字段是否为 ISO 代码？

---

### 规则 6：并行 agent 独立性

**定义**：Phase 5 的每个子任务（子代理 + skill-creator）必须完全独立，不依赖其它并行任务的产出。

**检查清单**：
- [ ] 每个子任务是否只产出一个 skill 根目录？（如 architect 只动 `.claude/skills/architect-skill/`，不覆盖其它 skill）
- [ ] 各子任务是否不依赖其它子任务输出目录中的内容？
- [ ] 多个子任务之间是否无强顺序依赖？
- [ ] 单个子任务失败是否不阻断其它子任务（若可并行）？

**原因**：独立性是并行执行的前提。如果 agent 之间有依赖，就必须串行执行，失去并行优势。

---

### 规则 7：子任务手话自包含

**定义**：启子代理时，**传给子代理的那一段话**里必须带齐信息，**不可**假设子代理能自动看到主会话全文。子代理将按手话用 **skill-creator** 执行；**具体产出文件名与结构不写在手话里**——以子代理**必读**的 `SKILL_ITERATION.md` 为准。

**手话必含**（可一段写清）：
- 任务、技术栈、代码根、**产出 skill 根目录**（如 `项目/.claude/skills/architect-skill/`，只到目录）
- 必读：按 `SKILL_ITERATION` 必读栈开读；文件在 **harness** `.castflow/core/`、`.castflow/bootstrap-assets/` 等（装架后项目内有 `.claude/` 同步副本，以栈为准）
- 语言（`{LANGUAGE}` 实值化）

**检查清单**：
- [ ] 技术栈、代码根、**产出 skill 根目录**是否写清？
- [ ] 必读是否按 `SKILL_ITERATION` 栈（harness `.castflow/...`）而非臆造路径？
- [ ] 手话里**未**罗列四 md 文件名？
- [ ] `{LANGUAGE}` 等占位符是否已换实值？
- [ ] 子代理是否不依赖其它并行子任务的中间文件？

**原因**：子代理为独立上下文；自包含手话是 skill-creator 正确起动的输入。

---

### 规则 8：文件写入必须用 Write 工具（禁止 shell 管道）

**定义**：所有 `bootstrap-output/content/**/*.md` 文件、`bootstrap-output/cf_manifest.json`、CLAUDE.md 草稿等的写入，必须使用 AI 内置的 Write/Edit 工具直接写入，**严禁使用 shell + python pipe / cat heredoc / echo 重定向 / cmd /c "type ..." 等任何形式的命令行写文件**。

**原因**：
1. Cursor 对每个 shell 命令都会弹审批对话框，10 个 md 文件就要点 10 次审批，用户体验极差
2. shell 写入存在编码、引号转义、换行符等多种坑，Write 工具无这些问题
3. shell 写入的内容不在 Cursor 的 diff 视图中显示，用户无法预览

**冷启动中推荐的 shell/装配调用**（须符合 Phase 4/6）：
- `python .castflow/bootstrap.py`（Phase A 装架，拷核心与模板；**唯一**应在冷启动里为「装架」而跑的主命令；**无** `--skill` 等易混淆参数）
- `python .castflow/bootstrap.py --validate`（验收）
- 可选：`--claude-md-only` 或 `--templates-only` 仅做 Phase A 子步；project/模块 skill 由 Phase 5 子代理经 **skill-creator** 落盘
- `mkdir ...`（仅在确需建目录时）

**检查清单**：
- [ ] 写 content/*.md 是否用了 Write 工具？
- [ ] 写 cf_manifest.json 是否用了 Write 工具？
- [ ] 是否避免了 `python -c "open(...).write(...)"` 这种命令行写法？
- [ ] 是否避免了 `cat <<EOF > file` 这种 heredoc 写法？

**违反此规则的代价**：用户每个文件都要点一次审批，10+ 文件 = 10+ 次中断，bootstrap 体验劣化为"半自动"。

---

### 规则 9：委派子任务时任务说明中的占位符必须全部替换

**定义**：发射或委派子任务前，任务说明里出现的 `{TECH_STACK}` / `{SOURCE_DIR}` / `{PROJECT_ROOT}` / `{LANGUAGE}` / `{MODULE_*}` 等**必须**全部换成实际值，禁止把未替换的占位符交给执行方（不再依赖已删除的 `bootstrap-assets/prompts/*.md` 长模板）。

**关键映射**：
- `{LANGUAGE}` 注入的是**自然语言名称**（`中文` / `English` / `日本語` 等），不是 ISO 代码（`zh` / `en` / `ja`）。映射规则见 SKILL.md 全量初始化中占位符表与 Phase 0 说明。

**检查清单**：
- [ ] grep prompt 字符串中是否还有残留的 `{TECH_STACK}` / `{SOURCE_DIR}` / `{PROJECT_ROOT}`？
- [ ] grep 是否还有残留的 `{LANGUAGE}`（最常被遗漏）？
- [ ] 模块流程是否替换了 `{MODULE_ID}` / `{MODULE_NAME}` / `{MODULE_DIR}`？
- [ ] 替换 `{LANGUAGE}` 时是否经过 ISO -> 自然名映射？

**原因**：bootstrap-skill 不经过 bootstrap.py 的 `replace_placeholders` 处理，占位符替换完全由主 agent 负责。任何遗漏都会导致 sub-agent 看到字面 `{LANGUAGE}` 而退化到默认中文输出，多语言配置失效。

---

## 常见陷阱

### 陷阱 1：模块识别过细

**现象**：把每个子目录都识别为独立模块，导致生成大量碎片化的 skill 和 agent。

**防护**：模块应该是有独立职责的顶层功能单元。子模块、工具类不应独立成 skill。建议 3-8 个模块为宜。

### 陷阱 2：命名规范检测不准

**现象**：采样的代码文件包含第三方库或生成代码，导致命名规范检测偏差。

**防护**：采样时排除 Packages/、node_modules/、vendor/、generated/ 等目录。优先从项目主代码目录采样。

### 陷阱 3：生成的 EXAMPLES.md 内容为空

**现象**：模板中的代码示例部分没有从项目中提取真实代码，只有占位注释。

**防护**：Phase 5 经 skill-creator 产出的 `EXAMPLES.md`（名以 `SKILL_ITERATION` 为准）中，须用 Grep/Read 从项目拉至少 3 个真实代码示例。若无法提取，在示例中标注 TODO 并告知用户。

### 陷阱 4：核心文件更新时覆盖了项目定制

**现象**：运行"更新核心"时，覆盖了用户在 CLAUDE.md 或 skill 文件中的手动修改。

**防护**：更新核心仅更新来自 .castflow/core/ 的文件，不触碰生成的或用户修改的文件。

### 陷阱 5：子任务手话信息不全

**现象**：启子代理时手话里缺技术栈、代码根、目标 skill 根目录，或 `{LANGUAGE}` 未替换，导致 skill-creator 落点或语言错。**最常见**是 `{LANGUAGE}` 未换实值，非中文 manifest 仍产出中文。

**防护**：严格按 SKILL.md 占位符表，保证 `{TECH_STACK}` / `{SOURCE_DIR}` / `{PROJECT_ROOT}` / `{LANGUAGE}` 等全部实值化；`{LANGUAGE}` 用 ISO → 自然名（zh→中文、en→English 等）。

---
