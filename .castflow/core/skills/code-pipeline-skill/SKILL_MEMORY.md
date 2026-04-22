# code-pipeline-skill-memory

**性质**：硬性约束（必须遵守）。与 `config/pipeline_protocol.md` 分工：本文档管 Skill 内部规则，protocol 管执行期协议（L1/L2 合成、run_id 流程、PCB 结构）。

**组织**：A 核心资产 -> B Step 职责（按序）-> C 横跨约束 -> D Agent 调度。

---

## A. 核心资产

### 规则 1：PIPELINE_CONTEXT.md 单一事实来源

所有工程信息通过 PIPELINE_CONTEXT.md 流转。文件物理结构：

- **头部 PCB 区**（常驻，5 子标题必存在）—— 结构定义见 [pipeline_protocol.md "PCB 看板标准结构"](./config/pipeline_protocol.md)
- **尾部 Step 段落**（追加）：Step 1-9 流转记录
- **Step 3 并行产物**：`temp/pipeline-output/{module_id}.md`，由 `python .claude/scripts/pipeline_merge.py` 汇总
- **PIPELINE_INDEX.md**：可选（token 优化），生成后须与主文件同步

**禁止**：生成其他临时分析文件（DECOMPOSITION.md、REPORT.md 等）。

---

## B. Step 职责（按序）

### 规则 2：Step 1 - 需求拆分 + API 声明

`requirement-analysis-agent` 执行两阶段：

- **Phase 1 探索**：学习现有 API、多维分析、2-3 个拆分方案、风险识别
- **Phase 2 声明**：功能拆分清单 + API 声明表（名称 / 签名 / 使用方 / 场景 / 状态）

**附加职责**（pipeline 模式）：
- [ ] 生成 run_id 写入 PIPELINE_CONTEXT.md 头部 —— 格式与生命周期见 [protocol 协议 5](./config/pipeline_protocol.md)
- [ ] 创建 PCB 5 区骨架（可空但标题必存在）
- [ ] 输入含 PDF / 导图 / 截图 -> 先执行 [protocol 协议 2](./config/pipeline_protocol.md)（双阶段解构）
- [ ] 末尾提议 Step 2 策略（推荐 / 跳过）和 Step 3 策略（主 agent / sub-agent）

---

### 规则 3：Step 2 - L1×L2 合成 + BLUEPRINT（可选）

**何时执行**：跨 3+ 模块、新约束、高风险集成。
**何时跳过**：单模块、API 全部已存在。

合成机制与各 PCB 区域映射规则见 [protocol 协议 1](./config/pipeline_protocol.md) 和 [协议 4](./config/pipeline_protocol.md)。本规则只负责触发：

- 决定是否执行 Step 2（条件如上）
- 调用 requirement-analysis-agent 按 protocol 完成合成与填充

**门控**：进入 Step 3 前 `SHADOW_BANS` 与 `CONFIG_SYNTHESIS` 必须非空，否则拒绝。

---

### 规则 4：Step 3 - 模块实现 + COMPLIANCE_CHECKLIST

各 `programmer-{module}-agent` 在 `temp/pipeline-output/{module_id}.md` 末尾生成 COMPLIANCE_CHECKLIST（早期反馈，不等到 Step 5）：

- [ ] 命名是否遵守 `PCB.CONFIG_SYNTHESIS`
- [ ] 是否违反 `PCB.SHADOW_BANS` 任一禁令
- [ ] 是否遵守对应 skill 的 SKILL_MEMORY
- [ ] 未验证 API 是否都 TODO 标记
- [ ] 代码是否能编译
- [ ] 若 Step 2 执行了，是否遵循 `PCB.BLUEPRINT` 和 `PCB.ATOMIC_EXECUTION`

**禁止**：凭记忆编码绕过 PCB；未在 PCB 记录的逻辑视为无证据幻觉。

---

### 规则 5：Step 4 - 信息匹配（仅验证，禁止改代码）

`integration-matching-agent` 输出 MATCHING_REPORT，分类五种问题：

| 分类 | 含义 |
|------|------|
| Consistent | 一致的 API 调用 |
| SignatureMismatch | 签名差异（需修复） |
| UndeclaredAPI | 未声明 API（严重） |
| CompletableTODO | 依赖已完成，TODO 可补全 |
| BlockingTODO | 依赖未完成，TODO 无法补全 |

