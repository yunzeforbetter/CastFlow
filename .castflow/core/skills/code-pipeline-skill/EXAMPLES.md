# Code Pipeline 示例库

## 使用方式

这个文件回答“我要看什么样的例子”。

- 想快速判断 Step 2 / Step 3 怎么走：看 **A. 决策速查**
- 想看 `PIPELINE_CONTEXT.md` 应该长什么样：看 **B. 核心模板**
- 想看 Step 1 的典型输出：看 **C. Step 1 输入 / 输出样例**
- 想看多模块协作的 Handoff / Closure / Verdict：看 **D. Handoff 协作样例**
- 想统一 Step 4 / Step 5 的判定口径：看 **E. Step 4 / Step 5 判例**
- 想确认 `pipeline_run_id` 生命周期：看 **F. run_id 生命周期**

示例重点是**帮助读者快速建立工作流心智模型**，不是穷举业务场景。

---

## A. 决策速查

### 示例 A1：Step 1 / Step 2 / Step 3 决策速查

统一收敛轻 / 中 / 重三类场景的 Step 2 / Step 3 建议，避免重复示例堆叠。

| 场景 | 特征 | Step 2 建议 | Step 3 建议 | 典型 verdict 预期 |
|---|---|---|---|---|
| 单模块 | 无跨模块依赖，API 已存在 | 跳过 | 主 agent 直接实现 | GO |
| 双模块 | 一方提供数据，一方消费 API | 可选 | 视修改量决定是否并行 | GO / GO-WITH-CAUTION |
| 多模块 | 3+ 模块、存在状态或事件契约 | 推荐 / 必须 | sub-agent 并行，先冻结 Handoff | GO-WITH-CAUTION / NO-GO |

---

## B. 核心模板

### 示例 B1：`PIPELINE_CONTEXT.md` 标准结构

单一事实来源文件模板。头部 PCB 区常驻，尾部 Step 段落追加。

```markdown
# PIPELINE_CONTEXT.md - [功能名称]

pipeline_run_id: pipeline_20260420_143055

---

## PCB - Pipeline Control Board

### SHADOW_BANS
- 禁止 Update 中 GetComponent / Find [来源: CLAUDE.md]
- 禁止 Logic 层引用 UnityEngine [来源: CLAUDE.md]

### CONFIG_SYNTHESIS
- 命名空间: GameLogic.Modules.[Module]
- 基类: ManagerBase / MonoBehaviour
- 命名规范: 私有字段 _camelCase，公共 PascalCase [来源: CLAUDE.md]

### MACRO_SCOPE
- 功能点1 -> 功能点2 -> 功能点3
- 模块A <-> 模块B（事件通信）

### BLUEPRINT
- BuildingManager : ManagerBase
  - public void UpgradeBuilding(int buildingId)
  - public event Action<int> OnBuildingUpgraded
- BuildingPanelUI : MonoBehaviour
  - private void HandleUpgradeClick()

### ATOMIC_EXECUTION
- [x] 创建 BuildingManager 骨架
- [ ] 实现 UpgradeBuilding 核心逻辑
- [ ] UI 订阅 OnBuildingUpgraded

---

## Step 1: 需求拆分与 API 声明
### 功能拆分
### API 声明表
### Step 2 建议
### Step 3 建议

---

## Step 2: 约束同步与蓝图生成 [可选]
（PCB 的 CONFIG_SYNTHESIS / SHADOW_BANS / BLUEPRINT 的合成过程记录）

---

## Step 3: 模块实现结果
### 模块A（详见 temp/pipeline-output/moduleA.md）
#### COMPLIANCE_CHECKLIST
### 模块B（详见 temp/pipeline-output/moduleB.md）
#### COMPLIANCE_CHECKLIST

---

## Step 4: 依赖闭合
### Dependency Closure Report
#### [Closed]
#### [SignatureMismatch]
#### [MissingProvider]
#### [BoundaryViolation]
#### [CompletableBlocks]
#### [BlockingBlocks]
#### [ImplicitRequires]

---

## Step 5: 集成验收
### VERIFICATION_REPORT
#### 最终判定: GO / GO-WITH-CAUTION / NO-GO
#### 回填信号: 已写入 .claude/traces/.pending_pipeline_result.json

---

## Step 6-9: 可选步骤与完成
```

