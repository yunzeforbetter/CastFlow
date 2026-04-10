# code-pipeline-skill-memory - Pipeline 核心规则

**本文档的性质**：硬性约束（必须遵守）。

---

### 规则 1：单一事实来源 + 上下文索引

**定义**：Pipeline 执行期间，所有工程信息必须通过 PIPELINE_CONTEXT.md 流转。引入 PIPELINE_INDEX.md 作为索引文件降低 token 消耗。

**操作要求**：
- 禁止生成中间输出文件（DECOMPOSITION.md、ANALYSIS_SUMMARY.txt、REPORT.md 等）
- 仅创建 PIPELINE_CONTEXT.md（所有分析写入此文件）
- 可选创建 PIPELINE_INDEX.md（行号索引，帮助后续 Agent 快速定位信息）
- 每个 Agent 启动前，读取 PIPELINE_INDEX.md 快速定位，而非读全文件
- Step 3 并行 agent 的独立输出文件放入 `temp/pipeline-output/` 目录，汇总阶段由主 agent 合并到 PIPELINE_CONTEXT.md

**检查清单**：
- [ ] 是否有 PIPELINE_CONTEXT.md 和 temp/ 以外的临时文件？
- [ ] PIPELINE_INDEX.md 是否与 PIPELINE_CONTEXT.md 保持同步？

---

### 规则 2：API 声明的完整性

**定义**：Step 1 必须清晰声明各模块的"API 需求"和"API 提供"。

**API 声明包含**：API 名称、签名、使用方、状态（精简格式，不扩展描述）

**检查清单**：
- [ ] 所有 API 都在表格中？
- [ ] 是否在 Step 1 末尾提议是否执行 Step 2？

---

### 规则 2.5：Step 2 约束同步与蓝图生成（可选）

**定义**：当功能复杂（跨多模块、有新约束）时，Step 1 末尾的提议可能建议执行 Step 2。

**Step 2 的职责**：
- 加载所有适用约束源（GLOBAL_SKILL_MEMORY、code-pipeline-skill-memory、各 skill 的 SKILL_MEMORY）
- 生成 CONSTRAINT_ALIGNMENT 物理看板，逐 API 检查约束合规
- 生成 BLUEPRINT 明确各模块的类名、职责、public 签名、依赖关系
- 需要用户确认后才进入 Step 3

**何时执行**：
- 推荐执行：功能跨多模块、涉及新框架约束、有复杂的集成需求
- 可以跳过：简单功能、仅调用已验证 API、单模块实现

**输出约束**：仅在 PIPELINE_CONTEXT.md 中，不创建独立文件

---

### 规则 3：TODO 注释的规范

**定义**：当某模块依赖其他模块的 API 且 API 未就绪时，应用 TODO 注释占位，不应留下编译错误或逻辑缺口。

**TODO 格式要求**：包含依赖 API 全名、预期签名、使用场景（格式示例见 EXAMPLES.md）

**检查清单**：
- [ ] Step 4 前，所有 TODO 都被标注清楚？
- [ ] Step 4 时，是否识别了所有 TODO 并分类（CompletableTODO vs BlockingTODO）？
- [ ] Step 6 时，是否所有 CompletableTODO 都被有效代码替换？

---

### 规则 3.5：Step 3 COMPLIANCE_CHECKLIST 前置检查

**定义**：各 implementer agent 在 Step 3 结束时，必须生成 COMPLIANCE_CHECKLIST。

**COMPLIANCE_CHECKLIST 包含**：
- [ ] 命名规范是否遵守（按项目 CLAUDE.md 规则）
- [ ] 是否遵守对应 skill 的 SKILL_MEMORY 规则
- [ ] 所有未验证的 API 是否都用 TODO 标记
- [ ] 代码是否能编译通过
- [ ] 若 Step 2 执行了，是否遵循了 BLUEPRINT 和 CONSTRAINT_ALIGNMENT

**目的**：在 Step 3 就进行早期反馈，而非延迟到 Step 5

---

### 规则 4：模块间的职责边界

**定义**：各模块的实现应专注于自己的职责，约束完全来自 Step 1 的 API 声明（或 Step 2 的 BLUEPRINT）。Pipeline 不预设任何功能必然包含的模块类型。

**允许的功能组合**：
- 功能可以仅包含数据/逻辑层
- 功能可以仅包含展示/UI层
- 功能可以仅包含特定领域层
- 功能可以包含任意组合
- 功能可以完全自定义

**职责原则**：
- 每个模块实现 Step 1 声明的 API
- 调用 Step 1 声明的 API（无论来自哪个模块）
- 不假设其他模块的实现方式

**禁止**：
- 假设功能必然包含某种模块类型
- 预设某个特定的架构模式
- 强加来自其他模块的约束
- 模块间有隐性假设而不是显式的 API 声明

---

### 规则 5：Step 4 的信息匹配职责

**定义**：integration-matcher 负责严格验证，不修改代码。

**MATCHING_REPORT 分类**：
- Consistent: 一致的 API 调用
- SignatureMismatch: 签名差异（需修复）
- UndeclaredAPI: 未声明 API（严重，需返工）
- CompletableTODO: 依赖已完成可补全的 TODO
- BlockingTODO: 依赖未完成的 TODO

**严格约束**：
- 禁止修改代码逻辑
- 禁止替换 TODO（即使依赖已完成，也仅标记）
- 禁止创建新的 API
- 禁止强加新的约束

---

### 规则 6：Step 5 的集成验收与问题处理

**定义**：通过评估 MATCHING_REPORT 做 GO/NO-GO 判定，不进行深度代码检查。

