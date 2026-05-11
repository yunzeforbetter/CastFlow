# Code Pipeline 示例库

> 这里只保留最小骨架与高信号判例。字段规则、读写路径与 Step 调度合同以 `config/pipeline_protocol.md` / `config/handoff_protocol.md` 为准。

## 用法

| 你要看什么 | 去哪看 |
|---|---|
| Step 2 / Step 3 怎么走 | `决策速查` |
| 常见误用怎么拦 | `误用判例` |
| `PIPELINE_CONTEXT.md` 最小形状 | `核心模板` |
| Step 1 与 Handoff 最小输出 | `Step 1 / Handoff` |
| Step 3 模块输出 | `Step 3 模块输出` |
| Step 4 / Step 5 判例 | `Closure / Verdict 判例` |
| `pipeline_run_id` / result signal / Step 9 清理 | `pipeline_run_id 生命周期` |
| 复杂系统模式 | `examples/*` |

## 决策速查

这个区块只给快速找样例入口；Step 进入条件、强规则与 fail-closed 以 `config/step_contracts.md` 为准。

| 场景 | 特征 | 推荐去看 |
|---|---|---|
| 单模块 | API 已存在、无跨模块依赖 | `Step 1 / Handoff` 中的 `L0` 示例 |
| 双模块 | 一方提供 API，另一方消费 | `Step 1 / Handoff` + `Step 3 模块输出` |
| 多模块 | 3+ 模块、共享契约、存在并行实现 | `Step 1 / Handoff` 中的 `L2` Handoff 示例 |
| 复杂系统 | 3+ 模块、长时间 churn、需要 wave / 子 pipeline | `核心模板` 的复杂系统追加段落 + `examples/*` |

## 误用判例

### AP-DISPATCH-01：主 agent 只说“执行 Step 1”

- Wrong：`执行 Step 1，先拆需求再继续`
- Violates：`SKILL_MEMORY.md` 规则 0；`pipeline_protocol.md` 的 `Step 调度卡`
- Right：显式给出 Step 1 的读 / 写 / 交，并要求输出 `DecompositionSnapshot`、`CapabilityScan`、`ArtifactBinding`、`DecisionSynthesis`
- Stop signal：没有协议卡时，不启动该 Step
- Acceptance：
  - [ ] 已说明 Step 1 读什么
  - [ ] 已说明 Step 1 写什么
  - [ ] 已说明 Step 1 交什么

### AP-STEP1-01：只读 PRD 直接做拆分定案

- Wrong：

```md
## Step 1
- 根据 PRD 判断联盟需要新做成员、礼物、科研、投票模块
- 建议直接进入实现
```

- Violates：`step_contracts.md` Step 1 禁止 / Fail-closed；`pipeline_protocol.md` 协议 2
- Right：先产出独立 `### CapabilityScan`，列出真实仓库中的候选承载点与 `Evidence`，再进入 `DecisionSynthesis`
- Stop signal：如果结论还回不到仓库路径、符号或检索范围，保持 `Discovering` 或 `PendingDecision`
- Acceptance：
  - [ ] 不是只基于 PRD / 口述下结论
  - [ ] `CapabilityScan` 已落盘
  - [ ] `Evidence` 已回指到仓库证据

### AP-STEP1-02：用一句“已检索”替代独立 `CapabilityScan`

- Wrong：

```md
### Phase 1 总结
- 已检索项目，暂无直接复用能力，建议新做
```

- Violates：`step_contracts.md` Step 1 最小可判定标准；`pipeline_protocol.md` 协议 2A
- Right：

```md
### CapabilityScan
#### MatchedCapabilities
- `AllianceManager`：已存在联盟门面与协议收发

#### CandidateHosts
- `Logic/Modules/Alliance`

#### Evidence
- `Assets/Scripts/GameLogic/Logic/Modules/Alliance/AllianceManager.cs` | `AllianceManager` | 已存在联盟核心门面

#### Recommendation
- `reuse`
```

- Stop signal：缺独立 `### CapabilityScan` block，或缺 `MatchedCapabilities` / `CandidateHosts` / `Evidence` / `Recommendation` 任一项时，Step 1 不完整
- Acceptance：
  - [ ] `CapabilityScan` 是独立 block
  - [ ] 四个最小字段已填写
  - [ ] 未命中时也明确写 `None` / `未命中`

