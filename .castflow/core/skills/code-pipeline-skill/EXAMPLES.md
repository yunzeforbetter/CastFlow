# Code Pipeline 示例库

## 设计原则

Pipeline 工作流是完全通用的，不预设任何特定的功能类型组合。功能拆分完全由需求决定。示例重点在于**展示流程结构和决策逻辑**，而非具体业务内容。

---

## 示例 1：仅单层功能

**特点**：仅涉及一个模块，无跨模块依赖。

### Step 1 输出格式

```markdown
## Step 1: 需求拆分与 API 声明

### 功能拆分
- 模块A：[职责描述]

### API 需求分析
| API名称 | 来源 | 使用场景 | 当前状态 |
|--------|------|---------|--------|
| [API1] | 已有服务 | [场景] | 已存在 |
| [API2] | 已有服务 | [场景] | 已存在 |

### 工作流程
1. 所有依赖 API 已存在，无需其他模块实现

### Step 2 建议：跳过（单模块 + 全部 API 已存在）
### Step 3 建议：主 agent 直接实现（修改量小）
```

### 执行决策

- **Step 3**：主 agent 直接实现 + COMPLIANCE_CHECKLIST
- **Step 4**：无需集成匹配（单模块，API已存在）
- **Step 5**：`pipeline-verify-agent` 评估，判为 GO

---

## 示例 2：双层功能

**特点**：两个模块，一个提供数据，一个消费数据。

### Step 1 输出格式

```markdown
### 功能拆分
- 模块A（数据层）：提供数据管理和查询 API
- 模块B（展示层）：消费模块A的 API 进行展示

### API 声明

#### 模块A 提供的 API
| API名称 | 签名 | 使用者 | 场景 | 状态 |
|--------|------|--------|------|------|
| [API1] | [签名] | 模块B | [场景] | 待实现 |
| [API2] | [签名] | 模块B | [场景] | 待实现 |

### 关键决策
1. 模块A 优先实现（模块B 依赖其 API）

### Step 2 建议：可选（有新签名但结构简单）
### Step 3 建议：启动 programmer-A-agent 与 programmer-B-agent 并行
```

### 执行决策

- **Step 3**：`programmer-A-agent` 优先实现，`programmer-B-agent` 可用 TODO 占位
- **Step 4**：`integration-matching-agent` 验证模块B对模块A的 API 调用
- **Step 5**：基于 MATCHING_REPORT 评估

---

## 示例 3：多模块协作

**特点**：三个及以上模块独立但紧密协调。

### Step 1 输出格式

```markdown
### 功能拆分
- 模块A：数据和业务逻辑
- 模块B：界面展示和交互
- 模块C：特定领域处理

### API 声明（略）

### 工作流程
1. 模块A 是所有数据的唯一来源
2. 模块B 和 模块C 都依赖模块A
3. 模块B 和 模块C 之间通过事件/消息通信

### Step 2 建议：推荐执行（跨 3 模块、事件契约需对齐）
### Step 3 建议：启动 3 个 programmer-agent 并行（模块A 优先）
```

### 执行决策

- **Step 2**：推荐执行（多模块交互复杂）
- **Step 3**：模块A 优先，模块B 和 模块C 可并行
- **Step 4**：验证所有跨模块 API 调用
- **Step 5**：基于 MATCHING_REPORT 评估

---

## 示例 4：PIPELINE_CONTEXT.md 标准结构

**描述**：单一事实来源文件模板。头部 PCB 区常驻，尾部 Step 段落追加。

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

## Step 4: 信息匹配与补全
### MATCHING_REPORT
#### [Consistent]
#### [SignatureMismatch]
#### [UndeclaredAPI]
#### [CompletableTODO]
#### [BlockingTODO]

---

## Step 5: 集成验收
### VERIFICATION_REPORT
#### 最终判定: GO / GO-WITH-CAUTION / NO-GO
#### 回填信号: 已写入 .claude/traces/.pending_pipeline_result.json

---

