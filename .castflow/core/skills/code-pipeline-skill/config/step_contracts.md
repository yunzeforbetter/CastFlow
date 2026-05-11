# Step Contracts

> `code-pipeline` 的唯一 Step 收口页。这个文件不是弱导航表，而是 Step 级合同：定义每一步的目标、输入、输出、进入条件、下一步出口，以及必须满足的强规则。执行细节、字段级约束与更细粒度的 fail-closed 规则仍以 `pipeline_protocol.md` / `handoff_protocol.md` 为准。

## 文件职责

- 本文件：Step 1-9 的唯一收口页与 Step 级强规则入口
- `SKILL.md`：流程导航与阅读入口，不重复定义 Step 细则
- `SKILL_MEMORY.md`：跨 Step 的硬规则与禁止事项
- `config/pipeline_protocol.md`：执行协议真源
- `config/handoff_protocol.md`：Handoff / Freeze / Closure / Coverage 真源
- `EXAMPLES.md`：最小模板与判例

## Step 总表

| Step | 目标 | 主要输入 | 必须输出 | 进入条件 | 下一步出口 |
|---|---|---|---|---|---|
| Step 1 | 需求拆分、类似功能检索、产物绑定、路线决策、Handoff 级别判断 | 用户请求、项目代码/文档证据、原始资产 | 功能拆分、API 声明、依赖关系、类似功能检索结果、模块策略建议、必要时的 `ArtifactBinding`、决策状态（必要时含 `UserDecision`）、Handoff Level Decision、Freeze Recommendation、Step 2 / Step 3 建议 | pipeline 启动 | 路线未收敛 -> 停在决策态并回用户；需冻结 -> Step 2；可直接实现 -> Step 3；复杂度过高 -> 子 pipeline / 复杂系统模式 |
| Step 2 | 冻结共享约束与协作边界 | Step 1 产物、L1 参数、约束文件 | PCB、`BLUEPRINT`、`Frozen Handoff`（`L1+`） | Step 1 路线已收敛，且命中冻结条件 | Freeze 完成 -> Step 3 |
| Step 3 | 在声明边界内完成模块实现 | Step 1 / Step 2 声明产物、结构化 runtime state、PCB、Handoff、Blueprint 切片 | 代码、`temp/pipeline-output/{module_id}.md`、Handoff Update、COMPLIANCE_CHECKLIST | 路线已收敛；Step 3 Freeze Gate 已过 | 产物可归并 -> Step 4；发现新 blocker -> 回 Step 1 / Step 2 / recovery |
| Step 4 | 验证依赖是否闭合 | Step 1 / Step 2 产物、Step 3 模块输出、Handoff Update | `Dependency Closure Report` | 存在 Step 3 可归并产物 | 闭合充分 -> Step 5；缺口明显 -> Step 6 / recovery |
| Step 5 | 评估覆盖度并给出 verdict | Step 4 closure、Done Criteria 输入、必要模块细节 | `Done Criteria Coverage`、`VERIFICATION_REPORT`、pipeline result signal | Step 4 已完成 | `GO` -> Step 9；`GO-WITH-CAUTION` -> Step 6；`NO-GO` -> recovery / re-dispatch |
| Step 6 | 只补可补齐的块 | Step 5 的 `CompletableBlocks`、相关模块最新输出 | 更新后的模块输出、re-closure note、必要 checkpoint | Step 5 = `GO-WITH-CAUTION` | 至少回 Step 4；必要时再回 Step 5 |
| Step 7 | 做边界条件测试 | closure / verdict / blocker 信息、相关实现细节 | 风险列表、失败路径、修复建议 | 需要边界条件验证时 | 回 Step 6 / Step 4 / Step 5 或继续 Step 8 / Step 9 |
| Step 8 | 做性能诊断 | 目标模块/路径、实现证据、必要报告 | 性能问题、瓶颈位置、优化建议 | 需要性能诊断时 | 回 Step 6 / Step 4 / Step 5 或继续 Step 9 |
| Step 9 | 终结 pipeline 并清理运行态 | 最终 verdict、coverage、execution_steps、context_retention | `Cleanup` / `Persist` 结果、run_id 终结状态 | 最终结果已收敛或流程明确放弃 | pipeline 结束 |

## Step 1：需求拆分与路线决策

### 目标
- 功能拆分
- 类似功能检索
- 拟新增产物的绑定判断
- 路线推荐与用户决策
- Handoff 级别判断

### 主要输入
- 用户请求
- 项目代码 / 文档证据
- 原始资产（PDF / 导图 / 截图 / 设计稿）

### 必须输出
- `类似功能检索结果`
- `模块策略建议`
- 必要时的 `ArtifactBinding`
- 决策状态（无候选则标记已收敛；存在路线分歧则进入 `PendingDecision`）
- 必要时的 `UserDecision`
- Handoff Level Decision
- Freeze Recommendation
- Step 2 / Step 3 建议