### AP-STEP1-03：计划新增产物却没有 `ArtifactBinding`

- Wrong：

```md
### DecisionSynthesis
- 新增 `AlliancePermissionMeta.cs`
- 新增 `AllianceReviewService.cs`
- 推荐进入 Step 3
```

- Violates：`step_contracts.md` Step 1 禁止；`pipeline_protocol.md` 协议 2
- Right：

```md
### ArtifactBinding
- `AlliancePermissionMeta.cs` -> `new` -> `Logic/Modules/Alliance/Permission`
- `Reason`: 未检索到现有权限元数据承载点
- `Evidence`: `Assets/Scripts/GameLogic/Logic/Modules/Alliance/**/*.cs` 范围内未命中直接承载
```

- Stop signal：只要出现新增文件 / 类型 / 字段 / API 意图，却没有 `ArtifactBinding`，就不得进入 Step 2 / Step 3
- Acceptance：
  - [ ] 所有新增意图都已绑定为 `reuse / extend / new`
  - [ ] 每条绑定都有 `Reason` + `Evidence`

### AP-STEP1-04：有复用候选却默认全新实现

- Wrong：

```md
### CapabilityScan
#### MatchedCapabilities
- `AllianceManager`
- `AllianceMainUI`

### DecisionSynthesis
- 建议全新重写联盟系统
- 直接进入 Step 3
```

- Violates：`step_contracts.md` Step 1 强规则；`pipeline_protocol.md` 协议 2
- Right：至少同时给出“在已有能力上迭代”和“全新实现”两个方向；若用户尚未拍板，进入 `PendingDecision`
- Stop signal：存在可复用候选且路线仍有分歧时，不得把 `pipeline_decision_status` 写成 `resolved`
- Acceptance：
  - [ ] 复用候选已被纳入方案比较
  - [ ] 默认推荐是“在已有能力上迭代”
  - [ ] 路线分歧未解决时状态仍为 `PendingDecision`

## 核心模板

### `PIPELINE_CONTEXT.md` 最小骨架

```md
# PIPELINE_CONTEXT.md - [功能名称]

pipeline_run_id: pipeline_20260420_143055
pipeline_mode: standard
pipeline_current_step: 1
pipeline_lifecycle_state: Discovering
pipeline_decision_status: none
pipeline_decision_basis: unknown
pipeline_freeze_status: not_applicable
pipeline_active_modules: []
pipeline_last_closure_scope: none
pipeline_last_verdict: none
pipeline_result_signal_status: none

---

## PCB

### SHADOW_BANS
- 禁止项

### CONFIG_SYNTHESIS
- 命名、基类、命名空间、运行参数

### MACRO_SCOPE
- 功能点
- 模块关系

### BLUEPRINT
- 类、职责、Public API、事件契约

### ATOMIC_EXECUTION
- [ ] 原子任务 1
- [ ] 原子任务 2

---

## Step 1
### DecompositionSnapshot
#### 功能目标
#### provisional modules
#### provisional APIs
#### scan scope

### CapabilityScan
#### MatchedCapabilities
#### CandidateHosts
#### ReuseRisks
#### Evidence
#### OpenQuestions
#### Recommendation

### ArtifactBinding
#### ProposedArtifact
#### BindingMode
#### BoundHost
#### Reason
#### Evidence

### DecisionSynthesis
#### 模块策略建议
#### 决策状态 / UserDecision
#### Handoff Level Decision
#### Freeze Recommendation
#### Step 2 建议
#### Step 3 建议

### API 声明
### 依赖关系
### Handoff Draft / No-Handoff Rationale

---

## Step 2
### SHADOW_BANS
### CONFIG_SYNTHESIS
### MACRO_SCOPE
### BLUEPRINT
### ATOMIC_EXECUTION
### Frozen Handoff

---

## Step 3
### 模块输出归并

---

## Step 4
### Dependency Closure Report

---

## Step 5
### Done Criteria Coverage
### VERIFICATION_REPORT
```

### 复杂系统模式追加段落

