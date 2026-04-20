---
name: architect-skill
description: Project architecture constraint library and design pattern reference
---

# Architect-Skill - 约束规则库与设计模式指导

**定位**: 项目的架构约束规则库和设计模式实践库。可以被用户直接调用来查询架构规则，也可以被其他 Skill、Agent 和 Pipeline 加载来提供约束上下文。

**使用方式**:
- **直接使用**: "用 architect-skill 查一下 Manager 应该怎么创建"
- **Agent 加载**: 所有 agent 默认预加载此 skill
- **Pipeline 编排**: 全流程使用此 skill 作为架构约束来源

**双重身份**:

### 身份1：约束者（必须遵守）
- 强制性规则：所有系统必须无条件遵守的架构规范
- 详见 SKILL_MEMORY.md 中的硬性规则，EXAMPLES.md 中有对应代码示例
- 防护作用：避免架构混乱、循环依赖、编译失败

### 身份2：指导者（参考借鉴）
- 参考实现：经过验证的标准设计模式和最佳实践
- 详见 EXAMPLES.md 中的设计模式和代码示例
- 辅助作用：加速设计决策、提供代码模板

---

## 核心职责

### 第一部分：框架约束（必须遵守）

- 硬性规则和常见陷阱 -> 详见 **SKILL_MEMORY.md**
- 约束规则速查表和代码示例 -> 详见 **EXAMPLES.md** Part 1

### 第二部分：设计模式指导（参考借鉴）

- 设计模式代码示例 -> 详见 **EXAMPLES.md** Part 2-3
- 每个模式包含：描述 -> 何时使用 -> 代码示例 -> 项目参考

---

## 与 Code-Pipeline 的交接

**逻辑位置**: Step 1（需求分析与架构决策）

**产出**：确定项目模式、所属物理层、跨系统通信协议

---

## 核心文件导航

- **SKILL.md** - 本文档（快速导航）
- **EXAMPLES.md** - 设计模式的代码示例和详细讲解
- **SKILL_MEMORY.md** - 硬性规则 + 陷阱详解
- **ITERATION_GUIDE.md** - 维护和演进规则
