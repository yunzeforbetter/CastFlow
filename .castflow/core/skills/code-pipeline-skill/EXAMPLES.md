# Code Pipeline 示例库

> 这里只保留最小骨架与高信号判例。字段规则、读写路径与 Step 调度合同以 `config/pipeline_protocol.md` / `config/handoff_protocol.md` 为准。

## 用法

| 你要看什么 | 去哪看 |
|---|---|
| Step 2 / Step 3 怎么走 | `决策速查` |
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

## 核心模板

### `PIPELINE_CONTEXT.md` 最小骨架

```md
# PIPELINE_CONTEXT.md - [功能名称]

pipeline_run_id: pipeline_20260420_143055

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
### 功能拆分
### API 声明
### 依赖关系
### Handoff Draft / No-Handoff Rationale
### Handoff Level Decision
### Freeze Recommendation
### Step 2 建议
### Step 3 建议

---

## Step 2
### 约束同步
### BLUEPRINT
### Handoff Freeze

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

### Step 1 最小输出

```md
## Step 1

### 功能拆分
- UI
- Logic
- Battle

### 类似功能检索结果
- `Battle`：检索到 `Modules/Battle`，职责与需求高度重合，可作为主承载实现
- `UI`：检索到 `Modules/CommonUI/BattlePanel`，交互流相近，可复用部分展示逻辑
- `Logic`：未检索到可直接承载的现有实现，需要新增逻辑承载层

### 模块策略建议
- 默认：依托已有 `Battle` 能力迭代
- `Logic` 作为新增承载层拆出

### UserDecision
- Battle：若无额外约束，默认按“在已有能力上迭代”推进；如用户指定隔离演进，再切换为全新实现

### API 声明
- UI -> Logic.GetStatus()
- Logic -> Battle.StartBattle()

### 依赖关系
- UI 依赖 Logic
- Logic 依赖 Battle

### Handoff Draft
- UI / Logic / Battle

### Handoff Level Decision
- `L2`：存在跨模块 Requires / Provides，需要冻结边界

### Freeze Recommendation
- Needs Step 2

### Step 2 建议
- 推荐：共享 Battle API 与 UI 刷新事件需要先冻结

### Step 3 建议
- 使用模块配对执行单元并行推进 UI / Logic，Battle 保持 provider 优先
```

### `L0` 最小输出

```md
## Step 1

### 功能拆分
- Inventory

### 类似功能检索结果
- `InventoryPanel`：检索到现有背包展示与刷新链路，可直接作为承载实现

### 模块策略建议
- 默认：在已有 `InventoryPanel` 能力上迭代

### UserDecision
- Inventory：若无额外隔离诉求，默认按“在已有能力上迭代”推进

### API 声明
- Inventory.Refresh()

### 依赖关系
- 无跨模块依赖

### No-Handoff Rationale
- `L0`：单模块、单 agent、无跨模块 `Requires / Provides`

### Handoff Level Decision
- `L0`

### Freeze Recommendation
- 走 `L0` 快速路径，跳过正式 Handoff Freeze

### Step 2 建议
- 跳过

### Step 3 建议
- 直接进入单模块实现，但若新增跨模块依赖需回退升级到 `L1+`
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
