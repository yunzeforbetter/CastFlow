# Code Pipeline README

> 本页只给人看，不作为 AI 运行期整合、调度或验收的规则源。
> `code-pipeline-skill` 是一个复合组件：它组合 shared agents、模块配对执行单元与可选 skill 来完成复杂功能开发，但它本身不是框架根。

## 什么时候用

当需求出现以下信号时，优先考虑进入 `code-pipeline-skill`：

- 3+ 模块协作
- 存在事件、状态、权限等共享契约
- 需要多 agent 并行或分波次推进
- 需要显式的 Handoff、依赖闭合和最终 verdict
- 某个复杂域可能拆成子 pipeline

## 什么时候不用

以下场景通常不值得启 pipeline：

- 单模块小改动
- API 已明确，只是局部实现
- 不需要 Handoff，也不需要 Step 4 / Step 5 质量门
- 只用一个 skill 就能收敛

## 模式选择

| 模式 | 适用场景 | 你下一步该读什么 |
|---|---|---|
| 标准模式 | 单模块、双模块、依赖链短 | `SKILL.md` -> `config/pipeline_protocol.md` -> `config/handoff_protocol.md` |
| 复杂系统模式 | 3+ 模块、共享契约重、容易长时间 churn | `SKILL.md` -> `config/pipeline_protocol.md` -> `architecture/orchestration-model.md` -> 对应主定义页 |

## 你现在该看哪里

- 想判断要不要进 pipeline：本页 + `SKILL.md`
- 想按标准模式执行：`SKILL.md`
- 想看执行期控制：`config/pipeline_protocol.md`
- 想看 Handoff / Closure / Coverage：`config/handoff_protocol.md`
- 想看复杂系统编排：`architecture/*.md`
- 想看输出模板和判例：`EXAMPLES.md` + `examples/*`

## 文件地图

| 层 | 文件 | 用途 |
|---|---|---|
| 入口层 | `README.md` | 人类导航、模式选择、阅读顺序 |
| 工作流层 | `SKILL.md` | AI / 编排者的 Step 1-9 骨架 |
| 规则层 | `SKILL_MEMORY.md` | 必须遵守的硬规则与门禁 |
| 协议层 | `config/pipeline_protocol.md` / `config/handoff_protocol.md` | 执行期控制与模块交接质量门 |
| 架构层 | `architecture/*.md` | 复杂系统模式的主定义页 |
| 示例层 | `EXAMPLES.md` / `examples/*` | 最小模板与高信号判例 |

## 执行单元

| 名称 | 职责 | 典型阶段 | 主要输出 |
|---|---|---|---|
| `requirement-analysis-agent` | 建模、拆分、API 声明、冻结建议 | Step 1 / Step 2 | `Handoff Draft`（`L1+`）或 `No-Handoff Rationale`（`L0`）、Freeze Recommendation、共享契约 |
| 模块配对执行单元 | 按 `module_id` 匹配 `programmer-<module>-agent` 并加载同模块 `programmer-<module>-skill` | Step 3 / Step 6 | 代码、`temp/pipeline-output/{module}.md`、Handoff Update |
| `integration-matching-agent` | 依赖闭合验证 | Step 4 | Dependency Closure Report |
| `pipeline-verify-agent` | 覆盖验收与 verdict | Step 5 | Done Criteria Coverage、Module / Global Verdict |
| `debug-skill` | 边界条件与失败路径验证 | Step 7 | 问题列表与修复建议 |
| `profiler-skill` | 性能诊断 | Step 8 | 性能问题与优化建议 |

## 说明

- `README.md` 与 `architecture/README.md` 都是人类导航页，不是 AI 运行期规则源。
- AI 运行期以 `SKILL.md`、`SKILL_MEMORY.md`、`config/*`、`architecture/*.md` 的主定义页（不含 `architecture/README.md`）以及 `EXAMPLES.md` / `examples/*` 为准。
- agent / skill 的激活依赖元数据，不依赖路径查找。
- **变更记录**：CastFlow 仓库根目录 `CastFlow/CHANGELOG.md` → `## Unreleased` → **code-pipeline-skill 与执行层（真源 `.castflow/core/`）**；与 `pipeline_merge.py`、`trace-flush.py`、`traces/README.md` 相关的行为变更也在该节列出。