### 示例 B2：TODO 注释格式

当一个模块需要调用另一个模块的 API，但该 API 尚未实现时的占位规范。

```md
// TODO: 等待 [模块名].[API名]() 完成后替换
// 预期签名：[返回类型] [API名]([参数列表])
// 使用场景：[在什么场景下调用]
```

**常见陷阱**：
- 不写 TODO，直接留下编译错误
- TODO 注释缺少依赖 API 全名或预期签名

---

## C. Step 1 输入 / 输出样例

### 示例 C1：PDF / 导图类需求的 Step 1（协议 2 触发）

**输入**：用户附带 UI 截图 + 需求描述“实现这个界面的登录流程”。

**Step 1 必须双阶段解构**：

#### 阶段 1：原始资产清单

```markdown
顶部：LOGO、标题"欢迎登录"
中部：
  - 输入框1：label "账号"、placeholder "请输入手机号"
  - 输入框2：label "密码"、placeholder "请输入密码"、右侧眼睛图标
  - 复选框："记住我"
底部：
  - 主按钮："登录"、橙色填充
  - 文字链接："忘记密码？"、"新用户注册"
```

#### 阶段 2：功能关联报告

```markdown
- 账号输入框 -> 前端校验手机号格式 -> 存入 LoginForm.phone
- 密码输入框 -> 眼睛图标切换 type=password/text -> 存入 LoginForm.password
- 登录按钮 -> 触发 AuthService.Login(phone, password) -> 成功跳转主页 / 失败弹错误
- 忘记密码链接 -> 跳转 ResetPasswordPage
- 注册链接 -> 跳转 RegisterPage
```

**门控**：两阶段输出必须一并提交用户确认，确认前禁止进入 API 声明阶段。

### 示例 C2：Step 1 固定输出骨架（多模块）

Step 1 在多模块场景下推荐使用统一骨架，降低后续 agent 解析成本。

```markdown
## Step 1: 需求拆分与 API 声明

### 功能拆分清单
- UI：活动入口展示、点击交互、状态刷新
- Logic：活动状态、资格判断、进入流程编排
- Battle：启动活动战斗

### API声明表
| API名称 | 签名 | 来源模块 | 使用方 | 场景 | 状态 |
|--------|------|---------|--------|------|------|
| GetActivityState | ActivityState GetActivityState(int activityId) | Logic | UI | 刷新入口状态 | 待实现 |
| CheckEnterEligibility | bool CheckEnterEligibility(int activityId) | Logic | UI | 判断是否可进入 | 待实现 |
| StartActivityBattle | void StartActivityBattle(int activityId) | Battle | Logic | 启动活动战斗 | 待实现 |

### 依赖关系图
- UI -> Logic
- Logic -> Battle

### Handoff Draft
- 见各模块 Handoff 段落

### Handoff Level Decision
- L2：3 模块协作，存在跨模块 API 与业务完成条件

### Freeze Recommendation
- Needs Step 2：需先固化事件/状态约束再并行实现

### Step 2 建议
- 推荐：涉及 3 模块、状态契约需要对齐

### Step 3 建议
- 启动 sub-agent 并行：UI / Logic / Battle
```

---

## D. Handoff 协作样例

### 示例 D1：Handoff Quality Gate（多模块轻量交接）

**场景**：礼包功能涉及 UI 与 Logic 两个模块。

#### Handoff Draft（Step 1）

```markdown
## Handoff: UI

### Goal
- 展示礼包入口、状态和购买反馈。

### Owns
- PopupBundleUI 展示与交互。

### Provides
- RefreshBundleState(int bundleId)

### Requires
- Logic.GetBundleState(int bundleId)
- Logic.PurchaseBundle(int bundleId)

### Blocks
- unknown：PurchaseBundle 返回结构未确认。

### Constraints
- 遵守 programmer-ui-skill 与项目 UI 命名规范。

### Done Criteria
- 礼包入口按配置显示/隐藏。
- 购买成功后 UI 状态刷新。
- 购买失败时不改变本地状态。

### Open Questions
- TODO：PurchaseBundle 返回结构未确认，先用 TODO 占位。
```

