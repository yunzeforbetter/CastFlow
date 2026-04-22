---
name: bootstrap-skill
description: CastFlow framework initializer. Triggered by "bootstrap castflow" or requests to install / initialize / setup / update CastFlow, or to create a module skill. First action MUST be Phase 0 language selection (zh / en / ja / ko / other) before any scan or file write. Distinct from skill-creator which authors individual skills.
---

# Bootstrap-Skill - CastFlow 框架初始化器

## 定位与职责

**定位**：框架安装器。扫描项目结构，通过独立并行 agent 分析生成项目级 Skill，将完整 AI 辅助开发框架安装到 `.claude/`。模块级 Skill 由用户后续按需创建。

**核心职责**：
1. 全量初始化：扫描项目，生成项目级框架文件到 `.claude/`
2. 核心更新：同步 castflow submodule 的核心文件变更
3. 模块 Skill 创建：提供模板和流程，供用户按需为各模块生成 Skill

**执行架构**：主 agent 负责编排（扫描、确认、公共文件、验证），每个 skill 的分析和生成由独立并行 agent 全程闭环处理。

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| Phase 0 / Phase 2 对外话术模板 | EXAMPLES.md#示例-1 |
| cf_manifest.json 字段格式 | EXAMPLES.md#示例-2 |
| content 目录结构与占位符映射 | EXAMPLES.md#示例-3 |
| 模块 Skill 创建对话示例 | EXAMPLES.md#示例-4 |
| 核心更新流程 | EXAMPLES.md#示例-5 |
| 4 个 sub-agent prompt 模板 | `<本 skill 目录>/prompts/{architect,debug,profiler,module}-agent.md` |
| Phase 0 语言门禁规则 | SKILL_MEMORY.md#规则-5 |
| 占位符替换契约 | SKILL_MEMORY.md#规则-9 |
| 文件写入禁令（禁止 shell pipe） | SKILL_MEMORY.md#规则-8 |
| 迭代和维护 | ITERATION_GUIDE.md |

---

## 运行前置（按序加载，进入 skill 第一步）

1. **Read 本 skill 同目录的 `EXAMPLES.md` 示例 1**
   -> 获取 Phase 0 / Phase 2.1 / Phase 2.2 三段对外话术模板与默认值。**未完成此步禁止输出第一条对外消息。**
2. 检查 `bootstrap-output/cf_manifest.json` 是否存在（**勿**用项目根或其它目录的 `manifest.json` 判断，例如 Unity `Packages/manifest.json`），决定走哪条工作流：
   - 不存在 -> 全量初始化工作流
   - 存在 + 用户指令含"更新核心" -> 核心更新工作流（复用 manifest.language，告知"复用已有配置 language=xxx"）
   - 存在 + 用户在触发指令同句已指定语言 -> 全量初始化工作流，但 Step 0 改为复述确认（"已识别语言：xxx，确认继续？"）
   - 存在 + 普通触发 -> 询问用户「重新初始化 / 复用已有配置」后再决定走向

---

## 工作流：全量初始化

**适用场景**：首次在项目中引入 CastFlow 框架。
**前提条件**：项目已添加 castflow 为 git submodule（位于 `.castflow/`），项目有实际源代码。

**Step 0**：Phase 0 语言询问（首条对外消息）
- 输入：EXAMPLES.md 示例 1#Phase 0 模板
- 动作：**逐字输出**语言询问菜单，等待用户回复
- 产出：`manifest.language`（写入内存，未落盘）
- 禁止：任何文件扫描 / 读取 / 写入（除运行前置 Step 1 已 Read 的 EXAMPLES.md）
- **与 `bootstrap.py` 的关系**：`CastFlow/.castflow/bootstrap.py` **不包含**语言交互；Phase 0 只由**本 skill 的执行者**通过对话完成。仅运行脚本的用户须事先有 `bootstrap-output/cf_manifest.json`（或 `py -3 ... --init-manifest --language <码>` 生成缺省，再与 Phase 0 结果对齐/编辑 `language`）。

**Step 1**：项目扫描
- 动作：扫描技术栈、命名规范、项目规模
- 产出：扫描结果（用于 Step 2 输出展示）

