# Bootstrap-Skill 示例库

本文件展示初始化的**流程格式和输出结构**，不展示具体项目内容。实际执行时，所有内容由扫描结果和用户确认决定。

---

## 示例 1：全量初始化 - 完整对话流程

### Phase 0：语言选择（触发后第一条消息）

用户输入 `bootstrap castflow` 后，AI **不立即开始扫描**，第一条消息是：

```
AI: 生成的 Skill / CLAUDE.md / 规则描述将使用哪种语言撰写？
    （代码本身的标识符不会被翻译）

      1. 中文 (zh) [默认]
      2. English (en)
      3. 日本語 (ja)
      4. 한국어 (ko)
      5. 其他（请输入 ISO 639-1 代码或语言名称）

    请回复编号或语言名称。直接回车 = 中文。

用户: 用英文

AI: 已选 English (en)，开始扫描项目...
```

> 归一化要点：用户输入"用英文" -> manifest.language = `en` -> Phase 3 注入
> sub-agent prompt 的 `{LANGUAGE}` 占位符时映射为字面量 `English`。

### Phase 1：扫描结果展示

```
扫描结果:
  技术栈: C# + Unity
  框架特征: ProjectSettings/, Assembly-*.asmdef
  命名规范（检测到）:
    - 私有字段: _camelCase
    - 私有方法: PascalCase
    - 公共成员: PascalCase
  项目规模: 约 500 个 .cs 文件
```

### Phase 2：用户确认（按固定顺序）

#### 2.1 逐 Skill 确认

```
AI: 以下是可以为项目生成的 Skill，逐个确认：

1. architect-skill（推荐）
   用途：记录项目的架构约束规则和设计模式参考。
   扫描范围：Manager/Service 模式、事件系统、分层架构、依赖注入等。
   所有其他 Skill 和 Agent 都会参考它。
   -> 是否生成？

用户: 是

2. debug-skill（可选）
   用途：提供边界条件检查清单和防御性编程指导。
   扫描范围：MonoBehaviour 生命周期、资源释放、事件取消订阅等。
   -> 是否生成？

用户: 是

3. profiler-skill（可选）
   用途：提供性能红线和优化反模式参考。
   扫描范围：Update 热路径、GC 分配、对象池使用等。
   -> 是否生成？

用户: 跳过
```

#### 2.2 补充信息收集

```
命名规范确认：
  检测到 _camelCase 私有字段模式，是否采用？
用户: 是

额外的框架规则？
用户: Logic 层不引用 UnityEngine
```

### Phase 2 结束 - 公共文件处理

```
生成 manifest.json
生成 content/claude/ (命名规范、框架规则、项目规则)

处理公共文件：
  python .castflow/bootstrap.py --skill core       # 核心文件复制
  python .castflow/bootstrap.py --skill claude      # CLAUDE.md 生成
  python .castflow/bootstrap.py --skill templates   # 模板复制
```

### Phase 3 并行 Agent 闭环生成

主 agent 在一条消息中同时发射所有 agent，每个 agent 独立完成分析+生成：

```
主agent: 同时启动 2 个独立 agent（各自闭环）...

  [Task 1: architect-agent]
    prompt: "你是架构分析专家...全程闭环...技术栈: C# + Unity..."
    agent 内部：分析项目 -> 写 content -> 执行 bootstrap.py --skill architect
    最终产出：.claude/skills/architect-skill/ (4 个文件)

  [Task 2: debug-agent]
    prompt: "你是边界条件分析专家...全程闭环...技术栈: C# + Unity..."
    agent 内部：分析项目 -> 写 content -> 执行 bootstrap.py --skill debug
    最终产出：.claude/skills/debug-skill/ (4 个文件)

等待所有 agent 完成...

  architect-agent 完成 -> .claude/skills/architect-skill/ 已就绪
  debug-agent 完成     -> .claude/skills/debug-skill/ 已就绪
```

### Phase 4 验证与清理

```
python .castflow/bootstrap.py --validate
  [PASS] architect-skill
  [PASS] debug-skill

清理 bootstrap-output/

初始化完成。
模块 Skill 可按需创建：告诉 AI "为xxx系统生成 skill"。
```

---

## 示例 2：manifest.json 格式

Phase 2 确认后生成的 manifest 文件。

```json
{
  "version": 1,
  "tech_stack": "unity",
  "language": "en",
  "profile": "standard",
  "merge_mode": "full",
  "modules": [],
  "optional_skills": { "debug": true, "profiler": false },
  "naming_conventions": "_camelCase for private fields"
}
```

> 上例中 `language: "en"` 对应示例 1 用户选择"用英文"。Phase 3 启动每个
> sub-agent 时，主 agent 会把 `en` 映射为 `English` 注入 `{LANGUAGE}` 占位符。

字段说明：

