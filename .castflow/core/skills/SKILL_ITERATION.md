---
name: skill-iteration
description: >
  CastFlow four-file skill format. Use only when creating or restructuring
  a skill, or when skill-creator asks for the format. NOT for implementing
  features.
---

# SKILL_ITERATION.md

Skill 文件长什么样。只在 **T4-MAINTAIN**（创建或改 skill 自身结构）加载。怎么调用 skill 去写代码，见 `GLOBAL_SKILL_MEMORY.md` 和项目 `CLAUDE.md`，不在这里。

写入 `.castflow-runtime/skills/<name>/`。不要写适配器镜像。`python .castflow/manager.py sync` 只投影到 `.claude/skills` 和 `.agents/skills`；不要创建 `.grok/skills` 或 `.cursor/skills`（那两棵是兼容残留，sync 会清掉以免重复扫描）。

模块 `programmer-*-skill` 只按本文件写，不要套域 README 或 `*.template.md`（那些会把 skill 写成空架子）。architect / debug / profiler 若仍有冷启动模板，只取 YAML 召回句，正文仍按本文件。四角色文件里只要同时出现 `{{` 和 `}}`，validate 就当残留占位符 fail（规则是朴素子串，不是 token 形状）。示例代码若源文件含这对括号，改写成不触发的写法。

编排文档只传 skill 名、范围、路径，不要抄本文件。

本文件约束 **catalog / 模块 skill 的四角色文件**。Agent、本文件、自由形态 skill 的评测附件各有自己的形状。

机器检查：`python .castflow/manager.py validate`。缺四角色文件的目录 skip。description 形状错误、同一文件里同时有 `{{` 和 `}}`、emoji、多余 `.md` 是 **error**。体积超上限是 **warning**，不是再开文件的许可。

---

## 标准形状

四个角色文件必须有。默认只写这四份。任何额外 `.md`（含 `references/` 子目录）都会 validate fail。

| 文件 | 写什么 | 不要写 |
|------|--------|--------|
| `SKILL.md` | 我是谁、何时用、让位给谁、去哪读 | 用法教程、规则全文、迭代日志 |
| `EXAMPLES.md` | 调用时几乎每次照着抄的热路径 | 规范定义、模块全集、第二份案例库 |
| `SKILL_MEMORY.md` | 不可协商的约束和陷阱 | 日期、版本、过程记录、代码 fence |
| `ITERATION_GUIDE.md` | **本** skill 何时改哪个文件 | 本文件的职责表/禁区复读、检查记录 |

附件只在链路真用得上时才加，且必须是非 markdown：`scripts/`（确定性步骤）和该 skill 会读的 schema / config / json / 查找表。每个附件在四角色文件之一写明何时读、何时跑。没有指针 = 无用文件。

不要生成 ANALYSIS / TEMP / TODO / SUMMARY，不要为躲体积另开 markdown。

---

## SKILL.md

宿主匹配后**整份进上下文**，写短。长文说明职责已经混了。

**YAML**：仅 `name` + `description`。不要 `when-to-use` 或其它宿主不读的键，也不要往另外三个角色文件加 frontmatter。

`description` 是 always-on 召回句，不是说明书。公式：一句做什么 + `Use when` / `当用户` 具体意图 + **一句** `NOT` 到最容易误撞的 sibling。长度按空白折叠后的字符数算（与 `validate.py` `description_shape_errors` 的 `compact` 相同）。超上限是 error。漏召回好过误召回。

不要：同义词/口语清单、执行步骤、sibling 目录抄写、「即使没点名也要用」。

- 目录名匹配 `programmer-*-skill`：`Change <显示名> (<id>) in this repo. Use when the user names <显示名> or <id>. NOT other programmer-*-skill.` 禁止扩同义词、类/路径清单、额外让位目标。`len(compact) <= 280`。
- 其它 skill：口语何时用 + 一句 `NOT`。`len(compact) <= 240`。

两种都禁止关键词堆砌。禁止 pushy 扩词（命中即 error）：`even if they` / `even if the user`、`whenever the user mentions`、`make sure to use this skill whenever`、`即使没` / `即使不` / `即使用户没`。正文可以多写让位；description 里 `NOT` 这个词最多出现一次。

正文顺序：一句定位 -> Yield -> 有几条职责写几条 -> 导航到另外三文件。有附件再加一行何时读/跑。模块 skill 可以再写本模块真实类型和邻模块，仍然不是教程。

短公式或流程图可以用一个 fence。可粘贴的用法放到 EXAMPLES。

---

## EXAMPLES.md

只留最热、最直接、会改生成行为的真实用法，大约 3-8 条。宁可 3 条有人用，不要 15 条没人读。超体积时删或合并**本文件**。