```md
## Artifact State Table

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| MI_AUTH | SharedCore | Frozen | - | SharedBarrier | CP-01 |
| M8 | DomainComplex | NeedsSubpipeline | MI_EVENT,M4,M5 | LocalBarrier | CP-02 |

## Wave Plan

| Wave | EntryCondition | IncludedModules | DeferredModules | ExitArtifact |
|---|---|---|---|---|
| Wave 1 | Step 1 complete | MI_AUTH, MI_EVENT | M1, M8 | SharedBarrier Ready |

## Wave Dispatch Table

| Wave | Module | ArtifactState | Barrier | DispatchTarget | Inputs | ExpectedOutput | Fallback |
|---|---|---|---|---|---|---|---|
| Wave 2 | M1 | Frozen | SharedBarrier=Ready | programmer-m1-agent | Frozen Handoff, PCB | temp/pipeline-output/M1.md | main agent |

## Checkpoint Record

### CP-02
- Scope: M8
- ArtifactState: NeedsSubpipeline
- NewArtifacts: Shared Core Frozen
- BlockingArtifact: Map contract not Frozen
- TimeboxUntil: next recovery review
- NextAction: spawn sub-pipeline
- RecoveryAction: remove from normal dispatch
```

## Step 1 / Handoff

### Step 1 canonical shape

```md
## Step 1

### DecompositionSnapshot
#### 功能目标
#### provisional modules
#### provisional APIs
#### scan scope

### CapabilityScan
#### MatchedCapabilities
#### CandidateHosts
#### ReuseRisks
#### Evidence
#### OpenQuestions
#### Recommendation

### ArtifactBinding
- `ProposedArtifact` -> `BindingMode` -> `BoundHost`
- `Reason`
- `Evidence`

### DecisionSynthesis
#### 模块策略建议
#### UserDecision
#### Handoff Level Decision
#### Freeze Recommendation
#### Step 2 建议
#### Step 3 建议

### API 声明
### 依赖关系
### Handoff Draft / No-Handoff Rationale
```

### Step 1 最小输出

```md
## Step 1

### DecompositionSnapshot
#### 功能目标
- 完成战斗入口链路

#### provisional modules
- UI
- Logic
- Battle

#### provisional APIs
- UI -> Logic.GetStatus()
- Logic -> Battle.StartBattle()

#### scan scope
- `Modules/Battle`
- `Modules/CommonUI/BattlePanel`

### CapabilityScan
#### MatchedCapabilities
- `Battle`：检索到 `Modules/Battle`，职责与需求高度重合，可作为主承载实现
- `UI`：检索到 `Modules/CommonUI/BattlePanel`，交互流相近，可复用部分展示逻辑
- `Logic`：未检索到可直接承载的现有实现，需要新增逻辑承载层

#### CandidateHosts
- `Battle` -> `Modules/Battle`
- `UI` -> `Modules/CommonUI/BattlePanel`

#### ReuseRisks
- `Logic` 若强塞进现有 `Battle` 承载，会混入状态聚合职责

#### Evidence
- `Modules/Battle` | `Battle.StartBattle` | 现有战斗链路可承载启动职责
- `Modules/CommonUI/BattlePanel` | `BattlePanel.Refresh` | 现有展示链路可复用
- `Logic/**/*Battle*.cs` | 未命中直接状态聚合承载 | 作为新增逻辑承载的负例依据

#### OpenQuestions
- None

#### Recommendation
- `hybrid`

### ArtifactBinding
- `Battle.StartBattle()` -> `reuse` -> `Modules/Battle`
- `Reason`: 现有战斗主承载已覆盖启动职责
- `Evidence`: `Modules/Battle`
- `Logic.GetStatus()` -> `new` -> `Logic`；理由：未检索到可直接承载状态聚合的现有逻辑层
- `Evidence`: 未命中可直接承载状态聚合的现有逻辑层

### DecisionSynthesis
#### 模块策略建议
- 默认：依托已有 `Battle` 能力迭代
- `Logic` 作为新增承载层拆出

#### UserDecision
- Battle：若无额外约束，默认按“在已有能力上迭代”推进；如用户指定隔离演进，再切换为全新实现

#### Handoff Level Decision
- `L2`：存在跨模块 Requires / Provides，需要冻结边界

#### Freeze Recommendation
- Needs Step 2

#### Step 2 建议
- 推荐：共享 Battle API 与 UI 刷新事件需要先冻结

#### Step 3 建议
- 使用模块配对执行单元并行推进 UI / Logic，Battle 保持 provider 优先

### API 声明
- UI -> Logic.GetStatus()
- Logic -> Battle.StartBattle()

### 依赖关系
- UI 依赖 Logic
- Logic 依赖 Battle

### Handoff Draft
- UI / Logic / Battle
```

