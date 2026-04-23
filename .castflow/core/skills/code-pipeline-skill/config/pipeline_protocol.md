# Pipeline Protocol - 执行时扩展协议

> **性质**：仅在 code-pipeline 执行时生效。GLOBAL_SKILL_MEMORY 的全部 5 条协议（物理证据、约束对齐、执行模式、IDP、validated）**始终生效**，本协议在其上叠加。

---

## 协议 1：L1 × L2 合成 -> 物理固化（P0）

**L1（动态参数）**：来自 `config/params.schema.json` 的运行时选择，默认值见 `config/defaults.json`。
- execution_steps
- context_retention

**L2（静态约束）**：来自项目的不可变约束源。
- 项目 CLAUDE.md（命名规范、框架规则）
- `.claude/skills/GLOBAL_SKILL_MEMORY.md`（运行时协议）
- 相关 Skill 的 `SKILL_MEMORY.md`（模块规则）

**合成规则**（Step 2 执行或 Step 3 启动前）：

1. L1 决定**走什么步骤**（execution_steps）
2. L2 提取**硬性红线**：
   - 命名规范 -> 写入 PCB.CONFIG_SYNTHESIS
   - 核心禁令（如 "禁止 Update 中 GetComponent"）-> 写入 PCB.SHADOW_BANS
   - 框架命名空间、基类 -> 写入 PCB.CONFIG_SYNTHESIS
3. 代码实现以 PCB 参数为准，禁止绕过看板基于记忆编写。

**检查**：PCB.CONFIG_SYNTHESIS 与 SHADOW_BANS 非空才允许进入 Step 3。

---

## 协议 2：PDF / 导图 / 截图任务的双阶段解构（P0）

**触发条件**：Step 1 输入包含 PDF、设计稿、UI 截图、流程导图等非文本资产。

**阶段 1 - 原始资产清单**：
按顶/中/底/左/右逐块列出所有文字、图标、按钮名、连线，禁止出现"通常来说"、"应该有"等推测词。

**阶段 2 - 功能关联报告**：
每个功能组件必须映射到阶段 1 的具体条目，梳理交互链条和数据流向。

**门控**：两阶段输出一并提交用户确认，确认前禁止生成代码与 API 声明。

**输出位置**：PIPELINE_CONTEXT.md 的 Step 1 段落（子标题 `### 阶段 1 原始资产清单` / `### 阶段 2 功能关联报告`）。

---

## 协议 3：阶段性记忆重置与看板对齐（P0）

**物理看板是第一记忆，模型会话是第二记忆。**

每进入一个原子实现单元前：
1. `Read PIPELINE_CONTEXT.md`（至少头部 PCB 区）
2. 对齐 PCB.BLUEPRINT 中的签名与 PCB.CONFIG_SYNTHESIS 中的命名
3. PCB 未记录的逻辑视为无证据幻觉，必须先补入 PCB 再实现

---

## 协议 4：宏观蓝图先行与原子击破（P0）

**Step 2 或 Step 3 启动前**：
1. 声明类名、职责、Public 签名、事件契约 -> PCB.BLUEPRINT
2. 功能点清单、跳转动线 -> PCB.MACRO_SCOPE
3. 任务拆分为原子单元 -> PCB.ATOMIC_EXECUTION（`[ ]` 未完成 / `[x]` 已完成）

Step 3 实现时按原子单元依次推进，每完成一项更新 `[x]`。

---

## 协议 5：pipeline_run_id 追踪与进化回填（P0）

每次 pipeline 产生唯一 run_id，将 Step 3 的 trace 条目与 Step 5 的验收结果关联，形成进化系统的反馈闭环。

### Step 1：生成 run_id

格式：`pipeline_{YYYYMMDD}_{HHMMSS}`

写入 PIPELINE_CONTEXT.md 头部（PCB 之前）：
```
pipeline_run_id: pipeline_20260420_143055
```

### Step 3：自动打标

`trace-flush` 检测到 PIPELINE_CONTEXT.md 含 `pipeline_run_id:` 字段时，自动将新产生的 trace 条目 `validated` 初始化为 `pending-pipeline`，并记录 `pipeline_run_id` 字段。programmer-agent 无需感知此行为。

### Step 5：写回填信号

`pipeline-verify-agent` 输出 VERIFICATION_REPORT 后，写入 `.claude/traces/.pending_pipeline_result.json`：

```json
{
  "pipeline_run_id": "pipeline_20260420_143055",
  "result": "GO"
}
```

`result` 取值：`GO` / `GO-WITH-CAUTION` / `NO-GO`

### Stop Hook：批量回填

`trace-flush` 触发时读取此文件：

| result | validated | 进化系统语义 |
|--------|-----------|------------|
| GO | true | 合规实现，成功模式 |
| GO-WITH-CAUTION | true | 经 Step 6 补全后合规，包含修复经验 |
| NO-GO | false | P0 反面教材（origin-evolve-skill 优先级最高） |

批量更新匹配 `pipeline_run_id` 的所有 trace 条目后，删除 `.pending_pipeline_result.json`。

### Step 9：清理 run_id

- **Cleanup 模式**：PIPELINE_CONTEXT.md 随整体删除，run_id 自动消失
- **Persist 模式**：必须手动从 PIPELINE_CONTEXT.md 删除 `pipeline_run_id:` 行

**约束**：
- 禁止遗留过期 run_id（会导致下次 pipeline 的新 trace 被误关联到已结束的 run_id）
- 中途放弃的 pipeline 其 `pending-pipeline` 条目由 `trace-flush` 按 Step 0 规则（7 天后）标记为 invalid

---

## PCB 看板标准结构

PIPELINE_CONTEXT.md 的头部常驻区。初始化时以下区域全部创建（可为空，但标题必须存在）：

| 区域 | 内容 | 写入时机 |
|------|------|---------|
| SHADOW_BANS | L2 提取的核心禁令（如 No Update GetComponent） | Step 2 或 Step 3 启动前 |
| CONFIG_SYNTHESIS | L1 × L2 合成参数（命名空间、命名规范、基类等） | Step 2 或 Step 3 启动前 |
| MACRO_SCOPE | 功能点清单、跳转动线、模块关系 | Step 1/2 |
| BLUEPRINT | 类定义、Public 签名、事件契约、物理 API 锚点 | Step 2 |
| ATOMIC_EXECUTION | `[x]` 已完成 / `[ ]` 待完成 原子任务 | Step 2 初始化，Step 3/6 更新 |

**初始化方式**：Step 1 结束时 `requirement-analysis-agent` 创建 PCB 骨架（空区），Step 2（如执行）填充，Step 3 在实现过程中持续更新 ATOMIC_EXECUTION。

---

*Pipeline Protocol | code-pipeline 执行时扩展协议*
