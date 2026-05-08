# code-pipeline-skill-memory

**性质**：硬性约束（必须遵守）。这里回答“什么必须这样做”；入口和读法见 `SKILL.md`，执行期机制见 `config/pipeline_protocol.md`，模板与判例见 `EXAMPLES.md`。

---

## A. 全局硬规则

### 规则 1：`PIPELINE_CONTEXT.md` 是单一事实来源

所有工程信息通过 `PIPELINE_CONTEXT.md` 流转。文件物理结构：

- **头部 PCB 区**（常驻，5 子标题必存在）—— 结构定义见 `config/pipeline_protocol.md`
- **尾部 Step 段落**（追加）：Step 1-9 流转记录
- **Step 3 并行产物**：`temp/pipeline-output/{module_id}.md`，由 `python .claude/scripts/pipeline_merge.py` 汇总
- **PIPELINE_INDEX.md**：可选（token 优化），生成后须与主文件同步

**禁止**：生成其他临时分析文件（`DECOMPOSITION.md`、`REPORT.md` 等）。

### 规则 8：TODO 注释规范

当模块 A 依赖模块 B 的 API 但 B 未就绪时，必须用 TODO 占位，不留编译错误，也不留虚假实现。

格式：
```md
// TODO: 等待 [模块名].[API名]() 完成后替换
// 预期签名：[返回类型] [API名]([参数列表])
// 使用场景：[场景描述]
```

详见 `EXAMPLES.md` 的 TODO 样例。

### 规则 9：模块间职责边界

各模块仅实现 Step 1 声明的 API、调用 Step 1 声明的 API。除非 Step 1 或 Step 2 的 BLUEPRINT 显式声明，否则不应有隐性假设。

**禁止**：
- 假设功能必然包含某种模块类型
- 预设特定架构模式
- 强加来自其他模块的约束
- 模块间隐性假设

边界判例详见 `EXAMPLES.md` 的 BoundaryViolation 样例。

---

## B. Requirement-analysis 阶段规则（Step 1 / Step 2）

### 规则 2：Step 1 - 需求拆分 + API 声明

`requirement-analysis-agent` 执行两阶段：

- **Phase 1 探索**：学习现有 API、多维分析、2-3 个拆分方案、风险识别
- **Phase 2 声明**：功能拆分清单 + API 声明表（名称 / 签名 / 使用方 / 场景 / 状态）

**附加职责**（pipeline 模式）：
- [ ] 生成 run_id 写入 `PIPELINE_CONTEXT.md` 头部
- [ ] 创建 PCB 5 区骨架（可空但标题必存在）
- [ ] 输入含 PDF / 导图 / 截图 -> 先执行 `config/pipeline_protocol.md` 的双阶段解构协议
- [ ] 使用固定骨架输出：`功能拆分清单 / API声明表 / 依赖关系图 / Handoff Draft / Handoff Level Decision / Freeze Recommendation / Step 2 建议 / Step 3 建议`
- [ ] 末尾提议 Step 2 / Step 3 执行策略

Step 1 模板与输出样例详见 `EXAMPLES.md`，执行卡详见 `requirement-analysis-agent.md`。

### 规则 3：Step 2 - L1×L2 合成 + BLUEPRINT（可选）

**必须执行**（满足任一项）：
- 跨 3+ 模块
- 存在事件 / 状态契约需要对齐
- Handoff Level = L2 / L3 且存在 `unknown` Blocks
- Open Questions 中存在需要先固化约束的 `Risk`
- Freeze Recommendation = `Needs Step 2`

**通常跳过**：
- 单模块
- API 全部已存在且签名明确
- 2 模块且依赖链简单、无新约束

**门控**：进入 Step 3 前，`SHADOW_BANS` 与 `CONFIG_SYNTHESIS` 必须非空。具体填充机制见 `config/pipeline_protocol.md`，Handoff 冻结要求见 `config/handoff_protocol.md`。

Step 2 场景判断详见 `EXAMPLES.md` 的决策速查。

---

## C. Programmer 阶段规则（Step 3）

### 规则 4：Step 3 - 模块实现 + COMPLIANCE_CHECKLIST

各 `programmer-{module}-agent` 在 `temp/pipeline-output/{module_id}.md` 末尾生成 COMPLIANCE_CHECKLIST：

- [ ] 命名是否遵守 `PCB.CONFIG_SYNTHESIS`
- [ ] 是否违反 `PCB.SHADOW_BANS` 任一禁令
- [ ] 是否遵守对应 skill 的 `SKILL_MEMORY`
- [ ] 未验证 API 是否都 TODO 标记
- [ ] 代码是否能编译
- [ ] 若 Step 2 执行了，是否遵循 `PCB.BLUEPRINT` 和 `PCB.ATOMIC_EXECUTION`

**禁止**：凭记忆编码绕过 PCB；未在 PCB 记录的逻辑视为无证据幻觉。

### 规则 14：programmer-agent 只能在 Owns 内实现

Step 3 中各 programmer-agent 只能实现自己 Handoff 的 `Owns`，并兑现 `Provides`。实现过程中新增的跨模块依赖或阻塞，必须写入 Handoff Update。

**禁止**：
- 隐式新增跨模块 Requires
- 替其他模块实现职责
- 将未验证 API 当作真实 API 使用

Handoff Update 模板与协作样例详见 `config/handoff_protocol.md` 与 `EXAMPLES.md`。

---

## D. Validation 阶段规则（Step 4 / Step 5 / Step 9）

### 规则 5：Step 4 - 依赖闭合（仅验证，禁止改代码）

`integration-matching-agent` 输出 Dependency Closure Report，分类以下问题：

