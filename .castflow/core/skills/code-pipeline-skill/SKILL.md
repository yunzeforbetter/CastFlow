---
name: code-pipeline-skill
description: code_pipeline keyword trigger - orchestrates the full workflow from requirement analysis to delivery
---

# Code Pipeline 工作流

**定位**: 流程编排者 (Process Orchestrator)。当需要工业化、多模块协作的开发流程时，Pipeline 提供从需求拆分到验收交付的标准化工序。

**与 Skill/Agent 的关系**:
- Skill 和 Agent 是独立的一等公民，可以被用户直接调用
- Pipeline 是一种**可选的编排方式**，协调多个 Skill 和 Agent 按流程协作
- 简单任务不需要 Pipeline，直接使用 Skill 或 Agent 即可
- 复杂的多模块功能开发，Pipeline 提供结构化的质量保障

**核心职责**:
1. 根据 L1 参数控制执行策略
2. 通过 PIPELINE_CONTEXT.md 管理工程信息
3. 生成 PIPELINE_INDEX.md 降低 token 消耗
4. 协调各 subagent 的执行顺序（使用精简 Prompt）
5. 在关键节点进行状态判定

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 各步骤的具体示例 | EXAMPLES.md |
| 硬性规则和常见陷阱 | SKILL_MEMORY.md |
| 何时迭代、如何维护 | ITERATION_GUIDE.md |
| Pipeline 执行时扩展协议 | config/pipeline_protocol.md |
| L1 参数定义 | config/params.schema.json |

**核心 Agent**（来自 castflow core，直接可用）:
- requirement-analysis-agent: Step 1/2 需求分析
- integration-matching-agent: Step 4 信息匹配
- pipeline-verify-agent: Step 5 集成验收

**模块 Agent**（按需创建，见 `.claude/agents/`）:
- programmer-{module}-agent: Step 3 模块实现（pipeline 运行时按需创建）

**可选质量 Skill**（项目中若存在则自动关联）:
- debug-skill: Step 7 边界条件测试
- profiler-skill: Step 8 性能诊断

---

## 运行决策参数 (L1)

- **execution_steps**: 要执行的步骤 (Step1-9，按需选择)
  - Step1: 需求分析与API声明 (必须)
  - Step2: 约束同步与蓝图生成 (可选)
  - Step3: 模块并行实现 (必须)
  - Step4: 信息匹配与补全 (必须)
  - Step5: 集成验收与问题处理 (必须)
  - Step6: TODO补全与完善 (可选)
  - Step7: 边界条件测试 (可选)
  - Step8: 性能诊断 (可选)
  - Step9: 完成与清理 (必须)

- **context_retention**: Step 完成后的上下文处理
  - Cleanup: 删除 PIPELINE_CONTEXT.md
  - Persist: 保留上下文文件

---

## Workflow 流程

**启动前置**：加载 `config/pipeline_protocol.md`（协议 1-4 + PCB 看板结构）。此扩展协议仅在 pipeline 执行期间生效，补充 GLOBAL_SKILL_MEMORY 的核心协议 1/2。

**Step 1**: 需求拆分与API声明
- Agent: requirement-analyzer
- 执行: Phase 1 问题空间探索 + Phase 2 功能拆分与API声明
- 输出: PIPELINE_CONTEXT.md (Step 1 部分)
- 关键: 末尾提议是否执行 Step 2

**Step 2** [可选]: 约束同步与蓝图生成
- Agent: requirement-analyzer
- 触发: 复杂功能（跨多模块、新约束等），由用户基于 Step 1 建议决策
- 执行: 加载约束源，生成 CONSTRAINT_ALIGNMENT 和 BLUEPRINT
- 输出: 更新 PIPELINE_CONTEXT.md (Step 2 部分)

**Step 3**: 并行实现
- Agent: programmer-{module}-agent（可并行）。若模块无预建 agent，按规则 7 处理（提议创建或降级）
- 执行: 根据 Step 1/2 拆分实现代码，核心数据模块优先
- 约束: 各 agent 结束时生成 COMPLIANCE_CHECKLIST；用 TODO 占位未就绪 API
- 并行输出: 各 agent 写入 `temp/pipeline-output/{module_id}.md`（独立文件，避免并行写入冲突）
- 汇总: 所有 agent 完成后，执行 `python .claude/scripts/pipeline_merge.py` 将各模块输出追加到 PIPELINE_CONTEXT.md 的 Step 3 段

**Step 4**: 信息匹配与补全
- Agent: integration-matcher
- 执行: 验证 API 调用与声明的一致性（严格验证，不修改代码）
- 输出: MATCHING_REPORT + PIPELINE_CONTEXT.md (Step 4 部分)

**Step 5**: 集成验收与问题处理
- Agent: pipeline-verifier
- 执行: 评估 MATCHING_REPORT，给出 GO / GO-WITH-CAUTION / NO-GO
- 输出: VERIFICATION_REPORT + PIPELINE_CONTEXT.md (Step 5 部分)

**Step 6** [可选]: TODO 补全与完善
- 触发: Step 5 判为 GO-WITH-CAUTION
- 执行: 主 agent 根据 MATCHING_REPORT 中的 CompletableTODO 列表，逐个补全（依赖 API 已就绪，替换 TODO 为实际调用）
- 若 TODO 数量多且跨模块，可按需启动对应模块的 programmer-agent 处理

**Step 7** [可选]: 边界条件测试 (debug-skill)

**Step 8** [可选]: 性能诊断 (profiler-skill)

**Step 9**: 完成与清理
- 根据 context_retention 处理 PIPELINE_CONTEXT.md 和 temp/ 目录
  - Cleanup: 删除 PIPELINE_CONTEXT.md、PIPELINE_INDEX.md 和 temp/ 目录
  - Persist: 全部保留（包括 temp/ 下的过程文件）

---

## 重要约束

1. **单一事实来源**: 所有工程信息必须写入 PIPELINE_CONTEXT.md，不创建其他临时文件
2. **顺序依赖**: 核心数据模块应优先完成，其他模块可并行
3. **TODO 使用**: 若 API 未就绪，写 TODO 注释详说依赖（格式见 EXAMPLES.md）
4. **信息明确性**: Step 1 的 API 声明是所有实现的基础
5. **前置合规检查**: Step 3 各 agent 必须生成 COMPLIANCE_CHECKLIST
6. **严格权力边界**: Step 4 仅验证，Step 5 仅决策，Step 6 执行修复
7. **可选约束对齐**: 复杂功能可在 Step 2 进行约束物理化

---
