# Code Pipeline 示例库

## 示例设计原则

Pipeline 工作流是完全通用的，不预设任何特定的功能类型组合。功能拆分完全由需求决定。

示例重点在于**展示流程结构和决策逻辑**，而非具体业务内容。

---

## 示例 1：仅单层功能

**特点**：仅涉及一个模块，无跨模块依赖

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
```

### 执行决策

- **Step 3**：programmer-{A}-agent 实现 + COMPLIANCE_CHECKLIST
- **Step 4**：无需集成匹配（仅单模块，API已存在）
- **Step 5**：pipeline-verifier 评估，判为 GO

---

## 示例 2：双层功能

**特点**：两个模块，一个提供数据，一个消费数据

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
```

### 执行决策

- **Step 3**：programmer-{A}-agent 优先实现，programmer-{B}-agent 可使用 TODO 占位
- **Step 4**：integration-matcher 验证模块B对模块A的 API 调用
- **Step 5**：基于 MATCHING_REPORT 评估

---

## 示例 3：多模块协作

**特点**：三个及以上模块独立但紧密协调

### Step 1 输出格式

```markdown
### 功能拆分
- 模块A：数据和业务逻辑
- 模块B：界面展示和交互
- 模块C：特定领域处理

### API 声明

#### 模块A 提供的 API
| API名称 | 使用者 | 场景 |
|--------|--------|------|
| [API1] | 模块B | [场景] |
| [API2] | 模块C | [场景] |

### 工作流程
1. 模块A 是所有数据的唯一来源
2. 模块B 和 模块C 都依赖模块A
3. 模块B 和 模块C 之间通过事件/消息通信
```

### 执行决策

- **Step 2**：推荐执行（多模块交互复杂）
- **Step 3**：模块A 优先，模块B 和 模块C 可并行
- **Step 4**：验证所有跨模块 API 调用
- **Step 5**：基于 MATCHING_REPORT 评估

---

## 示例 4：PIPELINE_CONTEXT.md 结构

**描述**：Pipeline 的单一事实来源文件结构模板。

```markdown
# PIPELINE_CONTEXT.md - [功能名称]

## Step 1: 需求拆分与API声明
### 功能拆分
### API 声明表
### Step 2 建议

---

## Step 2: 约束同步与蓝图生成 [可选]
### 约束来源清单
### BLUEPRINT

---

## Step 3: 模块实现
### 模块A
#### COMPLIANCE_CHECKLIST
### 模块B
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

## Pipeline 工作流总结

| 步骤 | 负责Agent | 职责 | 输出 |
|------|---------|------|------|
| **Step 1** | requirement-analysis-agent | 功能拆分、API声明 + Step 2 建议 | PIPELINE_CONTEXT.md Step 1 |
| **Step 2**（可选） | requirement-analysis-agent | 约束同步、BLUEPRINT | Step 2 |
| **Step 3** | programmer-{module}-agent | 实现代码 + COMPLIANCE_CHECKLIST | 代码文件 + Step 3 |
| **Step 4** | integration-matching-agent | 验证API一致性、MATCHING_REPORT | Step 4 |
| **Step 5** | pipeline-verify-agent | 评估、GO/NO-GO判定 | Step 5 |
| **Step 6**（可选） | programmer-{module}-agent | 补全CompletableTODO | 更新代码 |

## 不预设的原则

- 功能不必然包含特定模块类型
- 功能不必然遵循某个特定的架构模式
- 模块类型和数量完全由需求决定

---
