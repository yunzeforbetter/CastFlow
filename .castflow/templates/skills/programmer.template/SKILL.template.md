---
name: programmer-{{MODULE_ID}}-skill
description: {{MODULE_DISPLAY_NAME}} module development guide - architecture, API reference, and best practices
---

# Programmer-{{MODULE_DISPLAY_NAME}}-Skill - {{MODULE_DISPLAY_NAME}}模块开发指南

**定位**: {{MODULE_DISPLAY_NAME}} 模块的知识库和开发指南。可以被用户直接调用来理解和修改模块代码，也可以被 Agent 和 Pipeline 加载来提供上下文。

**使用方式**:
- **直接使用**: "用 programmer-{{MODULE_ID}}-skill 帮我理解模块的核心逻辑"
- **Agent 加载**: implementer agent 自动加载此 skill 来理解模块约束
- **Pipeline 编排**: code-pipeline 在 Step 3 中通过 agent 间接使用

**核心职责**:
1. 提供 {{MODULE_DISPLAY_NAME}} 模块的架构概览和核心类关系
2. 提供关键API的使用示例
3. 记录模块特有的约束和常见陷阱
4. 指导新功能的实现方式

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 代码示例和API用法 | EXAMPLES.md |
| 硬性规则和陷阱 | SKILL_MEMORY.md |
| 何时迭代 | ITERATION_GUIDE.md |

## 模块架构概览

{{MODULE_ARCHITECTURE}}

## 核心类关系

{{CORE_CLASSES}}

## 与其他模块的关系

{{MODULE_RELATIONSHIPS}}

---