| 分类 | 含义 |
|---|---|
| Closed | Requires 已被 Provides 满足 |
| SignatureMismatch | 签名差异（需评估严重度） |
| MissingProvider | Requires 找不到 Provider（严重） |
| BoundaryViolation | 模块实现越出 Owns |
| CompletableBlocks | 可在 Step 6 补全的阻塞 |
| BlockingBlocks | 必须返工或用户决策的阻塞 |
| ImplicitRequires | 实现中出现但 Handoff 未声明的依赖 |

**禁止**：修改代码逻辑 / 替换 TODO / 创建新 API / 强加新约束。

分类口径详见 `config/handoff_protocol.md`，判例详见 `EXAMPLES.md`，执行卡详见 `integration-matching-agent.md`。

### 规则 6：Step 5 - 覆盖验收 + 写回填信号（仅决策，禁止改代码）

`pipeline-verify-agent` 职责：

1. 快速规范扫描（二次确认 Step 3 的 COMPLIANCE_CHECKLIST）
2. 评估 Dependency Closure Report 严重程度
3. 检查 L2/L3 的 Done Criteria Coverage
4. 给出 Module / Global Verdict：`GO` / `GO-WITH-CAUTION` / `NO-GO`
5. 写 `.claude/traces/.pending_pipeline_result.json`

**评估标准**：轻微/严重 `SignatureMismatch`、`MissingProvider`、`ImplicitRequires`、`BoundaryViolation` 的判定口径见 `EXAMPLES.md` 与 `pipeline-verify-agent.md`。

**禁止**：直接修改代码。

### 规则 7：Step 9 - 清理 + run_id 终结

两种模式（Cleanup / Persist）的处理与 run_id 清理细则见 `config/pipeline_protocol.md`。

本规则强调操作时机：
- Step 9 是 pipeline 的最后一步，必须执行（无论成功或放弃）
- Persist 模式结束前必须确认 `pipeline_run_id:` 行已从 `PIPELINE_CONTEXT.md` 移除
- 中途放弃的 pipeline 应告知用户 7 天后 trace-flush 会将 `pending-pipeline` 条目标记为 invalid

### 规则 15：Closure、Coverage 与 Verdict Gate 是 Step 5 的前置条件

Step 4 输出 Dependency Closure Report，Step 5 输出 Done Criteria Coverage 与 Module / Global Verdict。

**GO 前置条件**：
- [ ] Dependency Closure 无 `BlockingBlocks / MissingProvider / BoundaryViolation / ImplicitRequires`
- [ ] 严重 `SignatureMismatch` = 0
- [ ] L2/L3 的 Done Criteria 已覆盖，或仅剩非阻塞 caution
- [ ] 所有模块 verdict = GO

**GO-WITH-CAUTION 前置条件**：
- [ ] 不存在 blocker
- [ ] 剩余问题仅限 `CompletableBlocks / 轻微 SignatureMismatch / 可补全的 Coverage caution`
- [ ] 全局 verdict 不得高于最差模块 verdict

**NO-GO 触发条件**：
- [ ] 任一 `MissingProvider / ImplicitRequires / BoundaryViolation / BlockingBlocks`
- [ ] 任一严重 `SignatureMismatch`
- [ ] Done Criteria 存在不可补全缺口
- [ ] 任一模块 verdict = NO-GO

最小判定样例详见 `EXAMPLES.md`，执行卡详见 `pipeline-verify-agent.md`。

---

## E. Agent 调度规则

### 规则 10：programmer-agent 缺失处理

Step 3 启动并行前，若 `.claude/agents/programmer-{module_id}-agent.md` 不存在：

1. 向用户提议：模块无专属 agent，是否从模板创建
2. 同意 -> `python .castflow/bootstrap.py --agent {module_id}`
3. 拒绝 -> 主 agent 直接处理，不做上下文隔离

### 规则 11：Sub-agent 启动标准

Sub-agent 用于**防止上下文爆炸**，不是为了加速。启动条件（至少一项）：

- 单模块预估修改 > 300 行，或需阅读 > 1000 行
- 多模块代码模式差异大（如 Logic + UI 同时大改）
- Step 1 涉及 3+ 独立系统的交叉调用

**不启动**：同模块小改、总量小、模式相似。

### 规则 12：Agent Prompt 与 token 优化

- Agent Prompt 限制 200-300 行，仅含目标 / 步骤 / 输出格式
- **禁止**在 Prompt 内联完整 `CLAUDE.md / GLOBAL_SKILL_MEMORY / SKILL_MEMORY`，仅引用路径
- Agent 先读 `PIPELINE_CONTEXT.md` 的 PCB 区定位，深入时按 `PIPELINE_INDEX.md` 精准 Read
- Agent 输出限制 200-500 行，追加到 `PIPELINE_CONTEXT.md` 或 `temp/pipeline-output/`

---

## F. Handoff Quality Gate

### 规则 13：多 agent 协作必须先锁定 Handoff

当 Step 3 需要 2+ agent 并行，或模块间存在跨模块 Requires / Provides 时，Step 1 必须生成 Handoff Draft。Handoff 至少包含 `Owns / Provides / Requires / Blocks`；L2/L3 的完整模板见 `config/handoff_protocol.md`。

**进入 Step 3 前置门禁**：
- [ ] Handoff 已从 Draft 变为 Frozen
- [ ] `Owns` 不重叠
- [ ] `Requires` 有候选 Provider，或明确标记 `unknown`
- [ ] `Blocks` 已分类
- [ ] `UserDecision` 类 Open Questions 已解决

**禁止**：Handoff 未冻结时启动多 agent 实现。
