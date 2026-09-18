# ITERATION_GUIDE - Bootstrap-Skill 迭代指南

## Skill 定位

本Skill的核心职责：
1. 引导 GUI 冷启动（未勾选只拷文件；勾选则粘贴扫描生成提示词）
2. 按提示词（`_skill-gen-queue/` 一次一个）或 GUI JSON 队列（architect/debug/profiler 一次一个）生成（禁止评测环、禁止并行）
3. 不把正文写入适配器镜像
4. 进化开关只走 manager.py evolve

目标用户：首次使用 CastFlow 框架的项目，或需要扩展模块的已有项目

---

## 迭代规则

### Rule 1：新技术栈支持
触发条件：需要支持新的编程语言或框架
优先级：High
文件：`MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` 脚本语言表
检查清单：
  - [ ] 提示词脚本后缀是否覆盖该语言
  - [ ] 清单文件名是否能认出该框架

### Rule 2：生成规范改进
触发条件：生成的文件质量不满足需求
优先级：Medium
文件：`.castflow/core/skills/SKILL_ITERATION.md`（模块 skill 只按此文件写，不再套 programmer 域模板）
检查清单：
  - [ ] 四角色文件是否按 SKILL_ITERATION 写短、有证据
  - [ ] `python .castflow/manager.py validate` 是否通过

### Rule 3：模块划分改进
触发条件：AI 扫出的功能模块过多或过少
优先级：Medium
文件：`MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` + `.castflow/core/rules/module-catalog.md`
检查清单：
  - [ ] 是否按逻辑功能而不是目录/程序集切
  - [ ] 探索是否仍禁止读非脚本资产
  - [ ] 是否排除 CastFlow / `.castflow` / `.castflow-runtime` / 适配器树，且不把框架 skill 放进多选
  - [ ] 生成是否勾选后落 `_skill-gen-queue/`、一次一个、完成后删队列（禁止并行子代理）

### Rule 4：Phase 0 语言询问的位置和强约束不可削弱
触发条件：调整 Phase 0 / Phase 1 / Phase 2 的顺序或措辞
优先级：Critical（违反将导致多语言机制失效）
文件：SKILL.md (Phase 0 + 铁律 + description)、
      SKILL_MEMORY.md (规则 5)、
      EXAMPLES.md (示例 1)
约束：
  - Phase 0 必须保持为流程图的第一个节点，且明文写"主 agent 第一条对外消息"
  - 语言询问写在 SKILL.md 正文，不要塞进 description（description 只负责召回）
  - SKILL.md 顶部「执行铁律」段不得删除或弱化
  - SKILL_MEMORY 规则 5 不得降低优先级（必须为最高）
  - EXAMPLES.md 示例 1 必须先演示 Phase 0 对话再演示扫描
  - Phase 2 推荐 Skill（architect）固定生成，不得让用户决定是否跳过
  - Phase 2 可选 Skill（debug/profiler）必须在一条消息内打包询问，禁止逐条询问
  - Phase 3 补充信息（命名规范 + 框架规则）须单独一条消息询问（与 Phase 2 分开发送，禁止合并为一条）
  - 生成：`/goal` 走 `_skill-gen-queue/` 一次一个；architect/debug/profiler 走 GUI JSON 队列一次一个。禁止并行子代理。正文按 `SKILL_ITERATION.md`。
检查清单：
  - [ ] description 是否短、专名触发、一句 NOT？
  - [ ] SKILL.md 是否仍有 **铁律**（首条消息 = Phase 0）？
  - [ ] 流程图第一个节点是否是 Phase 0？
  - [ ] EXAMPLES.md 示例 1 第一段是否是 Phase 0 语言对话？
  - [ ] SKILL_MEMORY 规则 5 是否标注"违反此规则视为执行失败"？

格式和职责隔离见 SKILL_ITERATION.md，不要把那份表抄到这里。

## 质量指标

指标1：扫描准确率 - 识别的模块中有效模块占比应 > 80%
  测量：用户在 Phase 2 中删除的模块数 / 总识别模块数 < 20%

指标2：生成规范率 - `python .castflow/manager.py validate` 全部通过

指标3：用户满意度 - Phase 2 中用户需要大幅调整的次数应最少
  测量：用户新增/删除/修改的模块数

---