### `L0` 最小输出

```md
## Step 1

### DecompositionSnapshot
#### 功能目标
- 完成单模块背包刷新

#### provisional modules
- Inventory

#### provisional APIs
- Inventory.Refresh()

#### scan scope
- `InventoryPanel`

### CapabilityScan
#### MatchedCapabilities
- `InventoryPanel`：检索到现有背包展示与刷新链路，可直接作为承载实现

#### CandidateHosts
- `Inventory` -> `InventoryPanel`

#### ReuseRisks
- None

#### Evidence
- `InventoryPanel` | `InventoryPanel.Refresh` | 现有背包展示与刷新链路可直接承载

#### OpenQuestions
- None

#### Recommendation
- `reuse`

### DecisionSynthesis
#### 模块策略建议
- 默认：在已有 `InventoryPanel` 能力上迭代

#### UserDecision
- Inventory：若无额外隔离诉求，默认按“在已有能力上迭代”推进

#### Handoff Level Decision
- `L0`

#### Freeze Recommendation
- 走 `L0` 快速路径，跳过正式 Handoff Freeze

#### Step 2 建议
- 跳过

#### Step 3 建议
- 直接进入单模块实现，但若新增跨模块依赖需回退升级到 `L1+`

### API 声明
- Inventory.Refresh()

### 依赖关系
- 无跨模块依赖

### No-Handoff Rationale
- `L0`：单模块、单 agent、无跨模块 `Requires / Provides`
```

### `ArtifactBinding` 防重复生成判例

```md
### DecompositionSnapshot
#### scan scope
- `AlliancePermissionAuditConfig`

### CapabilityScan
#### MatchedCapabilities
- `AlliancePermissionAuditConfig`：已承载联盟权限审计配置字段

#### CandidateHosts
- `AlliancePermissionAuditConfig`

#### ReuseRisks
- None

#### Evidence
- `AlliancePermissionAuditConfig` | 已存在同域审计配置承载

#### OpenQuestions
- None

#### Recommendation
- `reuse`

### ArtifactBinding
- `AlliancePermissionAuditConfig.lastEditorId` -> `extend` -> `AlliancePermissionAuditConfig`
- `Reason`: 已有配置承载点已覆盖同域审计字段
- `Evidence`: `AlliancePermissionAuditConfig`
- `AlliancePermissionAuditConfig.lastEditTime` -> `extend` -> `AlliancePermissionAuditConfig`
- `Reason`: 与现有审计元数据同属配置承载
- `Evidence`: `AlliancePermissionAuditConfig`

### DecisionSynthesis
#### 模块策略建议
- 复用现有配置承载点，禁止新建平行 `AlliancePermissionMeta`
```

### `hybrid` 判例

```md
### DecompositionSnapshot
#### scan scope
- `InventoryPanel`
- `Inventory/Logic`

### CapabilityScan
#### MatchedCapabilities
- `InventoryPanel`：现有 UI 已覆盖刷新展示链路

#### CandidateHosts
- `InventoryPanel`
- `Inventory/Logic`：未命中直接排序策略宿主

#### ReuseRisks
- 若强塞进 `InventoryPanel`，会把展示与排序策略混在一起

#### Evidence
- `InventoryPanel` | `InventoryPanel.Refresh()` | 已覆盖刷新展示链路
- `Inventory/Logic` | 未命中直接排序策略承载 | 需要独立逻辑承载

#### OpenQuestions
- None

#### Recommendation
- `hybrid`

### ArtifactBinding
- `InventoryPanel.Refresh()` -> `reuse` -> `InventoryPanel`
- `Reason`: 现有 UI 已覆盖刷新展示链路
- `Evidence`: `InventoryPanel`
- `InventorySortProfile` -> `new` -> `Inventory/Logic`；理由：现有 UI 承载展示，不适合持久排序策略
- `Evidence`: 现有 `InventoryPanel` 仅承担展示

### DecisionSynthesis
#### 模块策略建议
- 展示链路沿用现有 UI，新增排序配置只落到独立逻辑承载
```

### 非文本输入的双阶段解构