| 字段 | 必需 | 说明 |
|------|------|------|
| version | 是 | 固定为 1 |
| tech_stack | 否 | 技术栈标识，用于条件段处理 |
| language | 否 | 生成文件的语言，默认 "zh"（中文）。支持任意语言标识如 "en"、"ja"、"ko" 等 |
| profile | 否 | lite/standard/full，默认 standard |
| merge_mode | 否 | full(备份覆盖)/incremental(跳过已有)，默认 full |
| modules | 是 | 模块列表，初始化时为空数组；创建模块 skill 时填入 |
| optional_skills | 否 | 是否生成 debug/profiler skill |
| naming_conventions | 否 | 命名规范短文本，content 文件优先 |

---

## 示例 3：content 目录结构

每个 agent 在闭环流程中先写 content 文件，再调用 `bootstrap.py --skill` 将 content 填入模板生成最终 skill。content 是中间产物，每个文件对应模板中的一个 `{{PLACEHOLDER}}`。

```
bootstrap-output/
  manifest.json
  content/
    claude/
      naming_conventions.md         -> CLAUDE.template 的 {{NAMING_CONVENTIONS}}
      framework_rules.md            -> {{FRAMEWORK_RULES}}
      project_rules.md              -> {{PROJECT_RULES}}
    architect/                      (architect subagent 生成, 6 个文件)
      hard_rules.md                 -> {{HARD_RULES}} (纯文字，禁止代码块)
      common_pitfalls.md            -> {{COMMON_PITFALLS}} (纯文字，禁止代码块)
      constraint_rules_summary.md   -> {{CONSTRAINT_RULES_SUMMARY}}
      constraint_examples.md        -> {{CONSTRAINT_EXAMPLES}}
      pattern_examples.md           -> {{PATTERN_EXAMPLES}}
      design_patterns.md            -> {{DESIGN_PATTERNS}}
    debug/                          (debug subagent 生成)
      focus_areas.md                -> {{FOCUS_AREAS}}
      project_checks.md             -> {{PROJECT_SPECIFIC_CHECKS}}
      examples.md                   -> {{DEBUG_EXAMPLES}}
      extra_rules.md                -> {{EXTRA_RULES}}
      extra_pitfalls.md             -> {{EXTRA_PITFALLS}}
    profiler/                       (profiler subagent 生成)
      performance_budgets.md        -> {{PERFORMANCE_BUDGETS}}
      project_optimizations.md      -> {{PROJECT_SPECIFIC_OPTIMIZATIONS}}
      examples.md                   -> {{PROFILER_EXAMPLES}}
      extra_rules.md                -> {{EXTRA_RULES}}
      extra_pitfalls.md             -> {{EXTRA_PITFALLS}}
```

---

## 示例 4：模块 Skill 创建（初始化后使用）

用户在初始化完成后，为项目模块创建 Skill 的完整流程。

### 触发

```
用户: "为建筑系统生成 skill"
```

### 确认

```
AI: 确认模块信息：
  模块 ID: building
  显示名: 建筑
  主要代码目录: Assets/Scripts/GameLogic/Logic/Building/

用户: 确认
```

### 独立 Agent 闭环生成 Skill

```
主agent: 生成 manifest，启动独立 agent 闭环处理...

  [Task: module-building-agent]
    prompt: "你是模块分析专家...全程闭环...模块ID: building..."
    agent 内部：
      1. 分析项目 -> 写 content/modules/building/ (6 个文件)
      2. 执行 bootstrap.py --skill building

等待 agent 完成...

  module-building-agent 完成
    -> .claude/skills/programmer-building-skill/ 已就绪
```

### 完成

```
AI: 建筑模块 Skill 已生成：.claude/skills/programmer-building-skill/
  日常开发直接使用 skill 即可。
  后续在 code-pipeline 中如需专属子代理，pipeline 会按需提议创建。
```

### 模块 content 文件结构

```
bootstrap-output/content/modules/{module_id}/
  architecture.md             -> {{MODULE_ARCHITECTURE}}
  core_classes.md             -> {{CORE_CLASSES}}
  relationships.md            -> {{MODULE_RELATIONSHIPS}}
  examples.md                 -> {{MODULE_EXAMPLES}}
  hard_rules.md               -> {{MODULE_HARD_RULES}}
  pitfalls.md                 -> {{MODULE_PITFALLS}}
```

---

## 示例 5：核心更新

**场景**：castflow submodule 有新版本

### 触发

```
用户: "bootstrap 更新核心"
```

### 执行

```
1. 对比 .castflow/core/ 与 .claude/skills/ 的核心文件
2. 更新:
   - SKILL_ITERATION.md
   - GLOBAL_SKILL_MEMORY.md
   - code-pipeline-skill/
   - skill-creator/
3. 保留（不覆盖）:
   - CLAUDE.md (按交互式合并策略处理)
   - architect-skill/
   - programmer-*-skill/
   - debug-skill/
   - profiler-skill/
   - .claude/agents/
4. 更新 .claude/templates/ 中的模板文件
```

---
