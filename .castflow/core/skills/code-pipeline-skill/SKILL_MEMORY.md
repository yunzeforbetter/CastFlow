# code-pipeline-skill-memory

**性质**：硬门禁摘要。这里只保留 `code-pipeline` 执行中必须遵守、且需要高优先级记忆的总门禁。Step 细节、状态字段、模板和完整执行协议只以 `config/pipeline_protocol.md` 与 `config/handoff_protocol.md` 为准。

## 最小规则路径

- 标准模式：规则 0 / 1 / 2 / 3 / 4 / 5 / 6
- 复杂系统模式：在标准模式基础上，再读规则 7 / 8

## 规则 0：Step dispatch 必须携带精确协议卡

- 主 agent 不能只说“执行 Step N”
- 调度 `requirement-analysis-agent`、模块配对执行单元、`integration-matching-agent`、`pipeline-verify-agent`、`debug-skill`、`profiler-skill`，以及执行 Step 9 的 `main agent` 时，必须附带 `config/pipeline_protocol.md` 中对应的 Step 调度卡
- 即使由 `main agent` 自行执行 Step 1 / Step 2，也必须显式按对应调度卡约束自己，不得以“没有 dispatch”作为绕过协议卡的理由
- 未显式给出读什么、写什么、交什么时，不得启动该 Step

## 规则 1：运行期真相与文档投影必须分离

- gate 真相由结构化 runtime state 承载
- `PIPELINE_CONTEXT.md` 只做投影与归档，不单独承担 gate 真相
- Step 3 模块产物写入 `temp/pipeline-output/{module_id}.md`
- 禁止生成额外临时分析文件，如 `DECOMPOSITION.md`、`REPORT.md`

## 规则 2：路线未收敛时必须停在决策态

- 进入 Step 2 或 Step 3 前，主 agent 必须先确认路线决策已收敛
- Step 1 最低必备分析仍包括独立的 `DecompositionSnapshot`、`CapabilityScan`、`DecisionSynthesis`；它们分别承载“拆解快照”“类似功能检索结果”“模块策略建议”
- 在 `code-pipeline` 模式下，Step 1 必须显式产出独立 `CapabilityScan` block，且至少包含 `MatchedCapabilities`、`CandidateHosts`、`Evidence`、`Recommendation`
- PRD、用户口述、设计稿只能定义 `scan scope`，不能替代 `CapabilityScan` 的源码 `Evidence`
- `Evidence` 不能只写宽泛目录或一句“未命中”；若结论是未命中，至少同时写出扫描范围、搜索目标与未命中结论
- 若计划新增文件 / 类型 / 字段 / API：必须先完成 `ArtifactBinding`
- 若存在可复用候选且存在路线分歧：必须进入 `PendingDecision`
- 未收到显式 `UserDecision` 前，禁止冻结 Handoff、生成最终 BLUEPRINT、进入实现，或把“全新实现”直接当成默认路线

## 规则 3：认知型复杂度优先分治，不让主流程变厚

- Step 1 内部子阶段命名与顺序固定为：`DecompositionSnapshot` -> `CapabilityScan` -> `ArtifactBinding` -> `DecisionSynthesis`
- Step 1 的 scan 类认知任务优先拆给只读 subagent，不要求主 agent 自己做全量搜索
- scan 类 subagent 只返回证据、候选承载点、复用风险、开放问题，不得写 runtime truth、冻结 Handoff、推进 Step
- scan 类任务即使拆给只读 subagent，聚合层仍必须把结果落回 Step 1 的 canonical block；只在子 agent 返回里出现结论，不算完成 `CapabilityScan`
- 除了面向人类解释的中文标题，协议关键字不得临时改名或混写近义词
- 若 scan 证据冲突或不足，主 agent 只能缩小范围重发 scan、补充 `Open Questions`，或停在 `PendingDecision`

## 规则 4：Step 3 / Step 4 / Step 5 的职责边界不可越界

- Step 3 只能在声明边界内实现，不得编造未声明 API 或替其他模块兑现职责
- Step 4 只验证依赖闭合，不改代码
- Step 5 只生成 coverage / verdict / result signal，不改代码

## 规则 5：进入 Step 3 前必须通过 Freeze Gate

- `L0` / `L1+` 进入 Step 3 前，必须满足 `config/handoff_protocol.md` 定义的 Freeze Gate
- `UserDecision`、Handoff、Blocks、Done Criteria 等判断只以 `config/handoff_protocol.md` 为准

## 规则 6：Step 9 必须终结 pipeline

- Step 9 是最后一步，无论成功或放弃都必须执行
- `Cleanup` / `Persist` 与 `pipeline_run_id` 清理规则只以 `config/pipeline_protocol.md` 为准

## 规则 7：复杂系统模式必须维护调度状态产物

- 进入复杂系统模式后，必须维护 `Artifact State Table`、`Wave Plan`、`Wave Dispatch Table`、`Checkpoint Record`
- 字段、更新时机与读写顺序只以 `config/pipeline_protocol.md` 为准

## 规则 8：复杂系统模式的 dispatch 是放行门

- 普通模块只有在 barrier、Frozen 状态和 checkpoint 说明都满足时，才能进入当前 `Wave Dispatch Table`
- `NeedsSubpipeline / Stalled / Blocked` 的派发限制只以 `architecture/*` 与 `config/pipeline_protocol.md` 为准
