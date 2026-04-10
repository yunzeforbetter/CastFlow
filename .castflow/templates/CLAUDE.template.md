---
title: Project Rules
---

# CLAUDE.md - 项目全局规则

> 本文档由 CastFlow bootstrap-skill 生成。Skill系统规范见 [SKILL_RULE.md](./.claude/skills/SKILL_RULE.md)

---

## API验证最高优先级规则（P0）- 禁止幻觉API

**硬性规则**：
- 禁止猜测API的使用方式
- 禁止生成伪代码等待用户补充
- 所有API必须有真实来源（EXAMPLES.md / 用户指导 / Grep搜索）

**验证流程**（按序，缺一不可）：
1. 查 Skill 的 EXAMPLES.md；未找到 -> 继续
2. 请用户提供项目中的参考位置；无法提供 -> 继续
3. Grep 项目搜索该API（至少2个真实使用）；搜索无果 -> 继续
4. 在代码中标 TODO，说明"无法验证该API"，请求用户指导

**代码生成后必须检查**：
- [ ] 是否有任何未验证的API（即使看起来合理）？
- [ ] 所有参数名、方法签名是否与真实实现一致？
- [ ] 是否有TODO标记？如有，是否向用户说明了原因？

---

## 使用Skill前的强制检查

**流程**：SKILL_MEMORY.md -> 参数确认 -> 用户同意 -> 执行

**检查清单**：
- [ ] 该Skill是否有SKILL_MEMORY.md？有则完整阅读
- [ ] 是否有params.schema.json？有则确认L1参数（若Skill无此文件则跳过）
- [ ] 在响应中列出所有硬性规则、禁止事项、必须做法
- [ ] 是否涉及学习代码？是则执行"学习->匹配->应用"流程（见下）
- [ ] 执行后代码是否遵守所有约束？

---

## 创建Skill时的强制检查

**触发条件**：用户要求创建新的 Skill（无论是否提及 skill-creator）

**流程**：读取 SKILL_RULE.md -> 参考已有 Skill -> 扫描代码 -> 用户确认 -> 生成

**检查清单**：
- [ ] 是否完整阅读了 `.claude/skills/SKILL_RULE.md`？
- [ ] 生成的文件是否遵循四文件结构（SKILL.md / EXAMPLES.md / SKILL_MEMORY.md / ITERATION_GUIDE.md）？
- [ ] SKILL.md 是否有 YAML 元数据（name + description）？
- [ ] EXAMPLES.md 中的代码是否从项目真实代码提取？
- [ ] 是否参考了 `.claude/skills/` 下已有的 Skill 作为结构和风格范本？
- [ ] 生成后是否通过了 SKILL_RULE.md 的规范检查？

---

## 迭代Skill时的强制检查

**触发条件**：用户要求修改、更新、迭代某个已有的 Skill

**流程**：读取该 Skill 的 ITERATION_GUIDE.md -> 确定改哪个文件 -> 修改 -> 验证

**检查清单**：
- [ ] 是否先阅读了该 Skill 的 `ITERATION_GUIDE.md`？
- [ ] 是否按 ITERATION_GUIDE 中的迭代规则确定了该改哪个文件？
- [ ] 是否遵守了文件职责隔离（代码示例只放 EXAMPLES.md，规则只放 SKILL_MEMORY.md 等）？
- [ ] 修改后是否通过了 SKILL_RULE.md 的规范检查？

---

## 用户反馈处理规范

**流程**：判断范围（单个Skill还是跨Skill）-> 记录到对应文档 -> 通知用户

**判断范围**：
- 单个Skill影响 -> SKILL_MEMORY.md
- 跨Skill或编码规范 -> GLOBAL_SKILL_MEMORY.md

**记录格式**：
- 新硬性规则：规则名称 + 定义 + 检查清单
- 新常见陷阱：现象 + 防护方式

---

## Skill规范体系概览

| 文档 | 位置 | 内容 | 何时阅读 |
|------|------|------|--------|
| **SKILL_RULE.md** | `./.claude/skills/` | 全局结构规范、验收检查 | 创建/迭代Skill时 |
| **GLOBAL_SKILL_MEMORY.md** | `./.claude/skills/` | 跨Skill通用规则 | 调用任何Skill前 |
| **[skill]/SKILL_MEMORY.md** | `./.claude/skills/[skill]/` | 该Skill的硬性规则和陷阱 | 调用该Skill前 |
| **[skill]/ITERATION_GUIDE.md** | `./.claude/skills/[skill]/` | 该Skill的演进规则 | 迭代该Skill时 |

