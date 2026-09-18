# bootstrap-skill-memory - 初始化硬性规则

**本文档的性质**：硬性约束（必须遵守）。约束全量初始化和核心更新。

---

### 规则 1：不覆盖已有文件

**定义**：生成文件前必须检查目标路径是否已有文件。已有文件不覆盖，除非用户明确要求。

**检查清单**：
- [ ] 是否检查了 CLAUDE.md 是否已存在？
- [ ] 是否检查了 `.castflow-runtime/skills/` 下是否有同名 skill？（不要只看适配器镜像）
- [ ] 已有文件是否跳过或提示用户？

---

### 规则 2：生成文件必须符合 SKILL_ITERATION.md

**定义**：四角色文件按 `SKILL_ITERATION.md` 写。机器检查跑 `python .castflow/manager.py validate`，不要再跑文档里的 bash 剧本（已删除）。

**检查清单**：
- [ ] 四角色文件齐全？附件仅在有链路用途时存在，且无无用 markdown？
- [ ] SKILL.md description 短、专名触发、一句 NOT（非关键词堆砌、非 pushy 扩词）？
- [ ] `python .castflow/manager.py validate` 通过？

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

### 规则 5：冷启动走 GUI，禁止 AI 代跑装架（最高优先级）

**定义**：bootstrap-skill 触发后，主 agent **不得**自己执行 seed，也 **不得**再做 Phase 0 语言询问（语言在 GUI 里选）。第一条对外消息必须是：请用户双击 `castflow.bat`（或 `python .castflow/manager.py launch`），在浏览器里完成配置并点「开始冷启动」。

**违反此规则视为执行失败**（包括：代跑 manager.py seed、先问语言再动手）。未勾选时禁止自己扫目录列模块；勾选并粘贴提示词后，读取提示词给出的文件并按文件执行。

**强制顺序**：
1. **GUI**：`castflow.bat` / `manager.py launch` → 用户选语言/适配器/进化 → 开启冷启动（只拷文件）。
2. **未勾选扫描生成**：不要扫项目，不要写 programmer skill，没有交接提示词。
3. **勾选并粘贴了提示词**：默认是 `/goal 读取并按照 .castflow-runtime/skills/MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md 执行`。`/goal` 启动长任务；读取该文件并按文件执行。禁止扫描 CastFlow / `.castflow` / `.castflow-runtime` / 适配器树，禁止把框架 skill 放进多选。禁止 Python scan，禁止扫描账本状态机（`STATE.yaml` 等）。勾选后只落临时生成队列 `.castflow-runtime/_skill-gen-queue/`（一次一个 skill，全部完成后删除），禁止写适配器镜像。
4. **进化**：只通过 `manager.py evolve on|off` 或 UI 开关。

**门禁规则**：
- 未完成 GUI 装架 -> 不得自己 seed
- 用户没要求扫描生成 -> 不得扫树、不得写模块 skill
- 用户要求扫描生成 -> 不得用「没有 .cs / Scripts / 每目录 3 文件」当拒绝理由
- 扫描生成 -> 不得把 AI 框架（CastFlow / `.castflow` / `.castflow-runtime` / `.claude` 等）当模块选项
- 生成必须走 skill-creator，禁止评测环，禁止写入镜像目录

**唯一例外**（仍需主 agent 显式说明）：
- 用户在触发指令同一句话已指定语言：复述确认后再 seed
- 已有 `.castflow-runtime/config.json`：复用 language，告知用户

**检查清单**：
- [ ] 第一条对外消息是否是语言询问？
- [ ] 是否列出 zh/en/ja/ko/其他？
- [ ] 语言是否归一化为 ISO 639-1？
- [ ] 未勾选时是否避免了自己列模块？勾选后是否走扫描->多选->落地队列->清上下文->一次一个生成，而不是 Python scan 或并行子代理？

---

### 规则 6：一次只生成一个 skill

**定义**：生成 skill 同一时刻只允许 1 个。两条路径不要并行、不要混在同一回合。

1. **模块 skill（粘贴 `/goal`）**：按 `MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md`。勾选后落 `.castflow-runtime/_skill-gen-queue/`，一次只读一张 `status: pending` 卡，写完 validate/sync 后标 `done`，清上下文，再读下一张。全部完成后删除该目录。
2. **architect / debug / profiler（GUI JSON 队列或 `castflow generate skills`）**：只处理队列第一项 queued，写完即停。下一轮再取下一项。

**检查清单**：
- [ ] 本回合是否只写一个 skill 根目录？
- [ ] `/goal` 路径是否从 yaml 卡读，而不是凭记忆或 JSON catalog？
- [ ] 是否禁止并行生成子代理？

---

### 规则 7：子任务手话自包含