以上字段在输出组织上优先归入 `DecompositionSnapshot`、`CapabilityScan`、`ArtifactBinding`、`DecisionSynthesis` 四个 canonical block；其中 `CapabilityScan` 等价承载 `类似功能检索结果`，`DecisionSynthesis` 等价承载 `模块策略建议` 与决策状态。

### Step 1 内部子阶段
1. `DecompositionSnapshot`（拆解快照）：先生成最小功能目标、 provisional modules、provisional APIs 与 scan scope
2. `CapabilityScan`（能力探寻）：以 `DecompositionSnapshot` 为边界检索类似功能、候选承载点与复用风险
3. `ArtifactBinding`（产物绑定）：若计划新增文件 / 类型 / 字段 / API，逐项标记 `reuse / extend / new`
4. `DecisionSynthesis`（决策综合）：基于 `CapabilityScan` 与 `ArtifactBinding` 结果写 `模块策略建议`、`UserDecision`、Handoff / Freeze 结论

### Step 1 最小可判定标准
在 `code-pipeline` 模式下，Step 1 只有同时满足以下条件时才算完成：

1. 正文包含独立的 `DecompositionSnapshot`、`CapabilityScan`、必要时的 `ArtifactBinding`、`DecisionSynthesis` 四个 canonical block
2. `CapabilityScan` 中的 `MatchedCapabilities`、`CandidateHosts`、`Evidence`、`Recommendation` 四项均已填写；若未命中可复用承载，必须显式写 `None` / `未命中`，不能省略
3. `Evidence` 的每一项至少引用一个具体的项目代码路径或符号；若结论是“未命中”，必须同时给出扫描范围和搜索目标（符号 / 关键词族）以及未命中结论。仅写宽泛目录、模糊范围、PRD、用户口述或设计稿，都不能单独充当源码 `Evidence`
4. 若计划新增文件 / 类型 / 字段 / API，或 `Recommendation` 不是纯 `reuse`，必须继续给出对应的 `ArtifactBinding`
5. 若 `CapabilityScan` 的 `Evidence` 不足以支撑路线收敛，`DecisionSynthesis` 只能回写 `OpenQuestions` / `PendingDecision`，不得把路线写成已收敛

### 强规则
- Step 1 内部子阶段顺序固定为：`DecompositionSnapshot` -> `CapabilityScan` -> `ArtifactBinding` -> `DecisionSynthesis`
- `CapabilityScan` 必须覆盖类似功能、相近职责实现或可直接承载模块
- `CapabilityScan` 必须以真实仓库证据为基础，不得用 Phase 叙事、PRD 摘要或一句“已检索”替代独立 block
- 若计划新增文件 / 类型 / 字段 / API，必须先完成 `ArtifactBinding`
- 若存在可复用候选，默认推荐“在已有能力上迭代”
- `DecisionSynthesis` 的路线结论必须可回指到 `CapabilityScan` 的 `Evidence`
- 若存在路线分歧，必须显式收敛为决策态，等待 `UserDecision`

### 禁止
- 未检索类似功能就直接进入拆分定案
- 用 PRD、用户口述、设计稿或模糊记忆替代 `CapabilityScan` 的源码 `Evidence`
- 用 Phase 叙事、总结段落或一句“无可复用候选”吞掉独立 `CapabilityScan` block
- 未完成 `ArtifactBinding` 就输出新增产物或新增实现建议
- 有可复用候选却默认走全新实现
- 在 `UserDecision` 未解决时继续进入 Step 2 / Step 3

### Fail-closed
- 缺少 `类似功能检索结果`、`模块策略建议`、计划新增产物但缺少 `ArtifactBinding`，或有候选但路线仍未收敛时，不得进入 Step 2 / Step 3
- 缺少独立 `CapabilityScan` block，或 `MatchedCapabilities` / `CandidateHosts` / `Evidence` / `Recommendation` 任一缺失时，Step 1 视为未完成
- `Evidence` 未引用具体项目代码路径 / 符号，或在“未命中”场景下缺少扫描范围 + 搜索目标，或仅包含 PRD / 用户描述 / 设计输入时，Step 1 视为未完成
- `DecisionSynthesis` 无法把结论回指到 `CapabilityScan` 的 `Evidence` 时，不得把路线写成已收敛

## Step 2：约束冻结

### 目标
- 冻结共享约束
- 冻结协作边界
- 固化 Blueprint / PCB

### 主要输入
- Step 1 产物
- L1 参数
- 约束文件

### 必须输出
- PCB
- `BLUEPRINT`
- `Frozen Handoff`（`L1+`）

### 强规则
- 只有在路线已收敛且命中冻结条件时才进入 Step 2
- Freeze 细则只以 `handoff_protocol.md` 为准