#### Handoff Update（Step 3）

```markdown
## Handoff Update: UI

### Implemented Provides
- RefreshBundleState(int bundleId)

### Added Requires
- None

### Remaining Blocks
- completable：等待 Logic.PurchaseBundle 返回结构后补全失败分支。

### TODO
- TODO: 等待 Logic.PurchaseBundle(int bundleId) 返回结构确认后替换

### Evidence
- 修改文件：Assets/Scripts/GameLogic/Render/UI/Shop/PopupBundles/PopupBundleUI.cs
- 参考 API：现有按钮绑定和弹窗刷新模式
```

#### Dependency Closure（Step 4）

```markdown
## Dependency Closure Report

### Closed
- UI.Requires Logic.GetBundleState -> Logic.Provides GetBundleState

### CompletableBlocks
- UI 购买失败分支等待 Logic.PurchaseBundle 返回结构。

### BlockingBlocks
- None
```

#### Coverage + Verdict（Step 5）

```markdown
## Done Criteria Coverage

### UI
- [x] 礼包入口按配置显示/隐藏
- [x] 购买成功后 UI 状态刷新
- [ ] 购买失败时不改变本地状态：等待 PurchaseBundle 返回结构补全

## Module Verdicts
- UI: GO-WITH-CAUTION
- Logic: GO

## Global Verdict
GO-WITH-CAUTION
```

---

## E. Step 4 / Step 5 判例

### 示例 E1：BoundaryViolation 判定样例

帮助 Step 4 / Step 5 统一理解什么算“越出 Owns”。

#### 应判为 BoundaryViolation
- UI 模块直接实现活动资格判断，而不是调用 Logic 提供的资格 API。
- Logic 模块直接拼接 UI 展示文案或控制按钮显隐。
- Battle 模块直接读取 UI 本地状态决定是否开战。

#### 不应判为 BoundaryViolation
- UI 调用 Logic.GetActivityState() 刷新显示。
- Logic 调用 Battle.StartActivityBattle() 触发战斗。
- 模块内为兑现自身 Provides 而新增私有辅助函数。

#### 灰区处理
- 如果某逻辑既像展示又像业务，优先看 Handoff.Owns；不在 Owns 内就按 BoundaryViolation 处理。

### 示例 E2：Step 5 Verdict Checklist 轻量判定

用最小 decision table 约束 Step 5 的 verdict 输出，减少 agent 漂移。

#### 情况 A：只有 CompletableBlocks

```markdown
## Dependency Closure Report

### Closed
- UI.Requires Logic.GetBundleState -> Logic.Provides GetBundleState

### CompletableBlocks
- UI 购买失败分支等待已完成的返回结构接入。

## Done Criteria Coverage

### UI
- [x] 礼包入口按配置显示/隐藏
- [x] 购买成功后 UI 状态刷新
- [ ] 购买失败时不改变本地状态：可在 Step 6 补全

## Module Verdicts
- UI: GO-WITH-CAUTION
- Logic: GO

## Global Verdict
GO-WITH-CAUTION
```

#### 情况 B：出现 BoundaryViolation

```markdown
## Dependency Closure Report

### BoundaryViolation
- UI 模块直接实现礼包可购买资格判断，而不是调用 Logic.CheckBundleEligibility。

## Done Criteria Coverage

### UI
- [x] 礼包入口按配置显示/隐藏
- [x] 购买成功后 UI 状态刷新

## Module Verdicts
- UI: NO-GO
- Logic: GO

## Global Verdict
NO-GO
```

#### 情况 C：Closure 无阻塞且 Coverage 完整

```markdown
## Dependency Closure Report

### Closed
- UI.Requires Logic.GetBundleState -> Logic.Provides GetBundleState
- UI.Requires Logic.PurchaseBundle -> Logic.Provides PurchaseBundle

## Done Criteria Coverage

### UI
- [x] 礼包入口按配置显示/隐藏
- [x] 购买成功后 UI 状态刷新
- [x] 购买失败时不改变本地状态

## Module Verdicts
- UI: GO
- Logic: GO

## Global Verdict
GO
```