```md
### 阶段 1：原始资产清单
- 顶部：标题“登录”
- 中部：账号输入框、密码输入框、登录按钮

### 阶段 2：功能关联报告
- 登录按钮 -> AuthService.Login(phone, password)
- 忘记密码 -> ResetPasswordPage
```

### `L2` Handoff 最小模板

```md
## Handoff: AllianceMember

### Goal
- 完成成员管理模块

### Owns
- 成员列表、阶级调整、踢人

### Provides
- AllianceMemberList()
- AllianceRankUpdate()

### Requires
- MI_AUTH.CheckPermission()
- MI_EVENT.PublishAllianceEvent()

### Blocks
- None

### Constraints
- 权限检查必须走 MI_AUTH

### Done Criteria
- 成员阶级调整后 UI 正确刷新

### Open Questions
- Risk: 官职加成规则待策划确认
```

## Step 3 模块输出

```md
<!-- PIPELINE_SUMMARY -->
## AllianceMember

Modified files:
- Assets/Scripts/.../AllianceMemberData.cs

Key decisions:
- 权限检查统一走 MI_AUTH
- 事件更新统一走 MI_EVENT

API status:
- AllianceMemberList: implemented
- AllianceRankUpdate: implemented

Handoff Update:
- Implemented Provides: AllianceMemberList, AllianceRankUpdate
- Added Requires: None
- Remaining Blocks: None

COMPLIANCE_CHECKLIST: 6/6 passed
<!-- /PIPELINE_SUMMARY -->

<!-- PIPELINE_DETAIL -->
### Implementation Notes
- 详细实现说明

### Handoff Update
- Implemented Provides:
- Added Requires:
- Remaining Blocks:
- TODO:
- Evidence:

### COMPLIANCE_CHECKLIST
- [x] 命名规范
- [x] Handoff 对齐
<!-- /PIPELINE_DETAIL -->
```

归并规则见 `config/pipeline_protocol.md` 协议 4；这里只保留最小模板。

## Closure / Verdict 判例

### 判例 E1：`GO`

```md
## Dependency Closure Report
### Closed
- M1.Requires X -> MI_AUTH.Provides X

## Done Criteria Coverage
### M1
- [x] 所有业务条件已覆盖

## VERIFICATION_REPORT
### Module Verdicts
- M1: GO

### Global Verdict
- GO

### Reasons
- `Dependency Closure Report` 全部闭合
- `Done Criteria Coverage` 无缺口

### NextAction
- Step 9
```

### 判例 E2：`GO-WITH-CAUTION`

```md
## Dependency Closure Report
### CompletableBlocks
- M4 等待 M6.AddPlayerContribution()

## Done Criteria Coverage
### M4
- [x] 主流程完成
- [ ] 贡献结算待 Step 6 补全

## VERIFICATION_REPORT
### Module Verdicts
- M4: GO-WITH-CAUTION

### Global Verdict
- GO-WITH-CAUTION

### Reasons
- 主流程闭合
- `CompletableBlocks` 只影响增量结算

### NextAction
- Step 6
```

### 判例 E3：`NO-GO`

```md
## Dependency Closure Report
### MissingProvider
- M8.Requires CityBoundaryProvider, provider not found

## VERIFICATION_REPORT
### Module Verdicts
- M8: NO-GO

### Global Verdict
- NO-GO

### Reasons
- `MissingProvider` 未闭合
- 当前无可接受降级路径

### NextAction
- Recovery / re-dispatch
```

## `pipeline_run_id` 生命周期

### 示例 F1：标准闭环中的 run_id / trace / signal / cleanup

下面只展示一个最小时序样例；生命周期规则与合法取值以 `config/pipeline_protocol.md` 为准。

#### Step 1（生成）

`requirement-analysis-agent` 在 Step 1 结束时写入 `PIPELINE_CONTEXT.md` 头部：

```md
pipeline_run_id: pipeline_20260420_143055
```

#### Step 3（自动打标）

`trace-flush` 在本次 pipeline 期间产生的 trace 条目形如：

```md
<!-- TRACE status:pending schema:1 -->
timestamp: 2026-04-20T14:35:12Z
validated: pending-pipeline
pipeline_run_id: pipeline_20260420_143055
modules: [Building, UI]
...
<!-- /TRACE -->
```

模块实现单元无需主动写 `validated`；这是 hook 与 `pipeline_run_id` 的联动结果。

#### Step 5（写回填信号）

