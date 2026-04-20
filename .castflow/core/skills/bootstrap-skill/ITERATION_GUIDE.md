# ITERATION_GUIDE - Bootstrap-Skill 迭代指南

## Skill 定位

本Skill的核心职责：
1. 扫描目标项目的技术栈和模块结构
2. 引导用户确认分析结果
3. 从模板生成项目专属文件
4. 验证生成结果符合规范

目标用户：首次使用 CastFlow 框架的项目，或需要扩展模块的已有项目

---

## 迭代规则

### Rule 1：新技术栈支持
触发条件：需要支持新的编程语言或框架
优先级：High
文件：SKILL.md (Phase 1 扫描规则)
检查清单：
  - [ ] 新语言的文件后缀是否加入检测列表
  - [ ] 新框架的特征文件是否加入检测列表
  - [ ] 对应的命名规范检测逻辑是否更新

### Rule 2：模板改进
触发条件：生成的文件质量不满足需求
优先级：Medium
文件：.castflow/templates/ 下的模板文件
检查清单：
  - [ ] 模板占位符是否完整
  - [ ] 生成的文件是否通过 SKILL_ITERATION 检查

### Rule 3：扫描精度改进
触发条件：模块识别不准确（过多或过少）
优先级：Medium
文件：SKILL.md (Phase 1 模块识别)
检查清单：
  - [ ] 关键词列表是否需要更新
  - [ ] 排除目录列表是否完整

### Rule 4：Phase 0 语言询问的位置和强约束不可削弱
触发条件：调整 Phase 0 / Phase 1 / Phase 2 的顺序或措辞
优先级：Critical（违反将导致多语言机制失效）
文件：SKILL.md (Phase 0 + 顶部执行铁律 + description)、
      SKILL_MEMORY.md (规则 5)、
      EXAMPLES.md (示例 1)
约束：
  - Phase 0 必须保持为流程图的第一个节点，且明文写"主 agent 第一条对外消息"
  - SKILL.md 的 description 字段必须包含触发后立即询问语言的 CRITICAL 指令
  - SKILL.md 顶部「执行铁律」段不得删除或弱化
  - SKILL_MEMORY 规则 5 不得降低优先级（必须为最高）
  - EXAMPLES.md 示例 1 必须先演示 Phase 0 对话再演示扫描
  - Phase 2.1 推荐 Skill（architect）固定生成，不得让用户决定是否跳过
  - Phase 2.1 可选 Skill（debug/profiler）必须在一条消息内打包询问，禁止逐条询问
  - Phase 2.2 补充信息（命名规范 + 框架规则）必须合并为一条消息询问
检查清单：
  - [ ] description 是否仍然包含 "first action MUST be asking the user to choose a language"？
  - [ ] SKILL.md 顶部「执行铁律」是否仍然存在？
  - [ ] 流程图第一个节点是否是 Phase 0？
  - [ ] EXAMPLES.md 示例 1 第一段是否是 Phase 0 语言对话？
  - [ ] SKILL_MEMORY 规则 5 是否标注"违反此规则视为执行失败"？

---

## 文件职责

| 文件 | 何时修改 | 禁止内容 |
|-----|--------|--------|
| SKILL.md | 扫描/生成逻辑变化时 | 代码示例、规则定义 |
| EXAMPLES.md | 新场景出现时 | 规则定义、日期 |
| SKILL_MEMORY.md | 发现新约束时 | 日期、版本、过程记录 |
| ITERATION_GUIDE.md | 定位变化时 | 日期、版本、检查记录 |

---

## 质量指标

指标1：扫描准确率 - 识别的模块中有效模块占比应 > 80%
  测量：用户在 Phase 2 中删除的模块数 / 总识别模块数 < 20%

指标2：生成规范率 - 生成的文件通过 SKILL_ITERATION 检查的比例应 = 100%
  测量：Phase 4 检查全部通过

指标3：用户满意度 - Phase 2 中用户需要大幅调整的次数应最少
  测量：用户新增/删除/修改的模块数

---