**定义**：启子代理时，**传给子代理的那一段话**里必须带齐信息，**不可**假设子代理能自动看到主会话全文。子代理将按手话用 **skill-creator** 执行；**具体产出文件名与结构不写在手话里**——以子代理**必读**的 `SKILL_ITERATION.md` 为准。

**手话必含**（可一段写清）：
- 任务、技术栈、代码根、**产出 skill 根目录**（如 `项目/.castflow-runtime/skills/architect-skill/`，只到目录）
- 必读：`SKILL_ITERATION.md`。模块 skill 不要读域 README / `*.template.md`。architect/debug/profiler 的 YAML 召回句只取对应 `SKILL.template.md`
- 语言（`{LANGUAGE}` 实值化）

**检查清单**：
- [ ] 技术栈、代码根、**产出 skill 根目录**是否写清？
- [ ] 必读是否按 `SKILL_ITERATION` 栈（harness `.castflow/...`）而非臆造路径？
- [ ] 手话里**未**罗列四 md 文件名？
- [ ] `{LANGUAGE}` 等占位符是否已换实值？
- [ ] 是否只开了一个生成子代理，并等它结束后才开下一个？

**原因**：子代理为独立上下文；自包含手话是 skill-creator 正确起动的输入。

---

### 规则 8：文件写入必须用 Write 工具（禁止 shell 管道）

**定义**：skill 四角色文件、队列 yaml、CLAUDE.md 草稿等的写入，必须使用 AI 内置的 Write/Edit 工具直接写入，**严禁使用 shell + python pipe / cat heredoc / echo 重定向 / cmd /c "type ..." 等任何形式的命令行写文件**。

**原因**：
1. Cursor 对每个 shell 命令都会弹审批对话框，10 个 md 文件就要点 10 次审批，用户体验极差
2. shell 写入存在编码、引号转义、换行符等多种坑，Write 工具无这些问题
3. shell 写入的内容不在 Cursor 的 diff 视图中显示，用户无法预览

**冷启动中推荐的 shell/装配调用**：
- 装架走 GUI（`castflow.bat` / `manager.py launch`）。不要代跑 seed。
- 写 skill 用 Write 工具落到 `.castflow-runtime/skills/<name>/`，再 `python .castflow/manager.py validate` 与 `sync`
- 模块 skill 按 loop-engine 一次一个；不要并行子代理，不要写 `bootstrap-output/content/`

**检查清单**：
- [ ] 写 `.castflow-runtime/skills/<name>/` 四角色文件是否用了 Write 工具？
- [ ] 写 `_skill-gen-queue/` 是否用了 Write 工具？
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

**防护**：模块定义见 `.castflow/core/rules/module-catalog.md`。用户要求全库扫描时按功能归类，不要按每个子目录拆 skill。工具类不应独立成 skill。建议 3-8 个模块。

### 陷阱 1b：把 AI 框架扫成模块

**现象**：多选框里出现 CastFlow、installer、manager、hooks、bootstrap-skill、skill-creator、origin-evolve 等选项。

**防护**：粗扫前先跳过 `CastFlow/` `.castflow/` `.castflow-runtime/` `.claude/` `.agents/` `.cursor/` `.grok/` 和根 `bootstrap-skill/`。框架 skill 已经装架，不要再生成 programmer skill。扫描范围只剩用户项目的业务脚本。

### 陷阱 2：命名规范检测不准

**现象**：采样的代码文件包含第三方库或生成代码，导致命名规范检测偏差。

**防护**：采样时排除 Packages/、node_modules/、vendor/、generated/ 等目录。优先从项目主代码目录采样。

### 陷阱 3：生成的 EXAMPLES.md 内容为空

**现象**：模板中的代码示例部分没有从项目中提取真实代码，只有占位注释。

**防护**：生成的 `EXAMPLES.md` 须用 Grep/Read 从该模块脚本拉真实代码。若无法提取，在示例中标注 TODO 并告知用户。不要读域 README 凑例子。

### 陷阱 4：核心文件更新时覆盖了项目定制

**现象**：运行"更新核心"时，覆盖了用户在 CLAUDE.md 或 skill 文件中的手动修改。

**防护**：更新核心仅更新来自 .castflow/core/ 的文件，不触碰生成的或用户修改的文件。

### 陷阱 5：子任务手话信息不全

**现象**：启子代理时手话里缺技术栈、代码根、目标 skill 根目录，或 `{LANGUAGE}` 未替换，导致 skill-creator 落点或语言错。**最常见**是 `{LANGUAGE}` 未换实值，非中文 manifest 仍产出中文。

**防护**：严格按 SKILL.md 占位符表，保证 `{TECH_STACK}` / `{SOURCE_DIR}` / `{PROJECT_ROOT}` / `{LANGUAGE}` 等全部实值化；`{LANGUAGE}` 用 ISO → 自然名（zh→中文、en→English 等）。

---