**Step 2**：用户确认（两条独立消息，固定顺序）
- 2.1 输入 EXAMPLES.md 示例 1#Phase-2.1 模板 -> 输出 Skill 选择询问（debug / profiler 可选项 + 默认值），等待用户一次回复
- 2.2 输入 EXAMPLES.md 示例 1#Phase-2.2 模板 -> 输出命名规范确认 + 框架规则补充询问，等待用户一次回复
- 产出：`optional_skills` + `naming_conventions` + `framework_rules`
- 禁止：合并 2.1 与 2.2 为一条消息；省略默认值标注

**Step 3**：公共文件处理
- 命令：
  ```
  python .castflow/bootstrap.py --skill core
  python .castflow/bootstrap.py --skill claude
  python .castflow/bootstrap.py --skill templates
  ```
- 产出：`bootstrap-output/cf_manifest.json` + `bootstrap-output/content/claude/` + `.claude/skills/protocols/` 等核心文件

**Step 4**：并行 sub-agent 闭环生成
- 主 agent 一条消息内同时发射所有 agent，每个 agent 独立完成"分析 -> 写 content -> bootstrap.py --skill {type} -> .claude/skills/ 落盘"
- 读取本 skill 目录下的 `prompts/{architect,debug,profiler}-agent.md` 作为 prompt 模板
- 按下表替换占位符后并行发射（**未替换的字面量会泄漏到 sub-agent 提示词**）：

  | 占位符 | 来源 | 备注 |
  |-------|------|------|
  | `{TECH_STACK}` | manifest.tech_stack | 例如 `unity` |
  | `{SOURCE_DIR}` | Step 1 扫描结果 | 例如 `Assets/Scripts` |
  | `{PROJECT_ROOT}` | 当前工作目录 | 绝对路径 |
  | `{LANGUAGE}` | manifest.language 经映射 | `zh` -> `中文` / `en` -> `English` / `ja` -> `日本語` / `ko` -> `한국어` |

  模块 Skill prompt 额外有 `{MODULE_ID}` / `{MODULE_NAME}` / `{MODULE_DIR}`。

**Step 5**：验证与清理
- `python .castflow/bootstrap.py --validate`
- 删除 `bootstrap-output/`

---

## 工作流：核心更新

**适用场景**：castflow submodule 有新版本。**触发**："bootstrap 更新核心"。

**Step 0**：复用 manifest.language，告知用户"复用已有配置 language=xxx"
**Step 1**：对比 `.castflow/core/` 与 `.claude/skills/` 的核心文件
**Step 2**：更新核心文件 -> SKILL_ITERATION、GLOBAL_SKILL_MEMORY、protocols/、code-pipeline-skill、skill-creator、origin-evolve、bootstrap-skill 自身
**Step 3**：保留项目专属文件 -> CLAUDE.md（按交互式合并策略）、architect-skill、programmer-* skills、debug-skill、profiler-skill、`.claude/agents/` 中的项目自建 agent
**Step 4**：更新 `.claude/templates/` 中的模板文件

详细对话见 EXAMPLES.md#示例-5。

---

## 工作流：模块 Skill 创建（初始化后使用）

**触发**："为xxx系统生成 skill" / "为 Assets/Scripts/XXX/ 创建 skill" 等自然表述。

**模板选择**：

| 用户意图 | Skill 类型 | 模板 |
|---------|-----------|------|
| 为某个代码模块创建 Skill（有具体代码目录、Manager/Controller/Handler 等核心类） | 功能模块 | `.claude/templates/programmer.template/` |
| 创建通用职责 Skill（如安全审查、日志规范） | 自由格式 | 无模板，AI 按 SKILL_ITERATION.md 直接创建四文件 |

**功能模块流程**：
1. 主 agent 确认模块 ID、显示名、主要代码目录
2. 主 agent 读取本 skill 目录下的 `prompts/module-agent.md`，替换 `{MODULE_ID}` / `{MODULE_NAME}` / `{MODULE_DIR}` / `{LANGUAGE}` 后启动独立 agent 闭环
3. 主 agent 验证 `.claude/skills/programmer-{MODULE_ID}-skill/` 4 个文件存在且符合 SKILL_ITERATION 字数标准

并发：同时创建多个模块 Skill 时并行发射多个 agent。

**关于 programmer-agent**：模块 Skill 创建时**不生成** agent。agent 价值在于隔离上下文（pipeline 多模块并行），日常使用 skill 即可。code-pipeline 运行时如需会按需提议创建（详见 code-pipeline-skill）。
