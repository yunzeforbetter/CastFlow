# ITERATION_GUIDE - Code Pipeline Skill 迭代指南

## Skill 定位

**code-pipeline-skill 是流程编排者 (Process Orchestrator)**

核心职责：
- 根据 L1 参数驱动执行流程
- 通过 PIPELINE_CONTEXT.md（含 PCB 头部区）管理工程信息
- 协调各角色 subagent 的执行顺序
- 通过 pipeline_run_id 与进化系统形成反馈闭环

不负责：
- 具体的代码生成逻辑（交给各 implementer agent）
- 规则和约束的定义（来自 Step 1 的 API 声明 + L2 约束源）
- 功能模块的具体实现细节

---

## 迭代规则

### 规则 0：Token 消耗优化与上下文管理

**触发条件**：token 消耗过高
**优先级**：High
**文件**：SKILL_MEMORY.md（规则 12）

**优化方案**：
1. 禁止中间输出文件：所有分析结果直接写入 PIPELINE_CONTEXT.md（含 PCB）
2. 生成 PIPELINE_INDEX.md：行号索引，帮助 Agent 精准定位
3. 精简 Agent Prompt：限制在 200-300 行
4. 约束文件缓存：第一个 Agent 读取并摘要，后续 Agent 读取 PCB.CONFIG_SYNTHESIS 而非原始约束

---

### 规则 1：Workflow 步骤的演进

**触发条件**：现有步骤无法满足新的工作流需求
**优先级**：Medium
**文件**：SKILL.md + EXAMPLES.md

**检查清单**：
- [ ] 新步骤的职责清晰
- [ ] PIPELINE_CONTEXT.md 结构已更新（包括 PCB 区的变更）
- [ ] EXAMPLES.md 中有新步骤示例
- [ ] 与 pipeline_run_id 生命周期的交互已明确

---

### 规则 2：Subagent 职责的边界

**触发条件**：某 subagent 职责模糊或与其他 agent 重叠
**优先级**：High
**文件**：SKILL.md + SKILL_MEMORY.md

**检查清单**：
- [ ] 每个 subagent 有唯一职责
- [ ] 输入和输出必须清晰
- [ ] 不强加超出职责范围的约束
- [ ] Agent 名称与 `.claude/agents/` 目录中的文件名一致

---

### 规则 3：进化系统对接的演进

**触发条件**：validated 映射规则变更，或 pipeline_run_id 生命周期需调整
**优先级**：High
**文件**：config/pipeline_protocol.md（协议 5）+ SKILL_MEMORY.md（规则 2/6/7 的 run_id 相关条目）+ EXAMPLES.md（示例 6）

**检查清单**：
- [ ] 三个文件的映射规则一致
- [ ] 新增 result 类型是否有对应的 validated 取值
- [ ] Step 9 的清理逻辑是否覆盖新场景

---

## 文件职责

| 文件 | 何时修改 | 禁止内容 |
|-----|--------|--------|
| SKILL.md | 工作流骨架变化时（步骤增减、L1 参数变更） | 代码示例、规则详细定义 |
| EXAMPLES.md | 新场景出现时 | 规则定义、日期 |
| SKILL_MEMORY.md | 发现新硬性约束时 | 日期、版本、过程记录 |
| ITERATION_GUIDE.md | 定位变化时 | 日期、版本、检查记录 |
| config/pipeline_protocol.md | 执行期协议变化时（PCB 结构、run_id 流程、L1/L2 合成规则） | 日期、与 SKILL_MEMORY 重复的规则 |
| config/params.schema.json | L1 参数定义变化时 | 默认值说明（放 defaults.json） |
| config/defaults.json | L1 默认值调整时 | 非 schema 字段 |

---

## 禁止事项

- 创建除 PIPELINE_CONTEXT.md / PIPELINE_INDEX.md / temp/pipeline-output/ 外的临时分析文件
- 让 code-pipeline-skill 本身包含实现逻辑，仅编排不实现
- 跳过 PIPELINE_CONTEXT.md，直接通过 agent 通信
- 在 Step 4 时修改代码逻辑，仅验证和分类
- 在 Step 5 时直接修改代码，仅评估和决策
- 在 PCB 区域凭记忆填写，必须从 L1/L2 合成（协议 1）
- 遗留未清理的 pipeline_run_id 行（Persist 模式的常见陷阱）
