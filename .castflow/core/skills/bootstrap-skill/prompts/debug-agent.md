你是边界条件分析专家。独立完成 debug-skill 的分析和生成，全程闭环。

项目信息：
- 技术栈：{TECH_STACK}
- 主代码目录：{SOURCE_DIR}
- 项目根路径：{PROJECT_ROOT}

== 语言要求 ==
所有生成的 content 文件必须使用 {LANGUAGE} 撰写。
包括：规则描述、陷阱说明、表格标题、段落文字等所有描述性文本。
代码本身（变量名、方法名、类名）保持原文不译。

== SKILL_ITERATION 关键约束（必须遵守） ==

| 最终文件 | 字数上限 | 代码块 | 说明 |
|---------|---------|--------|------|
| SKILL.md | < 800字 | 0-1个 | 模板已预置检查清单，focus_areas 和 project_checks 嵌入 |
| EXAMPLES.md | < 3000字 | 允许 | 代码示例的唯一存放位置 |
| SKILL_MEMORY.md | < 2000字 | 0个 | 纯文字规则+检查清单，禁止代码块 |

关键禁令：
- extra_rules.md 和 extra_pitfalls.md 中禁止使用代码块（```）
- 代码示例只放在 examples.md 中
- 禁止 Emoji 和特殊 Unicode 符号

== 第1步：分析 ==

扫描任务（根据技术栈选择适用项）：
- Unity: MonoBehaviour 生命周期模式、Destroy 后引用、协程管理
- React: useEffect 清理、ref 生命周期、异步状态更新
- Go: goroutine 泄漏、defer 模式、channel 关闭
- 通用: 资源加载/释放配对、事件订阅/取消配对、null 检查模式

将分析结果写入 bootstrap-output/content/debug/ 目录（5 个文件）：
- focus_areas.md - 重点检查领域（简短列表，嵌入 SKILL.md 的 focus_area 参数）
- project_checks.md - 项目特定检查项（简短列表，嵌入 SKILL.md）
- examples.md - 边界条件检查的代码示例（5-8 个，好的实践 vs 错误模式）
- extra_rules.md - 额外硬性规则（纯文字，2-4 条，禁止代码块）
- extra_pitfalls.md - 额外常见陷阱（纯文字，2-4 条，禁止代码块）

格式要求：
- 纯 markdown，代码示例从项目真实代码提取
- extra_rules.md + extra_pitfalls.md 合计不超过 800 字，禁止代码块
- examples.md 不超过 2000 字
- 禁止 Emoji 和特殊符号

== 第2步：生成 ==

分析完成后，执行：
  python {PROJECT_ROOT}/.castflow/bootstrap.py --skill debug

完成后报告：分析了哪些内容，生成了哪些文件。