`pipeline-verify-agent` 输出 verdict 后，写入 `.claude/traces/.pending_pipeline_result.json`：

```json
{
  "pipeline_run_id": "pipeline_20260420_143055",
  "result": "GO-WITH-CAUTION",
  "finalized": false
}
```

#### Stop Hook（批量回填）

`trace-flush` 读取 result signal 后，按下表处理：

| result | finalized | validated | 含义 |
|---|---|---|---|
| GO | true | true | 一次性合规 |
| GO-WITH-CAUTION | false | pending-pipeline | 还要进入 Step 6 / 重跑 Step 4 / Step 5 |
| GO-WITH-CAUTION | true | true | 补全完成并已重新验收 |
| NO-GO | true | false | 本次 pipeline 判定失败 |

非法或不完整的 result signal 不得被消费；hook 会保留原文件，等待修复后重试。

#### Step 9（清理）

- Cleanup：`PIPELINE_CONTEXT.md` 随整体删除
- Persist：必须删除 `pipeline_run_id:` 行
- 若 `pending-pipeline` 长时间没有被最终 verdict 覆盖，hook 会按过期策略标记为 `invalid`

## 大型系统 / 多 pipeline 判例

### 示例 F2：城市战争系统的主 pipeline + 子 pipeline

这个案例展示三件事：

1. 主 pipeline 如何用顶部状态头表达当前 gate 真相
2. 复杂系统模式下模块如何通过模块配对执行单元完成 dispatch
3. 某个复杂域如何升级为 `sub-pipeline`，并通过 `Parent Summary` 回传父 pipeline

#### 主 pipeline 的 `PIPELINE_CONTEXT.md` 头部

```md
# PIPELINE_CONTEXT.md - CityWar

pipeline_run_id: pipeline_20260511_201500
pipeline_mode: complex
pipeline_current_step: 2
pipeline_lifecycle_state: Frozen
pipeline_decision_status: resolved
pipeline_decision_basis: reuse
pipeline_freeze_status: frozen
pipeline_active_modules: [MI_AUTH, MI_EVENT, UI_CITYWAR, LOGIC_CITYWAR, BATTLE_CITYWAR, MAP_CORE]
pipeline_last_closure_scope: none
pipeline_last_verdict: none
pipeline_result_signal_status: none

---
```

这里的关键不是正文里写了多少解释，而是顶部状态头已经明确说明：

- 当前是 `complex` 模式
- 路线决策已收敛（`decision_status: resolved`）
- Freeze Gate 已通过（`pipeline_freeze_status: frozen`）
- 因此主 agent 可以合法生成当前 wave 的 dispatch，而不是靠正文描述“看起来已经准备好了”

#### Step 1 / Step 2 后的主系统拆分

```md
## Artifact State Table

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| MI_AUTH | SharedCore | Frozen | - | SharedBarrier | CP-01 |
| MI_EVENT | SharedCore | Frozen | - | SharedBarrier | CP-01 |
| MAP_CORE | SharedCore | Frozen | MI_EVENT | SharedBarrier | CP-01 |
| UI_CITYWAR | Leaf | Frozen | LOGIC_CITYWAR,MI_EVENT | Wave-2 | CP-02 |
| LOGIC_CITYWAR | Leaf | Frozen | BATTLE_CITYWAR,MAP_CORE,MI_AUTH | Wave-2 | CP-02 |
| BATTLE_CITYWAR | DomainComplex | NeedsSubpipeline | MAP_CORE,MI_EVENT | SubPipelineBarrier | CP-02 |

## Wave Plan

| Wave | EntryCondition | IncludedModules | DeferredModules | ExitArtifact |
|---|---|---|---|---|
| Wave 1 | Shared core freeze complete | MI_AUTH, MI_EVENT, MAP_CORE | UI_CITYWAR, LOGIC_CITYWAR, BATTLE_CITYWAR | SharedBarrier Ready |
| Wave 2 | SharedBarrier Ready | UI_CITYWAR, LOGIC_CITYWAR | BATTLE_CITYWAR | UI/Logic summaries merged |
| Wave 3 | Child pipeline returns Parent Summary | BATTLE_CITYWAR | - | Global closure ready |
```

这个拆分体现的是：

