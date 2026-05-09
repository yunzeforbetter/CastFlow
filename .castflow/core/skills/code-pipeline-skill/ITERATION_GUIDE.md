# ITERATION_GUIDE - Code Pipeline Skill

## Skill 定位

`code-pipeline-skill` 只做流程编排，不做具体业务实现。

## 迭代规则

### 规则 1：工作流骨架变化

- 触发条件：Step 增减、入口条件变化、质量门变化
- 优先修改：`SKILL.md`
- 联动检查：`SKILL_MEMORY.md`、`config/*`、`EXAMPLES.md`
- 额外要求：`SKILL.md` 必须保留标准模式可执行的逐步流程说明；禁止退化成“只有 Step 表格 + 去别处看协议”

### 规则 2：执行期协议变化

- 触发条件：PCB、run_id、复杂系统产物、Step 3 归并规则变化
- 优先修改：`config/pipeline_protocol.md`
- 联动检查：`SKILL.md`、`SKILL_MEMORY.md`、`EXAMPLES.md`
- 额外要求：若协议变更影响 `pipeline_run_id`、result signal、Step 3 归并或 Step 9 清理，`EXAMPLES.md` 必须保留至少一个端到端闭环示例

### 规则 3：Handoff 机制变化

- 触发条件：Level、Freeze、Closure、Coverage、`Parent Summary` 变化
- 优先修改：`config/handoff_protocol.md`
- 联动检查：`SKILL.md`、`SKILL_MEMORY.md`、`examples/subpipeline-example.md`

### 规则 4：复杂系统主定义变化

- 触发条件：`ArtifactState`、barrier、wave、recovery、verification 的主规则变化
- 优先修改：对应 `architecture/*.md`
- 联动检查：`config/pipeline_protocol.md`、`EXAMPLES.md`、对应 `examples/*`

## 文件职责

| 文件 | 何时修改 | 禁止内容 |
|---|---|---|
| `README.md` | 人类入口、模式选择、阅读顺序变化时 | AI 运行期规则、命令细节、维护细节 |
| `SKILL.md` | Step 骨架或主流程读取顺序变化时 | 长 FAQ、协议复本、代码示例 |
| `SKILL_MEMORY.md` | 硬规则与门禁变化时 | 字段级模板、长解释、时间记录 |
| `config/pipeline_protocol.md` | 执行期控制变化时 | Handoff 模板、重复架构解释 |
| `config/handoff_protocol.md` | Handoff 机制变化时 | 执行期控制、重复架构解释 |
| `architecture/*.md` | 复杂系统某个主定义变化时 | 协议模板、维护清单 |
| `EXAMPLES.md` | 最小模板或判例变化时 | 协议主定义、维护日志 |
| `examples/*` | 某个专题示例变化时 | 新规则定义、维护日志 |

## 维护联动检查

- `README.md` 与 `architecture/README.md` 只给人看，不作为 AI 规则源
- `SKILL.md` 必须是 AI 的最小骨架入口，同时能独立解释标准模式下 Step 1-9 的节奏与下一步出口
- `PIPELINE_SUMMARY` 与 `Parent Summary` 的区别必须同时在主流程文档与示例中可见
- `HandoffStatus` 与 `ArtifactState` 不能混写
- 同一概念只能有一个主定义页
- 示例层只展示最小模板和高信号判例，不复写协议
- `EXAMPLES.md` 不能只剩模板碎片；至少保留一个 `pipeline_run_id -> trace -> result signal -> cleanup` 的闭环示例
