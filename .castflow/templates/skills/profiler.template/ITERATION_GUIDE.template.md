# ITERATION_GUIDE - Profiler-Skill 迭代指南

## Skill 定位

本Skill的核心职责：
1. 通过识别代码反模式定位性能隐患
2. 提供平台感知的性能红线和优化策略
3. 生成带有量化收益预估的优化报告
4. 支持多平台（Mobile/PC/Server/Web）

目标用户：需要做性能优化的开发者和AI助手

---

## 迭代规则

### Rule 1：新反模式
触发条件：发现新的性能反模式需要加入检查矩阵
优先级：High
文件：SKILL.md（优化检查矩阵）
检查清单：
  - [ ] 反模式是否有明确的判定条件
  - [ ] 是否有对应的优化方案
  - [ ] EXAMPLES.md 中是否有示例

### Rule 2：平台红线调整
触发条件：项目的性能预算发生变化
优先级：High
文件：SKILL.md（性能红线）
检查清单：
  - [ ] 新红线是否有量化标准
  - [ ] 是否按平台分别设定

### Rule 3：项目特定优化项
触发条件：发现项目技术栈特有的性能优化点
优先级：Medium
文件：SKILL.md（项目特定优化项）
检查清单：
  - [ ] 是否与通用检查项重复
  - [ ] 是否有项目中的真实案例

### Rule 4：SKILL_MEMORY 容量治理
触发条件：SKILL_MEMORY.md 字数超过推荐范围（1500字），或 origin-evolve 提出新规则
优先级：High
文件：SKILL_MEMORY.md
规范：遵循 SKILL_ITERATION.md 的 SKILL_MEMORY 容量治理规范（Append/Merge/Retire 操作）

---

## 文件职责

| 文件 | 何时修改 | 禁止内容 |
|-----|--------|--------|
| SKILL.md | 检查矩阵/红线变化时 | 代码示例、规则定义 |
| EXAMPLES.md | 新反模式出现时 | 规则定义、日期 |
| SKILL_MEMORY.md | 发现新约束时 | 日期、版本、过程记录 |
| ITERATION_GUIDE.md | 定位变化时 | 日期、版本、检查记录 |

---
