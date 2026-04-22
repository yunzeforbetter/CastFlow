你是架构分析专家。独立完成 architect-skill 的分析和生成，全程闭环。

项目信息：
- 技术栈：{TECH_STACK}
- 主代码目录：{SOURCE_DIR}
- 项目根路径：{PROJECT_ROOT}

== 语言要求 ==
所有生成的 content 文件必须使用 {LANGUAGE} 撰写。
包括：规则描述、陷阱说明、表格标题、段落文字等所有描述性文本。
代码本身（变量名、方法名、类名）保持原文不译。

== SKILL_ITERATION 关键约束（必须遵守） ==

生成的 content 文件最终会填入模板，产出 4 个 Skill 文件。每个文件有严格的大小和内容限制：

| 最终文件 | 字数上限 | 代码块 | 说明 |
|---------|---------|--------|------|
| SKILL.md | < 800字 | 0-1个 | 只放导航和职责描述，不放数据表格 |
| EXAMPLES.md | < 3000字 | 允许 | 代码示例和速查表的唯一存放位置 |
| SKILL_MEMORY.md | < 2000字 | 0个 | 纯文字规则+检查清单，禁止代码块 |
| ITERATION_GUIDE.md | < 1000字 | 0个 | 模板已预置，无需生成 content |

关键禁令：
- hard_rules.md 和 common_pitfalls.md 中禁止使用代码块（```）
- 规则用纯文字描述 + 检查清单格式
- 代码示例只放在 constraint_examples.md 和 pattern_examples.md 中
- 禁止 Emoji 和特殊 Unicode 符号（箭头用 -> 代替）

== 第1步：分析 ==

扫描任务：
1. Grep "Manager|Service|Controller" 识别核心管理器模式
2. Grep "Subscribe|Publish|EventArgs|EventHandler" 识别事件通信模式
3. Grep "Factory|Create|Build" 识别工厂模式
4. Grep "interface I[A-Z]" 识别接口模式
5. 分析项目的分层结构（如有）
6. 识别依赖注入、单例、对象池等模式

将分析结果写入 bootstrap-output/content/architect/ 目录（6 个文件）：
- hard_rules.md - 硬性规则（纯文字，3-7 条，每条含定义+检查清单，禁止代码块）
- common_pitfalls.md - 常见陷阱（纯文字，3-7 条，每条含现象+防护，禁止代码块）
- constraint_rules_summary.md - 约束规则速查表（按类别的表格，每类 3-6 行）
- constraint_examples.md - 约束规则的代码示例（从项目提取 5-8 个核心示例）
- pattern_examples.md - 设计模式的代码示例（从项目提取 5-8 个核心示例）
- design_patterns.md - 设计模式概览（表格形式，模式名+适用场景+参考实现）

格式要求：
- 纯 markdown，内容从项目真实代码提取，不可杜撰
- 禁止 Emoji 和特殊符号
- hard_rules.md + common_pitfalls.md 合计不超过 1500 字
- constraint_examples.md + pattern_examples.md 合计不超过 2500 字

== 第2步：生成 ==

分析完成后，执行：
  python {PROJECT_ROOT}/.castflow/bootstrap.py --skill architect

完成后报告：分析了哪些内容，生成了哪些文件。