**Step 5 的职责**：
1. 快速规范扫描（二次确认 Step 3 的 COMPLIANCE_CHECKLIST）
2. 评估 MATCHING_REPORT 的严重程度
3. 给出最终判定

**判定评估标准**：
- SignatureMismatch: 参数名不同（可接受） vs 返回类型不同（BLOCKER）
- UndeclaredAPI: 真的未声明（BLOCKER） vs 匹配遗漏（修复）
- CompletableTODO: 标记进入 Step 6
- BlockingTODO: 无法在此处解决，需返工

**最终判定**：
- GO: 无 BLOCKER，一致或轻微差异
- GO-WITH-CAUTION: 有可解决问题（CompletableTODO），需进入 Step 6
- NO-GO: 有 BLOCKER 需返工（返回 Step 1/3）

---

### 规则 7：模块缺少 programmer-agent 时的处理

**定义**：Step 3 需要为模块启动并行 agent 时，如果该模块没有预建的 programmer-agent，pipeline 应按需处理而非失败。

**处理流程**：
1. 检查 `.claude/agents/programmer-{module_id}-agent.md` 是否存在
2. 如果存在：直接使用该 agent
3. 如果不存在：
   - 向用户提议："模块 {module} 没有专属 agent，pipeline 并行实现需要独立 agent 来隔离上下文。是否从模板创建？"
   - 用户同意：执行 `python .castflow/bootstrap.py --agent {module_id}` 生成 agent 文件（或从 `.claude/templates/programmer.template.md` 手动生成）
   - 用户拒绝：该模块由主 agent 直接处理（加载 skill 后实现，不做上下文隔离）

**检查清单**：
- [ ] Step 3 启动前是否检查了每个模块的 agent 是否存在？
- [ ] 缺少 agent 时是否向用户提议？
- [ ] 用户拒绝后是否有降级方案（主 agent 直接处理）？

---

### 规则 8：Agent 提示词优化与缓存机制

**定义**：为降低 token 消耗，所有 Agent 启动时应遵循"精简提示词 + 上下文缓存"模式。

**执行规则**：
- Agent Prompt 限制在 200-300 行，仅包含任务目标、关键步骤、输出格式
- 禁止在 Prompt 中内联完整的 CLAUDE.md、GLOBAL_SKILL_MEMORY.md，仅引用路径
- Agent 先读 PIPELINE_INDEX.md 定位，再精准 Read 对应部分
- 输出限制在 200-500 行，追加到 PIPELINE_CONTEXT.md（Step 3 并行 agent 输出到 `temp/pipeline-output/`，由脚本汇总）

---

### 规则 9：Sub-agent 启动标准

**定义**：Sub-agent 的目的是防止上下文爆炸和注意力分散，不是为了并行加速。启动前必须评估上下文压力。

**启动 Sub-agent 的条件（至少满足一项）**：
- 单模块相关代码量大（预估修改超过 300 行或需要阅读超过 1000 行）
- 多模块代码模式差异大（如 Logic 层和 UI 层同时大改），同一上下文中容易混淆
- Step 1/2 的 API 声明涉及 3 个以上独立系统的交叉调用

**不启动 Sub-agent 的情况**：
- 修改集中在同一模块内
- 总修改量较小，主 agent 能从容处理
- 修改内容模式相似（如批量添加类似方法）

**决策流程**：Step 1 完成后，主 agent 根据拆分结果评估上下文压力，向用户建议 Step 3 的执行策略（主 agent 直接实现 / Sub-agent 分模块实现），由用户最终决定。此判断与 Step 2 建议一并展示。

**检查清单**：
- [ ] Step 1 完成后，主 agent 是否根据拆分结果评估了上下文压力？
- [ ] 是否向用户展示了 Step 3 执行策略建议及理由？
- [ ] 主 agent 能处理的情况是否避免了启动 Sub-agent？

---

## 常见陷阱

### 陷阱 1：API 声明不清晰

**现象**：Step 1 时模块的"提供"列表模糊，导致其他模块不知道具体应该调什么。

**防护**：Step 1 中每个 API 都必须有明确的名称、签名和使用场景。复杂功能建议在 Step 2 进行 BLUEPRINT 对齐。

### 陷阱 2：跳过 TODO 注释

**现象**：某模块发现另一模块 API 未完成，没有用 TODO 注释，直接留下编译错误或虚假实现。

**防护**：规则 3 强制使用 TODO 注释，Step 4 查找和分类，Step 6 补全。

### 陷阱 3：Step 4 成为"重新设计"而非"验证"

**现象**：integration-matcher 发现不一致时，直接修改代码或 API，而不是仅生成报告让 Step 5 决策。

**防护**：规则 5 严格定义 Step 4 仅进行验证和报告，所有决策权留给 Step 5。

### 陷阱 3.5：Step 5 权力越界

**现象**：pipeline-verifier 在 Step 5 直接修改代码，而不仅仅做决策。

**防护**：规则 6 定义 Step 5 的权力边界。具体修改由 Step 3/6 负责。

### 陷阱 4：不同模块假设对方做了某事

**现象**：模块 A 假设模块 B 会发送事件，但模块 B 没有这样做。或两个模块都在改同一份数据。

**防护**：规则 4 强调职责边界。除非 Step 1（或 Step 2 的 BLUEPRINT）明确声明，否则不应该有隐性假设。

### 陷阱 5：跳过 Step 2 导致约束不对齐

**现象**：用户跳过 Step 2，导致 Step 3 各 implementer agent 各自理解约束，Step 4 时发现大量 SignatureMismatch。

**防护**：requirement-analyzer 在 Step 1 必须提议是否建议执行 Step 2。复杂功能推荐执行。

---
