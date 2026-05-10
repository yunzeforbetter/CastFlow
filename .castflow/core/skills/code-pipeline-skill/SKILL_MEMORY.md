# code-pipeline-skill-memory

**性质**：硬门禁摘要。这里只保留 `code-pipeline` 执行中必须遵守、且需要高优先级记忆的总门禁。Step 细节、字段、模板和完整执行协议只以 `config/pipeline_protocol.md` 与 `config/handoff_protocol.md` 为准。

## 最小规则路径

- 标准模式：规则 0 / 1 / 2 / 3 / 4 / 5
- 复杂系统模式：在标准模式基础上，再读规则 6 / 7

## 规则 0：Step dispatch 必须携带精确协议卡

- 主 agent 不能只说“执行 Step N”
- 调度 `requirement-analysis-agent`、模块配对执行单元、`integration-matching-agent`、`pipeline-verify-agent`、`debug-skill`、`profiler-skill`，以及执行 Step 9 的 `main agent` 时，必须附带 `config/pipeline_protocol.md` 中对应的 Step 调度卡
- 未显式给出读什么、写什么、交什么时，不得启动该 Step

## 规则 1：在 `code-pipeline` 执行期间，`PIPELINE_CONTEXT.md` 是单一事实来源

- 所有 pipeline 信息通过 `PIPELINE_CONTEXT.md` 流转
- Step 3 模块产物写入 `temp/pipeline-output/{module_id}.md`
- 禁止生成额外临时分析文件，如 `DECOMPOSITION.md`、`REPORT.md`
- `PIPELINE_CONTEXT.md` 的结构、PCB、Step 产物、run_id 与 gate 规则只以 `config/pipeline_protocol.md` 为准

## 规则 2：Step 1 路线决策门禁必须通过

- 进入 Step 2 或 Step 3 前，主 agent 必须先确认 Step 1 已通过路线决策门禁
- Step 1 最低必备字段：`类似功能检索结果`、`模块策略建议`
- 若存在可复用候选：`UserDecision` 必须显式记录且已解决
- Gate 未通过时，只允许补充分析或回用户确认；禁止冻结 Handoff、生成最终 BLUEPRINT、进入实现，或把“全新实现”直接当成默认路线

## 规则 3：Step 3 / Step 4 / Step 5 的职责边界不可越界

- Step 3 只能在声明边界内实现，不得编造未声明 API 或替其他模块兑现职责
- Step 4 只验证依赖闭合，不改代码
- Step 5 只生成 coverage / verdict / result signal，不改代码

## 规则 4：进入 Step 3 前必须通过 Freeze Gate

- `L0` / `L1+` 进入 Step 3 前，必须满足 `config/handoff_protocol.md` 定义的 Freeze Gate
- `UserDecision`、Handoff、Blocks、Done Criteria 等判断只以 `config/handoff_protocol.md` 为准

## 规则 5：Step 9 必须终结 pipeline

- Step 9 是最后一步，无论成功或放弃都必须执行
- `Cleanup` / `Persist` 与 `pipeline_run_id` 清理规则只以 `config/pipeline_protocol.md` 为准

## 规则 6：复杂系统模式必须维护调度状态产物

- 进入复杂系统模式后，必须维护 `Artifact State Table`、`Wave Plan`、`Wave Dispatch Table`、`Checkpoint Record`
- 字段、更新时机与读写顺序只以 `config/pipeline_protocol.md` 为准

## 规则 7：复杂系统模式的 dispatch 是放行门

- 普通模块只有在 barrier、Frozen 状态和 checkpoint 说明都满足时，才能进入当前 `Wave Dispatch Table`
- `NeedsSubpipeline / Stalled / Blocked` 的派发限制只以 `architecture/*` 与 `config/pipeline_protocol.md` 为准
