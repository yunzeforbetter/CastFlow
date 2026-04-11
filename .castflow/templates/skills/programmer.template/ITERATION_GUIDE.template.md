# ITERATION_GUIDE - Programmer-{{MODULE_DISPLAY_NAME}}-Skill 迭代指南

## Skill 定位

本Skill的核心职责：
1. 提供 {{MODULE_DISPLAY_NAME}} 模块的架构理解
2. 提供关键API的使用示例
3. 记录模块特有的约束和陷阱
4. 指导新功能的实现方式

目标用户：需要开发或修改 {{MODULE_DISPLAY_NAME}} 模块的开发者和AI助手

---

## 迭代规则

### Rule 1：新API出现
触发条件：模块中新增了重要的公开API
优先级：High
文件：EXAMPLES.md
检查清单：
  - [ ] 代码示例是否完整可编译
  - [ ] 项目参考是否真实存在

### Rule 2：发现新约束
触发条件：发现新的硬性规则或常见陷阱
优先级：High
文件：SKILL_MEMORY.md
检查清单：
  - [ ] 规则定义是否明确
  - [ ] 检查清单是否可执行

### Rule 3：架构变化
触发条件：模块架构发生重大变化
优先级：High
文件：SKILL.md
检查清单：
  - [ ] 架构概览是否更新
  - [ ] 核心类关系是否更新

---

## 文件职责

| 文件 | 何时修改 | 禁止内容 |
|-----|--------|--------|
| SKILL.md | 架构变化时 | 代码示例、规则定义 |
| EXAMPLES.md | 新API/用法出现时 | 规则定义、日期 |
| SKILL_MEMORY.md | 发现新约束时 | 日期、版本、过程记录 |
| ITERATION_GUIDE.md | 定位变化时 | 日期、版本、检查记录 |

---