- `MI_AUTH` / `MI_EVENT` / `MAP_CORE` 先作为共享核冻结
- `UI_CITYWAR` 和 `LOGIC_CITYWAR` 可以在共享核冻结后并行实现
- `BATTLE_CITYWAR` 因为牵涉地图占领、跨城状态同步、战斗结算，直接被标记为 `NeedsSubpipeline`

#### Wave 2 的 dispatch 行

```md
## Wave Dispatch Table

| Wave | Module | ArtifactState | Barrier | DispatchTarget | Inputs | ExpectedOutput | Fallback |
|---|---|---|---|---|---|---|---|
| Wave 2 | UI_CITYWAR | Frozen | SharedBarrier=Ready | paired execution unit for UI_CITYWAR | Frozen Handoff, PCB, UI blueprint slice, MI_EVENT contract | temp/pipeline-output/UI_CITYWAR.md | main agent |
| Wave 2 | LOGIC_CITYWAR | Frozen | SharedBarrier=Ready | paired execution unit for LOGIC_CITYWAR | Frozen Handoff, PCB, logic blueprint slice, MI_AUTH/MAP_CORE contracts | temp/pipeline-output/LOGIC_CITYWAR.md | main agent |
| Wave 2 | BATTLE_CITYWAR | NeedsSubpipeline | SharedBarrier=Ready | sub-pipeline | Parent handoff, shared contracts, battle domain scope | Parent Summary | recovery review |
```

这里先看通用规则，再给一个 UI 例子：

- `module_id = UI_CITYWAR`
- 当前模块类型是 UI 承载域
- `DispatchTarget` 写的是“匹配到该模块的模块配对执行单元”
- 该执行单元再按模块类型装配对应的 agent / skill
- 最终产物仍然写到 `temp/pipeline-output/UI_CITYWAR.md`

例如当 `UI_CITYWAR` 被归入 UI 承载域时，它可以匹配到 `programmer-ui-agent`，并由该 agent 加载 `programmer-ui-skill`。

也就是说，大型系统模式改变的是放行条件和调度记录，不改变“按模块类型匹配模块配对执行单元”的命名约定。

#### 主 pipeline 发给模块配对执行单元的最小卡

```md
Step: 3
module_id: UI_CITYWAR
paired_execution_unit: matched programmer-<module>-agent + same-module programmer-<module>-skill

Read:
- PIPELINE_CONTEXT.md 顶部状态头
- PIPELINE_CONTEXT.md 中的 PCB / BLUEPRINT
- Frozen Handoff: UI_CITYWAR
- Artifact State Table / Wave Dispatch Table / Checkpoint Record
- MI_EVENT 事件契约

Write:
- 当前模块代码
- temp/pipeline-output/UI_CITYWAR.md

Guard:
- 若顶部状态头仍为 PendingDecision -> refuse
- 若 Wave Dispatch Table 中当前行不再满足 barrier -> stop and checkpoint
- 若发现新的跨模块 Requires 超出 Frozen Handoff -> 回写 Handoff Update，不得自行扩边界
```

这个最小卡说明：模块不是因为名字恰好落到某个具体 agent 就自动放行，而是因为当前 wave 的 dispatch 行已经合法建立，随后才交给匹配到的模块配对执行单元执行。对 `UI_CITYWAR` 这种 UI 承载域，最终匹配到的具体实现可以是 `programmer-ui-agent` + `programmer-ui-skill`，但这只是通用规则在该案例里的一个实例。

#### 子 pipeline：`BATTLE_CITYWAR`

当 `BATTLE_CITYWAR` 被标记为 `NeedsSubpipeline` 后，主 pipeline 不直接把它塞进普通 Step 3，而是生成一个子 pipeline 入口：

```md
# PIPELINE_CONTEXT.md - CityWar-Battle-Subpipeline

pipeline_run_id: pipeline_20260511_202100
pipeline_mode: complex
pipeline_current_step: 1
pipeline_lifecycle_state: Discovering
pipeline_decision_status: resolved
pipeline_decision_basis: reuse
pipeline_freeze_status: not_applicable
pipeline_active_modules: [BATTLE_LOOP, BATTLE_UI, SCORE_SETTLEMENT]
pipeline_last_closure_scope: none
pipeline_last_verdict: none
pipeline_result_signal_status: none

---
```

这个子 pipeline 只负责 `BATTLE_CITYWAR` 领域内部的再拆分，例如：

