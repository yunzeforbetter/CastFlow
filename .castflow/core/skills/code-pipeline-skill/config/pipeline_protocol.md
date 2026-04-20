# Pipeline Protocol - Pipeline 执行时扩展协议

> **性质**：仅在 code-pipeline 执行时生效。基础协议（GLOBAL_SKILL_MEMORY 协议 1/2）始终生效，无需重复加载。

---

## 协议 1：数据分层合成与物理固化 - P0

执行前将 L1 动态参数与 L2 静态约束编译合成，物理写入看板：
1. 若 Skill 目录有 `params.schema.json` 或 `defaults.json`，必须读取；否则跳过
2. 将合成结果（命名空间、类基类、组件预设等）写入 PCB 的 CONFIG_SYNTHESIS
3. 代码实现以看板参数为准，禁止绕过看板基于记忆编写

---

## 协议 2：地毯式原始资产清单与双阶段解构 - P0

处理 PDF / 导图 / 截图类任务时，必须物理隔离"数据输入"与"逻辑设计"：

**阶段 1 - 原始资产清单**：按顶/中/底/左/右逐块列出所有文字、图标、按钮名、连线，禁止出现"通常来说"、"应该有"等推测词。

**阶段 2 - 功能关联报告**：每个功能组件必须映射到阶段 1 的具体条目，梳理交互链条和数据流向。

**门控**：两阶段输出必须一并提交用户确认，确认前禁止生成代码。

---

## 协议 3：阶段性记忆重置与看板对齐 - P0

物理看板是第一记忆，模型会话是第二记忆。每进入一个原子实现单元前，必须 `Read PIPELINE_CONTEXT.md` 重置注意力。看板未记录的逻辑视为无证据幻觉。

---

## 协议 4：宏观蓝图先行与原子击破 - P0

先声明类名、职责、Public 签名，写入 PCB 的 BLUEPRINT；再将任务拆分为独立小问题，依次解决并标记 `Completed`。

---

## PCB 看板标准结构

看板缺失时以此初始化（禁止凭经验脑补）：

| 区域 | 内容 |
|------|------|
| SHADOW_BANS | Skill Memory 导出的核心禁令（如 No Image） |
| CONFIG_SYNTHESIS | L1/L2 合成参数最终值（Namespace、BaseClass 等） |
| MACRO_SCOPE | 功能点清单、跳转动线图 |
| BLUEPRINT | 类定义、事件契约、物理 API 锚点 |
| ATOMIC_EXECUTION | [x] 已完成 / [ ] 待完成 原子任务 |

---

## 协议 5：pipeline_run_id 追踪协议

每次 pipeline 产生唯一 run_id，将 Step 3 的 trace 条目与 Step 5 的 GO/NO-GO 结果关联。

**Step 1**：生成 `pipeline_{YYYYMMDD}_{HHMMSS}`，写入 PIPELINE_CONTEXT.md 头部：`pipeline_run_id: <id>`

**Step 3**：trace-flush 检测到 PIPELINE_CONTEXT.md 含 `pipeline_run_id:` 字段时，自动将新 trace 的 `validated` 初始化为 `pending-pipeline`，打标透明，programmer-agent 无需感知。

**Step 5**：pipeline-verify-agent 输出 VERIFICATION_REPORT 后，写入 `traces/.pending_pipeline_result.json`：
```
pipeline_run_id: <id>
result: GO
```
Stop Hook 触发时 trace-flush 读取此文件，批量将匹配条目的 `validated` 更新为 true/false，然后删除文件。

**Step 9**：从 PIPELINE_CONTEXT.md 删除 `pipeline_run_id:` 行（Cleanup 模式随文件删除；Persist 模式需手动删除）。

**约束**：禁止遗留过期 run_id（会导致新 trace 被误关联）；中途放弃的 pipeline 其 `pending-pipeline` 条目 7 天后由 trace-flush 标记为 invalid。

---

*Pipeline Protocol | code-pipeline 执行时扩展协议*