**最小判定规则**：
- 命中 `BoundaryViolation / MissingProvider / ImplicitRequires / BlockingBlocks` -> `NO-GO`
- 无 blocker，但存在 `CompletableBlocks` 或可补全 coverage caution -> `GO-WITH-CAUTION`
- 无 blocker，且 coverage 完整 -> `GO`

#### SignatureMismatch 严重度最小样例

- **轻微 / 可接受或 caution**：参数名不同；不改变调用语义的非关键参数顺序调整。
- **严重 / 必须 NO-GO**：返回类型不同；必需参数缺失；参数类型不兼容导致契约变化。
- **灰区 / 按影响判**：新增可选参数；默认值参数变化；nullable 语义变化。若调用方无需改动且语义不变，可记为 caution；否则按严重处理。

---

## F. `pipeline_run_id` 生命周期

### 示例 F1：`pipeline_run_id` 完整生命周期

#### Step 1（生成）

`requirement-analysis-agent` 在 Step 1 结束时写入 `PIPELINE_CONTEXT.md` 头部：

```md
pipeline_run_id: pipeline_20260420_143055
```

#### Step 3（自动打标）

`trace-flush` 在本次 pipeline 期间产生的所有 trace 条目形如：

```md
<!-- TRACE status:pending -->
timestamp: 2026-04-20T14:35:12Z
pipeline_run_id: pipeline_20260420_143055
validated: pending-pipeline
modules: [Building, UI]
...
<!-- /TRACE -->
```

programmer-agent 无需主动感知此字段。

#### Step 5（写回填信号）

`pipeline-verify-agent` 在给出 GO/NO-GO 判定后写入 `.claude/traces/.pending_pipeline_result.json`：

```json
{
  "pipeline_run_id": "pipeline_20260420_143055",
  "result": "GO-WITH-CAUTION"
}
```

#### Stop Hook（批量回填）

`trace-flush` 触发时读取此文件，将所有 `pipeline_run_id: pipeline_20260420_143055` 的条目 `validated` 批量更新：

| result | validated |
|---|---|
| GO | true |
| GO-WITH-CAUTION | true |
| NO-GO | false |

然后删除 `.pending_pipeline_result.json`。

#### Step 9（清理）

- Cleanup 模式：`PIPELINE_CONTEXT.md` 随整体删除
- Persist 模式：主 agent 手动删除 `PIPELINE_CONTEXT.md` 中的 `pipeline_run_id:` 行

---

## G. 总结表

### 示例 G1：Pipeline 工作流总结表

| 步骤 | 负责Agent | 核心职责 | 输出 |
|---|---|---|---|
| **Step 1** | requirement-analysis-agent | Phase 1 探索 + Phase 2 API 声明 + Handoff Draft + 生成 run_id | `PIPELINE_CONTEXT.md`（含 PCB 骨架 / Handoff） |
| **Step 2**（可选） | requirement-analysis-agent | L1×L2 合成、BLUEPRINT、ATOMIC_EXECUTION、Handoff Freeze | 填充 PCB / 冻结 Handoff |
| **Step 3** | programmer-{module}-agent | 实现代码 + Handoff Update + COMPLIANCE_CHECKLIST | 代码 + `temp/pipeline-output/*.md` |
| **Step 4** | integration-matching-agent | 验证依赖闭合 | Dependency Closure Report |
| **Step 5** | pipeline-verify-agent | Done Criteria Coverage + Module/Global Verdict + 写回填信号 | `VERIFICATION_REPORT` + `.pending_pipeline_result.json` |
| **Step 6**（可选） | programmer-{module}-agent | 补全 CompletableBlocks，完成后回到 Step 4/5 验证闭环 | 代码更新 + 新 Closure/Verdict |
| **Step 7**（可选） | debug-skill | 边界条件测试 | 修复建议 / 代码更新 |
| **Step 8**（可选） | profiler-skill | 性能诊断 | 优化建议 / 代码更新 |
| **Step 9** | 主 agent | 清理（Cleanup/Persist）+ run_id 处理 | 文件删除或 run_id 行移除 |

---

## 不预设的原则

- 功能不必然包含特定模块类型
- 功能不必然遵循某个特定的架构模式
- 模块类型和数量完全由需求决定
- Step 2 / 6 / 7 / 8 按需启用，由 L1 参数或 Step 1 建议决定
