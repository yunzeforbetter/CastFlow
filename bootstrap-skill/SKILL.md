---
name: bootstrap-skill
description: bootstrap castflow install init setup update submodule .castflow bootstrap.py scaffold CLAUDE.md Phase0 language cf_manifest cold start Phase5 skill-creator module skill NOT merge skill meta-spec
---

# bootstrap-skill

**作用**：装架 CastFlow 到项目 `.claude/`；**project/模块 skill** 只在 Phase 5 用 **子代理 + skill-creator** 写。

**铁律**（与 SKILL_MEMORY 规则 5 一致）：主 agent **第一条对外消息**只能是 Phase 0 语言询问；该步之前**禁止**扫项目、读除 EXAMPLES 外文件、写盘。

**职责**：(1) 全量初始化 (2) 核心更新 (3) 给模块 skill 提供流程与模板入口。

**要点**：装架后项目里有 `skill-creator`。Phase 5 手话不抄路径表、不枚举四文件名；子代理由 harness（`.castflow/...`）读规范，产出写到 `项目/.claude/skills/<name>/`。

**必读（读 harness 源，与装架后项目内 `.claude/...` 为同内容拷贝）**  
见 [`../.castflow/core/skills/SKILL_ITERATION.md` → 必读资料栈（创建与冷启动统一）](../.castflow/core/skills/SKILL_ITERATION.md#必读资料栈创建与冷启动统一)（含 `AUTHORING`、域 `README`、`.template.md` 约定）。

---

## 快速导航

| 要查 | 位置 |
|------|------|
| Phase 0/2/3 话术 | EXAMPLES.md#示例-1 |
| cf_manifest、content 占位 | EXAMPLES.md#示例-2、#示例-3 |
| 模块 skill 对话例 | EXAMPLES.md#示例-4 |
| 核心更新 | EXAMPLES.md#示例-5 |
| 域模板（architect/debug/profiler） | `../.castflow/bootstrap-assets/skill-templates/<域>.template/` + 各目录 `README.md` |
| 模块模板 programmer | `../.castflow/core/templates/skills/programmer.template/`（装架后：`项目/.claude/templates/skills/programmer.template/`） |
| Phase 5 手话 + skill-creator | 上节链到 `SKILL_ITERATION`；见下 **Phase 5** |
| 硬规则 | SKILL_MEMORY.md |
| 维护 | ITERATION_GUIDE.md |

---

## 运行前置

1. 先读同目录 `EXAMPLES.md` 示例 1（Phase 0/2/3 话术），**再发第一条对外消息**。
2. 看 `bootstrap-output/cf_manifest.json` 是否存在，决定全量 / 复用 / 更新（见 SKILL_MEMORY）。

---

## 全量初始化

**前提**：castflow 为 submodule（`.castflow/`），项目有源码。

- **Phase 0**：语言菜单，等用户；不落盘。脚本不管语言，见 EXAMPLES。
- **Phase 1**：扫技术栈、规模、目录。
- **Phase 2**：debug/profiler 开关（一条消息）。
- **Phase 3**：命名规范（接在 Phase 2 后，单条消息）。
- **Phase 4**（仅装架，一条命令）  
  `python .castflow/bootstrap.py`  
  同步到**项目** `.claude/`、`CLAUDE.md`、`.claude/templates/`；**不**生成 architect/debug/profiler/programmer-* 正文。  
  主命令前需已有 `cf_manifest.json` 与 `content/claude/`。  
  可选：`--claude-md-only` / `--templates-only`。  
  验收：装架后项目内存在从 core 同步的元规范、protocols、templates、`skill-creator` 等（以实际仓库为准）。

- **Phase 5**（**禁止**用 `bootstrap.py` 代写 project skill）  
  - 子任务：**子代理 + skill-creator**，产出 `项目/.claude/skills/<name>/`。  
  - 子代理**必读**以 [`SKILL_ITERATION` 必读栈](../.castflow/core/skills/SKILL_ITERATION.md#必读资料栈创建与冷启动统一) 为准（harness 路径在表内、含 `.castflow/core` 与 `bootstrap-assets`）。  
  - 主 agent **一段话**含：目标 skill 名、语言、实值化的栈/目录/`{HARNESS}` 等；**不**列四文件名。规则 9：SKILL_MEMORY。

- **Phase 6**：`python .castflow/bootstrap.py --validate`，可删 `bootstrap-output/`。

---

## 核心更新

触发如「更新核心」。复用 `manifest.language` → 对比 **`.castflow/core/` 与已装项目 `.claude/`** → 合入上游变更、保留项目专属 skill/agent → 更 `.claude/templates/`。细目：EXAMPLES#示例-5。

---

## 装架后：模块 skill

| 意图 | 模板源（harness） | 落点 |
|------|-------------------|------|
| 具体代码模块 | `../.castflow/core/templates/skills/programmer.template/` + skill-creator | `项目/.claude/skills/programmer-<id>-skill/` |
| 无域模板 | skill-creator + `SKILL_ITERATION` | 同上结构 |

手话同 Phase 5；不生成 programmer-agent 除非另有流程需要。
