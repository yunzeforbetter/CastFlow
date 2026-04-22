---
name: code-pipeline-skill
description: code_pipeline keyword trigger - orchestrates the full workflow from requirement analysis to delivery
---

# Code Pipeline 工作流

**定位**: 流程编排者 (Process Orchestrator)。协调多 Skill / Agent 按标准工序协作，输出可追溯的工程决策与代码实现。

**不是**: 代码生成者、规则定义者、执行引擎。

**适用**: 多模块协作、跨系统改造、高风险功能。简单任务直接用 Skill / Agent，不走 pipeline。

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 单层功能流程示例 | EXAMPLES.md#示例-1 |
| 双层功能流程示例 | EXAMPLES.md#示例-2 |
| 多模块并行示例 | EXAMPLES.md#示例-3 |
| TODO 注释规范示例 | EXAMPLES.md#示例-5 |
| PCB 单一事实来源（规则 1） | SKILL_MEMORY.md#规则-1 |
| Step 1 需求拆分（规则 2） | SKILL_MEMORY.md#规则-2 |
| Step 2 L1×L2 合成（规则 3） | SKILL_MEMORY.md#规则-3 |
| Step 3 模块实现（规则 4） | SKILL_MEMORY.md#规则-4 |
| TODO 注释规范（规则 8） | SKILL_MEMORY.md#规则-8 |
| programmer-agent 缺失处理（规则 10） | SKILL_MEMORY.md#规则-10 |
| Sub-agent 启动标准（规则 11） | SKILL_MEMORY.md#规则-11 |
| L1×L2 合成机制（协议 1） | config/pipeline_protocol.md#协议-1 |
| PDF / 导图双阶段解构（协议 2） | config/pipeline_protocol.md#协议-2 |
| PCB 看板标准结构 | config/pipeline_protocol.md#pcb-看板标准结构 |
| run_id 生命周期（协议 5） | config/pipeline_protocol.md#协议-5 |
| L1 参数 Schema / 默认值 | config/params.schema.json、config/defaults.json |
| 迭代维护 | ITERATION_GUIDE.md |

---

## 运行前置（按序加载）

1. **GLOBAL_SKILL_MEMORY.md** 协议 1-5（全部生效）
2. **config/pipeline_protocol.md** 协议 1-5（pipeline 期间附加生效）
3. **config/params.schema.json + defaults.json** -> 合成 L1 参数
4. **项目 CLAUDE.md + 相关 SKILL_MEMORY** -> 提取 L2 约束
5. **初始化 PIPELINE_CONTEXT.md**（含 PCB 头部区 + run_id）

---

## 核心资产

**PIPELINE_CONTEXT.md 单一事实来源**，含两个正交维度：

- **PCB 看板区**（头部，常驻）：SHADOW_BANS / CONFIG_SYNTHESIS / MACRO_SCOPE / BLUEPRINT / ATOMIC_EXECUTION —— 认知抓手，防幻觉
- **Step 段落区**（尾部，追加）：Step 1-9 流转记录 —— 过程追踪

每原子单元开工前必须 Read PIPELINE_CONTEXT.md（协议 3）。PCB 未记录的逻辑视为无证据幻觉。

---

## 工作流

**Step 1**: 需求拆分 + API 声明
- Agent: `requirement-analysis-agent`（Phase 1 问题空间探索 -> Phase 2 功能拆分 + API 声明）
- 若输入含 PDF/导图/截图 -> 先执行 pipeline_protocol 协议 2（双阶段解构）
- 生成 `pipeline_run_id: pipeline_{YYYYMMDD}_{HHMMSS}` 写入 PIPELINE_CONTEXT.md 头部
- 末尾提议：Step 2 / Step 3 执行策略

**Step 2** [可选]: 约束同步 + BLUEPRINT
- Agent: `requirement-analysis-agent`
- 合成 L1 × L2 -> 写入 PCB.CONFIG_SYNTHESIS / SHADOW_BANS
- 类名/签名/事件契约 -> 写入 PCB.BLUEPRINT
- 用户确认后进入 Step 3

**Step 3**: 模块并行实现
- Agent: `programmer-{module}-agent`（缺失按 SKILL_MEMORY 规则 10 处理）
- 各 agent 末尾生成 COMPLIANCE_CHECKLIST，TODO 占位未就绪 API
- 并行输出 -> `temp/pipeline-output/{module_id}.md`
- 汇总：`python .claude/scripts/pipeline_merge.py`

**Step 4**: 信息匹配（严格验证，禁止改代码）
- Agent: `integration-matching-agent`
- 输出 MATCHING_REPORT：Consistent / SignatureMismatch / UndeclaredAPI / CompletableTODO / BlockingTODO

**Step 5**: 集成验收（仅决策，禁止改代码）
- Agent: `pipeline-verify-agent`
- 判定 GO / GO-WITH-CAUTION / NO-GO
- 写入 `.claude/traces/.pending_pipeline_result.json`（进化系统回填 validated）

**Step 6** [可选]: CompletableTODO 补全（GO-WITH-CAUTION 触发）

**Step 7** [可选]: 边界条件测试（debug-skill）

**Step 8** [可选]: 性能诊断（profiler-skill）

**Step 9**: 完成与清理
- Cleanup: 删除 PIPELINE_CONTEXT.md、PIPELINE_INDEX.md、`temp/pipeline-output/`
- Persist: 全部保留，**并从 PIPELINE_CONTEXT.md 删除 pipeline_run_id 行**（防止下次 trace 误关联）

---

## L1 运行参数

- `execution_steps`: 数组，要执行的步骤子集（Step1/3/4/5/9 为必选，其他可选）
- `context_retention`: `Cleanup` | `Persist`

详见 `config/params.schema.json`。

---

## 进化系统对接

pipeline 通过 `pipeline_run_id` 将 Step 3 的 trace 与 Step 5 的 GO/NO-GO 结果关联，为自我进化提供验证信号：

| Step 5 判定 | validated | 含义 |
|-----------|-----------|------|
| GO | true | 一次性合规，成功模式 |
| GO-WITH-CAUTION | true | 经补全后合规，包含可复用修复经验 |
| NO-GO | false | P0 反面教材（origin-evolve 最高优先级） |

详见 pipeline_protocol.md 协议 5。