### 禁止
- Step 1 路线未收敛就进入冻结
- 跳过 PCB 或 Handoff Freeze 直接推进多模块实现

### Fail-closed
- Freeze 未完成、PCB 不完整、Handoff 未冻结，或决策态仍未解决时，不得进入 Step 3

## Step 3：模块实现

### 目标
- 在声明边界内完成实现
- 产出可归并、可验收的模块结果

### 主要输入
- Step 1 / Step 2 声明产物
- 结构化 runtime state
- PCB
- Handoff
- Blueprint 切片
- 必要时的 `ArtifactBinding`

### 必须输出
- 代码
- `temp/pipeline-output/{module_id}.md`
- Handoff Update
- COMPLIANCE_CHECKLIST

### 强规则
- 路线决策必须已收敛
- Freeze Gate 必须已通过
- 只能在声明边界内实现
- 若实现涉及新增文件 / 类型 / 字段 / API，必须对齐对应的 `ArtifactBinding`

### 禁止
- 越界实现
- 编造未声明 API
- 跳过 Handoff Update
- 在决策态仍未解决时启动实现
- 在 `L0` 场景出现跨模块依赖后继续硬推实现

### Fail-closed
- 路线未收敛、Gate 未过、缺少必要的 `ArtifactBinding`、模块输出不可归并或依赖未就绪时，不得假装完成并推进 Step 4

## Step 4：依赖闭合

### 目标
- 证明依赖是否真正闭合

### 主要输入
- Step 1 / Step 2 产物
- Step 3 模块输出
- Handoff Update

### 必须输出
- `Dependency Closure Report`
- 完整分区：`Closed / SignatureMismatch / MissingProvider / BoundaryViolation / CompletableBlocks / BlockingBlocks / ImplicitRequires`

### 强规则
- Step 4 只验证，不改代码
- 无法证明闭合时必须保守归类到缺口分区

### 禁止
- 修改代码
- 替换 TODO
- 把未证明闭合写成 `Closed`

### Fail-closed
- 缺少 closure 分区或证据不足时，不得进入 Step 5 的乐观 verdict

## Step 5：覆盖验收

### 目标
- 基于 closure 判断覆盖度与最终 verdict

### 主要输入
- Step 4 closure
- Done Criteria 输入
- 必要模块细节

### 必须输出
- `Done Criteria Coverage`
- `VERIFICATION_REPORT`
- pipeline result signal（仅最终化时）

### 强规则
- Step 5 只决策，不改代码
- 局部 / 全局 verdict 的判定细节只以 `pipeline_protocol.md` 为准

### 禁止
- 修改代码
- 在证据不足时给 `GO`

### Fail-closed
- coverage 缺口未解释、verdict 证据不足或 result signal 非法时，不得宣布完成

## Step 6：补全 CompletableBlocks

### 目标
- 只补齐已经证明可补齐的缺口

### 主要输入
- Step 5 的 `CompletableBlocks`
- 相关模块最新输出

### 必须输出
- 更新后的模块输出
- re-closure note
- 必要 checkpoint

### 强规则
- 只能补 `CompletableBlocks`
- 补完后至少重跑 Step 4；必要时重跑 Step 5

### 禁止
- 借 Step 6 偷做新功能
- 直接把 `GO-WITH-CAUTION` 改写成 `GO`

### Fail-closed
- 若出现新 blocker 或共享 contract 变化，必须回退重跑，不得直接收尾

## Step 7：边界条件测试

### 目标
- 验证 golden path 之外的边界与失败路径

### 主要输入
- closure / verdict / blocker 信息
- 相关实现细节

### 必须输出
- 问题列表
- 风险点
- 修复建议

### 强规则
- 缺少可验证输入时，只能输出风险与补测建议

### 禁止
- 在缺乏证据时宣称“已验证通过”

## Step 8：性能诊断

### 目标
- 定位性能瓶颈与优化机会

### 主要输入
- 目标模块 / 路径
- 实现证据
- 必要报告

### 必须输出
- 性能问题
- 瓶颈位置
- 优化建议

### 强规则
- 缺少性能证据时，只能输出假设与采样建议

### 禁止
- 把主观推测写成确定性瓶颈

## Step 9：完成与清理

### 目标
- 终结 pipeline
- 清理 `pipeline_run_id`
- 决定 `Cleanup` 或 `Persist`

### 主要输入
- 最终 verdict
- coverage
- execution_steps
- context_retention

### 必须输出
- 最终清理结果
- run_id 终结状态

### 强规则
- Step 9 必须执行
- 清理规则只以 `pipeline_protocol.md` 为准

### 禁止
- 在 run_id 未清理或 result signal 未收敛时宣布 pipeline 完成

### Fail-closed
- 清理未完成或最终状态未收敛时，不得结束 pipeline