## Step 6-9: 可选步骤与完成
```

---

## 示例 5：TODO 注释格式

**描述**：当一个模块需要调用另一个模块的 API，但该 API 尚未实现时的占位规范。

```
// TODO: 等待 [模块名].[API名]() 完成后替换
// 预期签名：[返回类型] [API名]([参数列表])
// 使用场景：[在什么场景下调用]
```

**常见陷阱**：
- 不写 TODO，直接留下编译错误
- TODO 注释缺少依赖 API 全名或预期签名

---

## 示例 6：pipeline_run_id 完整生命周期

**Step 1（生成）**：

`requirement-analysis-agent` 在 Step 1 结束时写入 PIPELINE_CONTEXT.md 头部：

```
pipeline_run_id: pipeline_20260420_143055
```

**Step 3（自动打标）**：

`trace-flush` 在本次 pipeline 期间产生的所有 trace 条目形如：

```
<!-- TRACE status:pending -->
timestamp: 2026-04-20T14:35:12Z
pipeline_run_id: pipeline_20260420_143055
validated: pending-pipeline
modules: [Building, UI]
...
<!-- /TRACE -->
```

programmer-agent 无需主动感知此字段。

**Step 5（写回填信号）**：

`pipeline-verify-agent` 在给出 GO/NO-GO 判定后写入 `.claude/traces/.pending_pipeline_result.json`：

```json
{
  "pipeline_run_id": "pipeline_20260420_143055",
  "result": "GO-WITH-CAUTION"
}
```

**Stop Hook（批量回填）**：

`trace-flush` 触发时读取此文件，将所有 `pipeline_run_id: pipeline_20260420_143055` 的条目 `validated` 批量更新：

| result | validated |
|--------|-----------|
| GO | true |
| GO-WITH-CAUTION | true |
| NO-GO | false |

然后删除 `.pending_pipeline_result.json`。

**Step 9（清理）**：

- Cleanup 模式：PIPELINE_CONTEXT.md 随整体删除
- Persist 模式：主 agent 手动删除 PIPELINE_CONTEXT.md 中的 `pipeline_run_id:` 行

---

## 示例 7：PDF / 导图类需求的 Step 1（协议 2 触发）

**输入**：用户附带 UI 截图 + 需求描述"实现这个界面的登录流程"。

**Step 1 必须双阶段解构**（pipeline_protocol 协议 2）：

### 阶段 1 原始资产清单

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

### 阶段 2 功能关联报告

```markdown
- 账号输入框 -> 前端校验手机号格式 -> 存入 LoginForm.phone
- 密码输入框 -> 眼睛图标切换 type=password/text -> 存入 LoginForm.password
- 登录按钮 -> 触发 AuthService.Login(phone, password) -> 成功跳转主页 / 失败弹错误
- 忘记密码链接 -> 跳转 ResetPasswordPage
- 注册链接 -> 跳转 RegisterPage
```

**门控**：两阶段输出必须一并提交用户确认，确认前禁止进入 API 声明阶段。

---

## Pipeline 工作流总结表

| 步骤 | 负责Agent | 核心职责 | 输出 |
|------|---------|---------|------|
| **Step 1** | requirement-analysis-agent | Phase 1 探索 + Phase 2 API 声明 + 生成 run_id | PIPELINE_CONTEXT.md（含 PCB 骨架） |
| **Step 2**（可选） | requirement-analysis-agent | L1×L2 合成、BLUEPRINT、ATOMIC_EXECUTION | 填充 PCB 全部区域 |
| **Step 3** | programmer-{module}-agent | 实现代码 + COMPLIANCE_CHECKLIST | 代码 + temp/pipeline-output/*.md |
| **Step 4** | integration-matching-agent | 验证 API 一致性 | MATCHING_REPORT |
| **Step 5** | pipeline-verify-agent | GO/NO-GO 判定 + 写回填信号 | VERIFICATION_REPORT + .pending_pipeline_result.json |
| **Step 6**（可选） | programmer-{module}-agent | 补全 CompletableTODO | 代码更新 |
| **Step 7**（可选） | debug-skill | 边界条件测试 | 修复建议 / 代码更新 |
| **Step 8**（可选） | profiler-skill | 性能诊断 | 优化建议 / 代码更新 |
| **Step 9** | 主 agent | 清理（Cleanup/Persist）+ run_id 处理 | 文件删除或 run_id 行移除 |

---

## 不预设的原则

- 功能不必然包含特定模块类型
- 功能不必然遵循某个特定的架构模式
- 模块类型和数量完全由需求决定
- Step 2 / 6 / 7 / 8 按需启用，由 L1 参数或 Step 1 建议决定
