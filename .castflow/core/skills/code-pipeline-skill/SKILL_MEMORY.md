# code-pipeline-skill-memory

**性质**：硬规则。这里只保留 `code-pipeline` 组件内部必须遵守的门禁、禁止项和调度规则。字段、模板和完整流程细节见 `config/*` 与 `architecture/*`。

## 边界前提

- shared agents / templates 只定义组件本体能力
- `code-pipeline` 对 shared components 的写入路径、输出格式与结果信号合同，只以 `config/pipeline_protocol.md` 为准

## 最小规则路径

- 标准模式：规则 0 / 1 / 2 / 3 / 4 / 5 / 6 / 7 / 10 / 11 / 12
- 复杂系统模式：在标准模式基础上，再读规则 8 / 9

## 规则 0：Step dispatch 必须携带精确协议卡

- 主 agent 不能只说“执行 Step N”
- 调度 `requirement-analysis-agent`、模块配对执行单元、`integration-matching-agent`、`pipeline-verify-agent`、`debug-skill`、`profiler-skill`，以及执行 Step 9 的 `main agent` 时，必须附带 `config/pipeline_protocol.md` 中对应的 Step 调度卡
- 未显式给出读什么、写什么、交什么时，不得启动该 Step

## 规则 1：在 `code-pipeline` 执行期间，`PIPELINE_CONTEXT.md` 是单一事实来源

- 所有 pipeline 信息通过 `PIPELINE_CONTEXT.md` 流转
- `PIPELINE_CONTEXT.md` 属于 `code-pipeline` own 的 runtime state，不是框架公共原语
- Step 3 模块产物写入 `temp/pipeline-output/{module_id}.md`
- 禁止生成额外临时分析文件，如 `DECOMPOSITION.md`、`REPORT.md`
- `PIPELINE_CONTEXT.md` 的结构、PCB 与 run_id 规则以 `config/pipeline_protocol.md` 为准

## 规则 2：Step 1 必须产出固定骨架

`requirement-analysis-agent` 在 Step 1 至少必须产出：

- 功能拆分
- API 声明
- 依赖关系
- `Handoff Draft`（`L1+`）或 `No-Handoff Rationale`（`L0`）
- Handoff Level Decision
- Freeze Recommendation
- Step 2 / Step 3 建议

若输入包含 PDF、导图或截图，必须先执行双阶段解构协议。输出骨架与示例见 `EXAMPLES.md`，运行细节见 `config/pipeline_protocol.md`。

## 规则 3：满足条件时必须执行 Step 2

满足任一条件时，必须执行 Step 2：

- 跨 3+ 模块
- 存在事件、状态、权限等共享契约
- Handoff Level = `L2` / `L3`
- 存在 `unknown` Blocks
- Freeze Recommendation = `Needs Step 2`

进入 Step 3 前，`PCB.SHADOW_BANS` 与 `PCB.CONFIG_SYNTHESIS` 必须非空。

## 规则 4：Step 3 只能在 Owns 内实现

- `L1+` 场景下，模块配对执行单元只能实现当前模块 `Owns`
- `L0` 场景下，不生成正式 Handoff，但 Step 3 只能实现 Step 1 已声明的单模块职责
- 新增依赖或剩余阻塞必须写入 Handoff Update
- 未就绪依赖必须使用规范 TODO 占位
- 禁止创造未声明的新 API
- 禁止替其他模块兑现职责
- `L0` 场景一旦出现跨模块 `Requires / Provides`，必须停止并回退升级到 `L1+`

## 规则 5：Step 3 模块输出必须可归并

每个 `temp/pipeline-output/{module_id}.md` 必须包含：

- `PIPELINE_SUMMARY`
- `PIPELINE_DETAIL`
- Handoff Update
- COMPLIANCE_CHECKLIST