---

## 学习->匹配->应用强制流程

**问题**：大型上下文下学习代码容易忘记约束

**规则**：学习项目代码后，必须先做规则匹配检查，再应用

**完整流程**：见 [GLOBAL_SKILL_MEMORY.md 协议 2](./.claude/skills/GLOBAL_SKILL_MEMORY.md)（学习后强制约束对齐）

**简要步骤**：
1. 学习代码 -> 总结逻辑
2. 列出涉及组件 -> 查找对应约束（SKILL_MEMORY / CLAUDE.md / 项目示例）
3. 逐项对比：学到的用法 vs 约束 -> 标记符合/需调整/无法应用
4. 等待用户确认后，再应用代码

---

## 禁止生成无用报告文件

**规则定义**：禁止为了"完整性"或"规范"而生成无实际使用价值的审查报告、完成报告等文档文件。

**适用范围**：code-pipeline和所有Skill执行流程

**唯一允许的例外**：

- **PIPELINE_CONTEXT.md** - 临时文件，用于记录Step执行信息
  - 用途：步骤间信息交接
  - 限制：必须在工作结束后**删除**
  - 保留时长：仅在执行pipeline期间保留

**执行方式**：

```
code-pipeline执行时:
  1. 创建 PIPELINE_CONTEXT.md（临时）
  2. 在各Step中更新内容
  3. 工作完全结束后立即删除此文件
  4. 禁止保留任何 *_REPORT.md 文件
```

**检查清单**：
- [ ] 用户是否明确要求保存这个报告？
- 如果"否" -> **删除该文件**

---

## 执行记录

每次完成有实际产出的任务后（代码修改、功能实现、bug修复、重构等），将执行摘要静默追加到 `.claude/traces/trace.md`。

**记录格式**：

```
<!-- TRACE status:pending -->
task: {任务描述}
skills: [{使用的Skill列表}]
sub_agents: {是否使用了Sub-agent，几个}
files_modified: [{修改的文件列表}]
retries: {是否有重试，原因}
user_corrections: {用户在过程中的纠正，如有}
outcome: {success/partial/failed}
<!-- /TRACE -->
```

**约束**：
- 静默执行，不向用户展示记录过程
- 仅追加，不修改已有记录
- 纯咨询对话、简单问答不记录
- 记录内容精简，每条控制在 10 行以内

**用途**：trace 供 origin-evolve 分析，用于知识体系的自我进化。用户可通过 `origin evolve` 触发分析。

---

## Bootstrap 触发

当用户说 "bootstrap castflow" 或 "bootstrap 更新核心" 时，读取 `.castflow/core/skills/bootstrap-skill/SKILL.md` 并按其流程执行。

**执行模型**：主 agent 负责扫描（Phase 1）和用户确认（Phase 2），然后为每个确认的 Skill 启动独立的并行 agent 进行代码分析（Phase 3），最后主 agent 收集结果并组装验证（Phase 4）。

---

<!-- ========== 以下为项目段，由用户自行维护 ========== -->
<!-- bootstrap 初始化时会根据扫描结果预填，用户可以随时修改 -->

## 代码命名规范

<!-- 由用户定义。如果未填写，AI 将参考项目现有代码的实际编写规范。 -->
<!-- 示例：私有字段 _camelCase | 私有方法 PascalCase | 公共 PascalCase | 本地变量 camelCase -->

{{NAMING_CONVENTIONS}}

---

## 框架特定规则

<!-- if:unity -->
### Unity .meta 文件管理

`.meta` 文件由 Unity 自动生成和管理，禁止手动创建或编辑。`.gitignore` 不得排除 `.meta` 文件。新增或移动资源必须通过 Unity 编辑器操作。
<!-- endif -->

<!-- if:react -->
### React Hooks 规则

Hooks 只能在函数组件或自定义 Hook 的顶层调用，禁止在条件、循环或嵌套函数中调用。自定义 Hook 必须以 `use` 开头。
<!-- endif -->

<!-- if:go -->
### Go error 处理

函数返回的 error 必须显式处理，禁止用 `_` 忽略。使用 `fmt.Errorf("context: %w", err)` 包装上下文信息。
<!-- endif -->

{{FRAMEWORK_RULES}}

<!-- 注意：架构编码规则（分层架构、资源配对、设计模式等）由 architect-skill 管理，不在 CLAUDE.md 中重复。 -->
<!-- CLAUDE.md 项目段仅放置项目级管理规则（命名规范、文件管理、工具链配置等）。 -->