**禁止**：修改代码逻辑 / 替换 TODO / 创建新 API / 强加新约束（即使依赖已完成也只能标记为 CompletableTODO）。

---

### 规则 6：Step 5 - 集成验收 + 写回填信号（仅决策，禁止改代码）

`pipeline-verify-agent` 职责：

1. 快速规范扫描（二次确认 Step 3 的 COMPLIANCE_CHECKLIST）
2. 评估 MATCHING_REPORT 严重程度
3. 给出判定：`GO` / `GO-WITH-CAUTION` / `NO-GO`
4. 写 `.claude/traces/.pending_pipeline_result.json` —— 文件格式与回填语义见 [protocol 协议 5](./config/pipeline_protocol.md)

**评估标准**：SignatureMismatch 参数名不同（可接受）vs 返回类型不同（BLOCKER）；UndeclaredAPI 真未声明（BLOCKER）vs 声明遗漏（修复即可）。

**禁止**：直接修改代码（具体修改归 Step 3 / 6）。

---

### 规则 7：Step 9 - 清理 + run_id 终结

两种模式（Cleanup / Persist）的处理与 run_id 清理细则见 [protocol 协议 5 "Step 9：清理 run_id"](./config/pipeline_protocol.md)。

本规则强调操作时机：
- Step 9 是 pipeline 的最后一步，必须执行（无论成功或放弃）
- Persist 模式结束前必须确认 `pipeline_run_id:` 行已从 PIPELINE_CONTEXT.md 移除
- 中途放弃的 pipeline 应告知用户 7 天后 trace-flush 会将 `pending-pipeline` 条目标记为 invalid

---

## C. 横跨约束

### 规则 8：TODO 注释规范

当模块 A 依赖模块 B 的 API 但 B 未就绪时，必须用 TODO 占位（不留编译错误、不留虚假实现）。

格式（详见 EXAMPLES.md 示例 5）：
```
// TODO: 等待 [模块名].[API名]() 完成后替换
// 预期签名：[返回类型] [API名]([参数列表])
// 使用场景：[场景描述]
```

---

### 规则 9：模块间职责边界

各模块仅实现 Step 1 声明的 API、调用 Step 1 声明的 API。除非 Step 1（或 Step 2 的 BLUEPRINT）显式声明，否则不应有隐性假设。

**禁止**：
- 假设功能必然包含某种模块类型
- 预设特定架构模式
- 强加来自其他模块的约束
- 模块间隐性假设

---

## D. Agent 调度

### 规则 10：programmer-agent 缺失处理

Step 3 启动并行前，若 `.claude/agents/programmer-{module_id}-agent.md` 不存在：

1. 向用户提议："模块 {module} 无专属 agent，pipeline 并行需独立 agent 隔离上下文。是否从模板创建？"
2. 同意 -> `python .castflow/bootstrap.py --agent {module_id}`
3. 拒绝 -> 主 agent 直接处理（加载对应 skill 后实现，不做上下文隔离）

---

### 规则 11：Sub-agent 启动标准

Sub-agent 用于**防止上下文爆炸**，不是为了加速。启动条件（至少一项）：

- 单模块预估修改 > 300 行 或需阅读 > 1000 行
- 多模块代码模式差异大（如 Logic + UI 同时大改）
- Step 1 涉及 3+ 独立系统的交叉调用

**不启动**：同模块小改、总量小、模式相似（如批量加类似方法）。

决策入口：规则 2 的"Step 1 末尾提议"，由用户基于建议决定。

---

### 规则 12：Agent Prompt 与 token 优化

- Agent Prompt 限制 200-300 行，仅含目标 / 步骤 / 输出格式
- **禁止**在 Prompt 内联完整 CLAUDE.md / GLOBAL_SKILL_MEMORY / SKILL_MEMORY，仅引用路径
- Agent 先读 PIPELINE_CONTEXT.md 的 PCB 区定位，深入时按 PIPELINE_INDEX.md 精准 Read
- Agent 输出限制 200-500 行，追加到 PIPELINE_CONTEXT.md 或 `temp/pipeline-output/`

---