`PIPELINE_SUMMARY` / `PIPELINE_DETAIL` 必须带固定 HTML 标记；缺标记时 `pipeline_merge.py` 必须拒绝归并。  
`PIPELINE_SUMMARY` 用于合并回 `PIPELINE_CONTEXT.md`；`PIPELINE_DETAIL` 只供 Step 4 / Step 5 深读。  
`Parent Summary` 只用于子 pipeline 回传父 pipeline，不等于 Step 3 模块 summary。
`temp/pipeline-output/` 若没有任何模块产物，`pipeline_merge.py` 也必须 fail-closed；不得让 Step 4 / Step 5 基于空输出或旧归并块继续推进。

## 规则 6：Step 4 只验证，不改代码

`integration-matching-agent` 只能：

- 验证 Requires / Provides 是否闭合
- 分类 `SignatureMismatch / MissingProvider / BoundaryViolation / CompletableBlocks / BlockingBlocks / ImplicitRequires`
- 输出 Dependency Closure Report

禁止修改代码、替换 TODO、创建新 API、强加新约束。

## 规则 7：Step 5 只决策，不改代码

`pipeline-verify-agent` 只能：

- 评估 Step 4 的结果严重度
- 检查 Done Criteria Coverage
- 生成 Module / Global Verdict
- 写本组件的 pipeline result signal（默认运行时落点：`.claude/traces/.pending_pipeline_result.json`；`GO-WITH-CAUTION` 首次必须写 `finalized=false`）

禁止直接修改代码。

## 规则 8：复杂系统模式必须维护四类产物

进入复杂系统模式后，主流程必须维护：

- `Artifact State Table`
- `Wave Plan`
- `Wave Dispatch Table`
- `Checkpoint Record`

这些产物的字段、更新时机与读写顺序以 `config/pipeline_protocol.md` 为准。
复杂系统模式下，`Step 3 / Step 4 / Step 5 / Step 6` 的调度 prompt 必须显式附带与当前 wave / dispatch / checkpoint / verification scope 对应的字段，不得只复用标准模式最小卡。

## 规则 9：复杂系统模式的 dispatch 是放行门

普通模块只有在以下条件同时满足时，才能进入当前 `Wave Dispatch Table`：

- `ArtifactState = Frozen`
- 对应 barrier 已满足
- `HandoffStatus = Frozen`
- 最新 `Checkpoint Record` 已说明当前放行原因
- 模块不处于 `Blocked / Stalled / NeedsSubpipeline`

`NeedsSubpipeline` 只能写成显式 `DispatchTarget = sub-pipeline` 的派发行；`Stalled / Blocked` 禁止继续派发。

## 规则 10：多 agent 协作必须先锁 Handoff

当 Step 3 需要 2+ agent，或存在跨模块 Requires / Provides 时：

- Step 1 必须生成 Handoff Level Decision；`L1+` 必须生成 Handoff Draft，`L0` 必须写 `No-Handoff Rationale`
- 进入 Step 3 前必须通过 Freeze Gate
- `Owns` 不重叠
- `Requires` 有候选 Provider，或明确标记 `unknown`
- `UserDecision` 已解决

模板与 Freeze Gate 细则见 `config/handoff_protocol.md`。

## 规则 11：Step 6 不能直接宣布完成

当 Step 5 = `GO-WITH-CAUTION`：

- Step 6 只补 `CompletableBlocks`
- 补完后至少重跑 Step 4
- 若 closure 变化影响 coverage 或 verdict，必须重跑 Step 5
- Step 6 不得直接把 `GO-WITH-CAUTION` 改成 `GO`

## 规则 12：Step 9 必须终结 pipeline

- Step 9 是最后一步，无论成功或放弃都必须执行
- `Cleanup` 模式：本组件 own 的 `PIPELINE_CONTEXT.md` 随整体删除
- `Persist` 模式：必须删除 `pipeline_run_id:` 行
- 禁止遗留过期 run_id

## 规范 TODO

```md
// TODO: 等待 [模块名].[API名]() 完成后替换
// 预期签名：[返回类型] [API名]([参数列表])
// 使用场景：[场景描述]
```

TODO 样例见 `EXAMPLES.md`。