```md
## Artifact State Table

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| BATTLE_LOOP | SharedCore | Frozen | - | BattleBarrier | CP-B01 |
| BATTLE_UI | Leaf | Frozen | BATTLE_LOOP,MI_EVENT | BattleBarrier | CP-B01 |
| SCORE_SETTLEMENT | Leaf | Frozen | BATTLE_LOOP,MI_EVENT,MI_AUTH | BattleBarrier | CP-B01 |
```

子 pipeline 内部仍遵守同一套规则：

- 顶部状态头是真相
- dispatch 仍由 `Wave Dispatch Table` 放行
- Step 3 模块产物仍写入自己的 `temp/pipeline-output/`
- 完成后不把所有细节塞回父 pipeline，只回传 `Parent Summary`

#### 子 pipeline 回传给父 pipeline 的 `Parent Summary`

```md
## Parent Summary

### Scope
- BATTLE_CITYWAR sub-pipeline

### Delivered Contracts
- BattleStart(sessionId, attackerId, defenderId)
- BattleFinish(sessionId, result)
- ScoreSettlement.ApplyBattleResult(cityId, result)

### Remaining Limits
- Replay export deferred

### Parent Impact
- Parent pipeline may move BATTLE_CITYWAR from NeedsSubpipeline -> FrozenSummaryReturned
- Parent Step 4 must include delivered battle contracts in global closure
```

父 pipeline 收到这个 `Parent Summary` 后，更新自己的 checkpoint：

```md
## Checkpoint Record

### CP-03
- Scope: BATTLE_CITYWAR
- ArtifactState: FrozenSummaryReturned
- NewArtifacts: Parent Summary from CityWar-Battle-Subpipeline
- BlockingArtifact: None
- TimeboxUntil: next global closure review
- NextAction: run Wave 3 global Step 4
- RecoveryAction: if parent closure fails, reopen child pipeline only for impacted battle contracts
```

这时父 pipeline 可以进入 Wave 3：

- `UI_CITYWAR.md` 已由匹配到 `UI_CITYWAR` 的模块配对执行单元输出
- `LOGIC_CITYWAR.md` 已由匹配到 `LOGIC_CITYWAR` 的模块配对执行单元输出
- `BATTLE_CITYWAR` 通过子 pipeline 回传 `Parent Summary`
- 主 pipeline 的 Step 4 再做全局 closure，而不是假装 battle 域已经在父 pipeline 内被普通模块一次性完成

#### 这个案例想说明的边界

- 大型系统里，模块仍然通过“匹配到的模块配对执行单元”进入实现；`ui -> programmer-ui-agent / programmer-ui-skill` 只是其中一个具体实例
- 真正决定能不能执行 UI 的，是顶部状态头 + `Wave Dispatch Table`，不是正文里一句“开始做 UI”
- `NeedsSubpipeline` 的复杂域不应伪装成普通 Step 3 模块；它应该升级为子 pipeline，并以 `Parent Summary` 回传
- `pipeline_merge.py` 只负责把普通 Step 3 模块的 `PIPELINE_SUMMARY` 归并回父 `PIPELINE_CONTEXT.md`，不负责裁定 battle 子 pipeline 是否可以启动

## 标准模式最小闭环示意

这个表只帮助快速定位标准模式的最小样例链路，不承担 Step 合同职责；Step 目标、输入、输出、进入条件与出口统一看 `config/step_contracts.md`。

### 示例 G1：Step 1 -> Step 5 / 6 / 9 的最小节奏

| 步骤 | 对应样例 |
|---|---|
| Step 1 | `Step 1 / Handoff` |
| Step 2 | `核心模板` 中的 `PIPELINE_CONTEXT.md` 骨架 |
| Step 3 | `Step 3 模块输出` |
| Step 4 | `Closure / Verdict 判例` |
| Step 5 | `Closure / Verdict 判例` |
| Step 6 | `Closure / Verdict 判例` 中的 `GO-WITH-CAUTION` |
| Step 9 | `pipeline_run_id 生命周期` |

## H. TODO 格式

```md
// TODO: 等待 [模块名].[API名]() 完成后替换
// 预期签名：[返回类型] [API名]([参数列表])
// 使用场景：[场景描述]
```

常见问题：

- 不写模块名和 API 全名
- 没写预期签名
- 留下编译错误而不是规范 TODO