每条至少有：一句话场景、从仓库复制的代码、能 grep 到的路径或符号。import/using 给到能看懂调用即可，不要编 API。推荐结构：

```markdown
## 示例N：简明标题

场景
[什么时候照这个抄]

代码
[从项目复制的片段]

项目参考
[真实路径或符号]
```

陷阱只写真会踩的。

---

## SKILL_MEMORY.md

硬性规则 + 常见陷阱。有几条写几条，不要凑数。origin-evolve 读写的就是这个文件。本文件禁止代码 fence。

推荐条目：

```markdown
### 规则N：名称

Anchors: [class:Building/BuildingManager, method:Building/BuildingFunc:OnUpgrade]
Related: 规则X、陷阱Y

定义
[禁止或要求什么]

检查清单
- [ ] 能当场核对的项
```

```markdown
### 陷阱N：名称

Anchors: [pattern:EventArgs.Create]
Related: 规则X

现象
[症状]

防护
[怎么避免]
```

一条一个约束。检查清单只在需要逐步核对时写。

**Anchors**：钉住的代码符号。扩展格式 `[kind:path-hint:symbol]`，kind 为 `class` / `method` / `field` / `api` / `pattern`（无前缀视为 `class`）。旧格式 `[BuildingManager, OnUpgrade]` 仍有效，新写入优先扩展格式。origin-evolve 写入必须同时带 `Anchors:` 和 `Related:`。T4 只有在规则完全没有可 grep 符号时才可以省 Anchors；绑代码或还要给 evolve 接着 Merge 的条目，必须带扩展 Anchors 和 Related（空 Anchors 的 Jaccard 恒为 0，evolve 会当成新条目重复 Append）。

**Related**：与本条相关的规则/陷阱编号。Merge / Retire 时连带审查。

**[RETIRED]**：写在标题文字前面，不删正文。加载时跳过；去掉标记即可恢复。

```markdown
### [RETIRED] 规则N：名称
```

**容量操作**（写入要用户确认）：

| 操作 | T4 手动改 | origin-evolve 写入 |
|------|-----------|-------------------|
| Append | 与已有条目无语义重叠 | 无已有条目 Jaccard >= 0.5 |
| Merge | 语义重叠或同一代码区域；给用户看 diff | Jaccard >= 0.5（`python .castflow/manager.py homology`）。本文件不另造阈值 |
| Retire | grep 证明 Anchors 符号已不存在 | 同上 |

接近体积上限时先 Merge / Retire 再 Append。禁止另开规则文件。本文件的体积只认下面 `validate` 单位。origin-evolve 自己的词容量以那份 skill 为准，不要在这里换算成第二套数字。

---

## ITERATION_GUIDE.md

只写本 skill 特有的演进触发：什么变化改哪个文件、怎么确认改对了。不要复读本文件。不要把 SKILL.md 的职责再抄一遍当“定位”。质量指标只在有独特验收口径时写。

---

## 格式

- 不要 emoji，不要装饰性 Unicode（色块、星号、勾叉、Unicode 箭头）。ASCII `->`、标准 Markdown、`- [ ]`、`[RETIRED]` 可以。
- `SKILL_MEMORY.md` / `ITERATION_GUIDE.md` 不要日期、`Updated`、`V2.0`、签名。
- 引用的路径、类、方法必须在本次侦察范围内 Read / Grep 过。没打开源文件就不要写签名。

---

## 体积

目的是渐进披露：SKILL.md 始终在场，其余按需打开。不要凑字数，也不要拆文件躲检查。

单位与 `validate.py` `_count_size_units` 相同：去空白、不计代码 fence 的字符。超了给 warning。

| 文件 | 怎么算够 | 警告上限 |
|------|----------|----------|
| SKILL.md | 一屏简报 | 4000 |
| EXAMPLES.md | 3-8 条热路径；代码可以长 | 14000 |
| SKILL_MEMORY.md | 每条一个约束 | 9000 |
| ITERATION_GUIDE.md | 只留本 skill 触发器 | 4500 |

导航表：SKILL.md 指向另外三文件（有附件加一行）。EXAMPLES / MEMORY / GUIDE 条目多到需要跳转时再加目录；短文件不要为规范加空表。

---

## 改哪个文件

| 情景 | SKILL.md | EXAMPLES.md | SKILL_MEMORY.md | ITERATION_GUIDE.md |
|------|----------|-------------|-----------------|-------------------|
| 新的热路径用法 | | 是 | 可能 | |
| 新约束或陷阱 | | | 是 | |
| 职责或触发变化 | 是 | 可能 | 可能 | 是 |
| 框架 API 变了 | | 是 | 可能 | |
| 用户纠正用法 | | 是 | 可能 | |

写完跑 `python .castflow/manager.py validate`，再 `python .castflow/manager.py sync`。
