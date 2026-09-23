# CastFlow 2.0

[English](./README.md) | **中文**

> **让 AI 助手从第一天就深度理解你的项目，并且越用越懂。**

CastFlow 是一套可移植、可演进的 **AI 协同开发操作系统**，面向 **Claude Code / Grok TUI / Codex CLI / Cursor**。

**2.0 的改造原因：模型已经更强、也更敏感。** 1.x 用密集规则、9 步编排、报备清单和打分仪式去「管住」早期模型；放到今天，这些约束占用上下文、压扁判断力，反而限制 AI 的能力。2.0 把框架收成少而硬的护栏，把发挥空间还给模型。

落在产品上：入口从「跟 AI 聊完 Phase 0–6」换成「双击向导」；知识真源从「每个宿主各写一份」换成「一份 runtime，投影发现路径」；日常工作从「9 步 pipeline」换成「按模块 skill 直接写」；进化原料从「给编辑打分」换成「你本来就会写的 memory 快照」。

一次装架，终身进化。新旧对照与完整变更见 [CHANGELOG.zh-CN.md](./CHANGELOG.zh-CN.md)（[English](./CHANGELOG.md)）。

---

## 目录

- [为什么做 2.0](#为什么做-20)
- [2.0 相对 1.x 的核心提升](#20-相对-1x-的核心提升)
- [解决什么问题](#解决什么问题)
- [核心设计](#核心设计)
- [冷启动模块扫描](#冷启动模块扫描)
- [Jev 分类](#jev-分类)
- [项目结构总览](#项目结构总览)
- [端到端：从装架到自主进化](#端到端从装架到自主进化)
- [文件清单](#文件清单)
- [渐进式信息披露（T1–T4）](#渐进式信息披露t1-t4)
- [自我进化](#自我进化)
- [命令参考](#命令参考)
- [升级与回滚](#升级与回滚)
- [测试套件](#测试套件)

---

## 为什么做 2.0

CastFlow 1.x 诞生时，模型更容易幻觉、更容易越权、也更需要逐步手把手。当时合理的对策是：**把流程写死、把检查写满、把经验打成分数。**

模型变强之后，同一套对策开始反向生效：

- 规则越多，always-on 上下文越吵；敏感模型会把「建议」当成不可违反的仪式，该判断的时候先报备、该动手的时候先打卡。
- 9 步 pipeline、并行子代理、域模板套话，是在替模型做它已经会做的编排，同时挤掉它本该用来读项目代码的注意力。
- 五维评分把「改了多少行」当成「学到了什么」——模型对反馈已经足够敏感，真正值钱的是用户明确说过的纠正，不是编辑密度。

2.0 因此做减法：只保留项目特有、机器可校验、人必须审批的硬约束；把发现模块、写补丁、组织长任务交回给更强的模型。框架负责 **真源、投影、时点、进化账本**，不再扮演第二套操作系统去微操每一步。

---

## 2.0 相对 1.x 的核心提升

| 维度 | 1.x | 2.0 |
|------|-----|-----|
| 冷启动 | 对话里问语言、代跑 seed/scan、Phase 0–6 | GUI 向导：配置、可选 Jev、拷文件；`coldstart` 扫包；可 `unseed` 重来 |
| 知识真源 | `.claude/skills` 等适配器树各写一份 | `.castflow-runtime/skills/` 一份真源；只投影到 `.claude/skills` 与 `.agents/skills` |
| 模块发现 | Python 按目录/文件数切 | `coldstart` 把包依赖切成一棵合并树。结构定不了的，可选 Jev 分类。框架树排除 |
| 写 skill | 并行子代理，上下文挤薄 | 一次一个：落队列 → 清上下文 → 写 → validate/sync → 标 done |
| 日常改代码 | `code-pipeline-skill` 9 步编排 | 直接调用 `programmer-<模块>-skill` |
| 进化原料 | 五维评分 + 编辑 buffer + IDP | schema:4 **memory 快照账本**；纯代码会话不记条目 |
| 规则合并 | 模型自己算 Jaccard | `manager.py homology` 连通分量，一批算完 |
| 运行时协议 | 报备清单、Grep 次数、执行模式命名 | 三件事：API 先证后用、约束覆盖抄来的代码、范围不够就先问 |
| 框架位置 | 必须当子目录塞进工程 | 文件夹选择器；CastFlow 可在另一盘；hook 自动改绝对路径 |

**2.0 刻意删掉的东西**（不是没做完，是规则过密、会限制更强模型）：`code-pipeline-skill` 及三个 pipeline agent、旧的 `scan.py` 账本（不是 `coldstart`）、五维评分、programmer 域模板、`AUTHORING_GUIDE`、`skill-forge`、`CLAUDE.template.md`、`placeholders.py`、向 `.grok/skills` / `.cursor/skills` 再写一份。

---

## 解决什么问题

AI 助手进入大型项目常见的四种失控：

| 问题 | 症状 | CastFlow 的治法 |
|------|------|----------------|
| 架构遗忘 | 风格不一致、越过分层 | `architect-skill` 从真实代码提取规则；T1 强制加载运行时协议 |
| API 幻觉 | 调用不存在的方法、签名乱编 | 协议 1：EXAMPLES / 打开过的定义 / 用户指针，三者任一即可；未验证处标 TODO，不猜签名 |
| 知识碎片化 | 规则散落口头约定与 PR 评论 | 四件套 Skill（SKILL / EXAMPLES / SKILL_MEMORY / ITERATION_GUIDE），文件即知识 |
| 经验不积累 | 上次犯过的错下次照犯 | 跨工具共用 `.castflow-runtime/memory` + `traces/`；`origin evolve` 蒸馏为规则，**人审批后**写入真源再 sync |

它把项目知识变成 **可执行、可验证、可迭代** 的仓库资产。

---

## 核心设计

### 1. 冷启动：拷文件；扫描生成是可选项

```bash
CastFlow\castflow.bat                 # Windows：打印说明后打开向导（可先选工程目录）
./castflow.sh                         # macOS / Linux：同上（Finder 可双击 castflow.command）
python .castflow/manager.py launch    # 同上（任意 OS；在 CastFlow 仓里跑）
python .castflow/manager.py setup     # 无界面：config + seed + sync
python .castflow/manager.py unseed    # 卸下运行时和投影，再走一遍向导
python .castflow-runtime/manager.py update-framework   # 已装架的目标项目
```

CastFlow **不必**放在工程目录里。向导用系统文件夹对话框选项目根；跨盘时 hook 写入绝对路径。

- 未勾选「扫描模块并生成 skill」：只拷框架 skill 和核心文件，**不需要 AI 提示词**
- 勾选后：可改提示词。留空则用内置 `/goal`，读取 `.castflow-runtime/skills/MODULE_MARK_SYSTEM_PROMPT.md`
- 包扫描和 Jev 标记走 `manager.py coldstart`，见下文。**不**扫 `CastFlow/`、`.castflow/`、`.castflow-runtime/` 或适配器树
- Jev 是单独的勾选，默认关闭。勾选后才把 `.castflow/jev/` 拷进 runtime。密钥不在这次拷贝里
- 工厂仓（CastFlow 自己）拒绝 `seed` / `sync` / `setup`，并清掉误留下的 runtime

Skill 正文只有一份真源：`.castflow-runtime/skills/`。`sync` 用 symlink / junction / copy 投影到 `.claude/skills` 与 `.agents/skills`。Grok / Cursor 扫描这两处，**不再**各写一份 `.grok/skills` / `.cursor/skills`（残留会被清掉，避免重复召回）。本机停用的 skill 不再投影（`.castflow-runtime/skills-disabled.json`，gitignore；未列入则默认激活）。打开 manager 会刷新投影。项目根 `.gitignore` 由 sync 托管一块稳定规则，忽略整棵投影目录；已跟踪的投影会 `git rm --cached`，不删工作树。runtime 的 skill 正文仍可提交。

### 冷启动模块扫描

`manager.py coldstart` 把产品脚本走一遍，打印一份可勾选的切面。不加 `--select` 时什么都不写。

```bash
python .castflow/manager.py coldstart --root PATH [--target N]
python .castflow/manager.py coldstart --root PATH --select ID --queue
python .castflow/manager.py coldstart --root PATH --select ID --skill
```

已装架的项目用 `python .castflow-runtime/manager.py coldstart --root PATH`。

- 只看产品脚本。`CastFlow/`、`.castflow/`、`.castflow-runtime/`、适配器树、`Library`、`node_modules` 一类目录会跳过。
- 原子是仓库里已经有的包：功能目录、`tools/<Name>`、asmdef，或 vendor 目录。边是类型名引用。`using` 行不是边。
- 这些原子自底向上并成一棵树。`--target`（默认 16）是同一棵树的一层，不是再聚类一次。大于 8 时保留 `Modules/<Feature>` 节点。
- 角色是这层切面上的规则，不是另一次聚类：`feature`、`engine`、`tool`、`adapter`、`bootstrap`。
- 建议做成 skill 的，是有入口的 feature，外加最多两个不是大杂烩的 engine 包。tool、adapter、bootstrap、机制包和混合包仍会列出，但默认不勾。
- 选中的一个节点就是一个 skill。嵌套包是这个节点里的证据，不是额外的 skill。
- 这不是已删除的 `scan.py`。不写 `STATE.yaml`、`INVENTORY.md`、`GRAPH.md`，也不写知识图谱。
- 可选覆盖写在 `.castflow-runtime/module-roles.txt`，一行一个：`atom-id-or-path-prefix role`。

`--queue` 只把选中的短卡写到 `.castflow-runtime/_skill-gen-queue/`。`--skill` 必须且只能有一个 `--select`，按真实调用点写出对应的 `programmer-<id>-skill`，然后删掉队列。

### Jev 分类

可选，默认关闭。向导勾选后才把 `.castflow/jev/` 拷到 `.castflow-runtime/jev/`。不勾选就不安装。

密钥是 `.castflow-runtime/secrets.env` 里的 `TYPESAFE_API_KEY`。该文件被 git 忽略，是唯一的密钥存放处；以后的 key 也是这个文件里的更多行。密钥不进 `config.json`。

`coldstart` 给每个包原子打标记。标记打在图里的包上，不是打在合并后的 skill 节点上：

- 结构已经清楚的，绝不调用 Jev。先验把共享叶子（`common`、`shared`、`util`、`utils`）留成 tool；叶子名对上单个 feature 的，挂到那个 feature；adapter 和 feature 包保持原样；fan-in 至少 8、fan-out 至多 3、且没有入口的 engine 则拆开。
- 先验定不了的卡片，只有模块已安装且密钥可用时，才交给 TypeSafe Jev（`system_one`）。立场是 `feature`、`shared_method`、`independent_system`、`framework_mechanism`、`other`。标记照抄官方选择，不编造概率。
- 没有模块或没有密钥时，这些卡片是 `review`，命令会打印 Jev 未配置。标记停在结构先验上。

一条标记的动作是 `keep`、`attach`、`split` 或 `review`。

### 2. 渐进式信息披露：时点驱动加载

Skill 不会每次全量入上下文。按 **T1-PREPARE / T2-EXECUTE / T3-FEEDBACK / T4-MAINTAIN** 分层：写代码前读运行时协议全文，写的时候不再重读。权威源是项目根 `CLAUDE.md` / `AGENTS.md`（由 `ROOT_RULES.template.md` 生成）。

### 3. 按模块 skill 工作

跨模块需求直接调用已生成的 `programmer-<id>-skill`。需要架构边界、排障或热路径时再点名 `architect-skill` / `debug-skill` / `profiler-skill`（向导不再勾选这三类）。`code-pipeline-skill` 已退役。

生成纪律：勾选扫描后把短卡落到 `.castflow-runtime/_skill-gen-queue/`，一次只写一个 programmer skill，validate/sync 成功后标 `done` 再清上下文。并行生成会把上下文挤薄。增量同样走 loop-engine，或对 AI 说 `castflow generate skills`（skill-creator 一次写一个然后停）。

### 4. 自我进化：零额外动作采集 + 人在回路

经验原料的**唯一**捕获路径是 **memory 快照**（schema:4）。返工、被纠正、被下硬约束时写入 `.castflow-runtime/memory/`（YAML `name` + `type: feedback|project|reference`）。Hook 自动全文快照进 `trace.md`。评分、编辑 buffer、IDP 已全部退役。

- `user` 类型（个人画像）被过滤，不进 git
- 纯代码会话不产生 trace 条目——账本只记「学到了什么」
- 蒸馏推迟到 `origin evolve`：读 `<!-- MEMORY -->`、homology 聚类、生成 Append/Merge/Retire，**审批后**写入真源再 sync

进化插件可在向导或 `manager.py evolve on|off` 关掉（卸 hook 与 origin-evolve 投影，不删已有 traces）。

---

## 项目结构总览

```
CastFlow/
├── README.md                              # 英文（仓库默认）
├── README.zh-CN.md                        # 中文（本文件）
├── CHANGELOG.md                           # 英文变更记录（仓库默认）
├── CHANGELOG.zh-CN.md                     # 中文变更记录
├── LICENSE                                # MIT
├── castflow.bat                           # Windows 冷启动：文件夹选择器 + GUI
├── castflow.sh / castflow.command         # macOS / Linux 冷启动（.command = Finder 双击）
│
├── .castflow/                             # 框架源码（装架后休眠，随 git pull 更新）
│   ├── manager.py                         # 【主入口】launch / setup / seed / sync / skills …
│   ├── manager/                           # 冷启动、投影、队列、进化开关、stdlib HTTP 控制台
│   │   ├── cli.py / setup.py / coldstart.py / jevmark.py / envfile.py
│   │   ├── adapters.py / skills.py / catalog.py
│   │   ├── evolution.py / queue.py / config.py / paths.py / pick_dir.py
│   │   ├── bundle.py                      # seed：manager/installer → runtime，并写项目 launchers
│   │   └── ui/server.py + static/index.html
│   ├── jev/                               # 可选；只有向导勾选才拷进 runtime
│   ├── installer/                         # validate.py；随 seed 拷进 runtime
│   └── core/                              # 被 seed 同步进 runtime 的核心
│       ├── skills/
│       │   ├── GLOBAL_SKILL_MEMORY.md     # T1 运行时三协议
│       │   ├── SKILL_ITERATION.md         # 四角色文件标准；validate 管形状
│       │   ├── MODULE_MARK_SYSTEM_PROMPT.md
│       │   ├── origin-evolve-skill/       # 读 trace → Append/Merge/Retire 提议
│       │   ├── skill-creator/             # catalog 四件套（评测环非冷启动）
│       │   └── goal-loop-creator/         # 【核心】长任务转换系统：需求 → loop-engine 长任务包
│       ├── protocols/validated-protocol.md
│       ├── rules/
│       │   ├── evolve-reminder.md(.mdc)   # pending 时提醒 origin evolve
│       │   └── module-catalog.md          # 什么算模块；AI 只审表不扫树
│       ├── hooks/
│       │   ├── trace-collector.py         # 写 memory 时全文快照
│       │   ├── trace-flush.py             # 会话结束落账 + 龄期 compaction
│       │   ├── _homology.py               # Jaccard 连通分量（一批算完）
│       │   └── _castflow_paths.py         # hook 定位 runtime
│       ├── templates/root/ROOT_RULES.template.md
│       └── traces/                        # schema:4 契约 + limits / hooks.config
│
└── test/                                  # 框架回归（不分发）
    ├── run_all.py
    ├── manager/                           # seed/sync、向导、coldstart、Jev 标记
    ├── hooks/                             # 快照采集、homology、compaction、365 天
    ├── bootstrap/                         # validate.py 四件套形状（test_validate.py）
    ├── skills/                            # GLOBAL_SKILL_MEMORY 契约
    └── origin-evolve/                     # 规范确定性暴力验证
```

### 装架后用户项目

```
项目根目录/
├── CLAUDE.md / AGENTS.md                  # 框架段（ROOT_RULES）+ 项目段
├── castflow.bat / castflow.sh / .command  # 打开 runtime 管理器（seed 写入，不是框架仓那份）
├── .castflow-runtime/                     # 项目里唯一的 CastFlow 目录
│   ├── manager.py / manager/ / installer/ # 控制台、sync、validate（bundle 从框架拷入）
│   ├── hooks/                             # trace-collector / trace-flush / _homology
│   ├── skills/                            # 【真源】全量 skill 清单（可提交）
│   ├── memory/                            # 跨工具 feedback / project / reference
│   ├── traces/                            # trace.md 账本 + config
│   ├── protocols/ / rules/                # 含 module-catalog.md
│   ├── templates/ROOT_RULES.template.md   # 扁平拷贝（源在 core/templates/root/）
│   ├── config.json                        # 适配器、进化开关、jev_enabled（不含密钥）
│   ├── secrets.env                        # gitignore。TYPESAFE_API_KEY 及以后的 key。不进 config.json
│   ├── jev/                               # 仅冷启动勾选 Jev 时存在
│   ├── module-roles.txt                   # 可选：atom-id-or-path-prefix role
│   ├── skills-disabled.json               # 本机停用名单（gitignore，不进仓库）
│   └── _skill-gen-queue/                  # coldstart 选中的短卡（--skill 之后删除）
├── .claude/skills/                        # 发现镜像（gitignore，勿手改）
├── .agents/skills/                        # Codex 发现镜像（gitignore）
├── .claude/settings.json                  # Claude hook（增量合并）
├── .cursor/hooks.json                     # Cursor hook（无 .cursor/skills 树）
├── .grok/hooks/castflow.json              # Grok hook（无 .grok/skills 树）
└── CastFlow/                              # 可选：submodule；也可放在工程外（框架源，不是项目真源）
```

---

## 端到端：从装架到自主进化

### 步骤 1 — 拿到框架

```bash
git submodule add https://github.com/yunzeforbetter/CastFlow.git
```

CastFlow 与 `.claude` 同级最省事，但不是必须。克隆到任意目录再打开启动器，用文件夹对话框指向游戏/应用工程即可。

### 步骤 2 — 冷启动（打开启动器）

```bash
CastFlow\castflow.bat                  # Windows：双击
chmod +x castflow.sh castflow.command  # macOS / Linux：首次
./castflow.sh                          # 终端；Finder 双击 castflow.command
# 或: python3 CastFlow/.castflow/manager.py launch
```

| 步 | 动作 | 结果 |
|----|------|------|
| 1 配置 | 语言、适配器、进化、可选 Jev | 写入 `config.json`。只有勾选才拷 Jev 模块 |
| 2 可选 | 勾选扫描生成，可改提示词 | 留空用内置 `/goal` |
| 3 开启冷启动 | seed + sync | 框架 skill 与核心文件已投影 |
| 4 扫描 | `coldstart --root` | 包切面；装了 Jev 时一并打标记 |
| 5 AI（仅勾选时） | 粘贴提示词 | 按该提示词生成，一次一个 skill |

装架后控制台三页：**框架**（从源更新并同步）/ **Skills**（retire / activate / update / sync）/ **队列**。勾选错了用「回退并重新冷启动」，不必手删文件。

冷启动请打开启动器（Windows 双击 `castflow.bat`，macOS 双击 `castflow.command` 或跑 `./castflow.sh`），不要让 AI 代跑 seed。

### 步骤 3 — 扫描模块

```bash
python .castflow-runtime/manager.py coldstart --root .
python .castflow-runtime/manager.py coldstart --root . --select some-id --queue
python .castflow-runtime/manager.py coldstart --root . --select some-id --skill
```

第一条只打印切面和 Jev 标记，不写文件。`--queue` 只保留你选中的 id。`--skill` 按真实调用点写出一个 programmer skill，然后删掉队列。

向导里若勾了扫描，粘贴它的 `/goal` 是另一条路：AI 一次写一个 programmer skill。不要并行生成。skill 文件的规则在 `SKILL_ITERATION.md`。写入 runtime，再 sync。

日常增量：

```
为 xx 系统生成 skill
```

### 步骤 4 — 日常改功能

```
帮我在 xx 系统里加一个批量升级功能
```

宿主按 description 加载对应 `programmer-*-skill`。多模块分别走各模块 skill。

### 步骤 5 — 自主进化

一周里你被纠正过几次，每次写一条 `feedback` memory。Hook 已快照进 `trace.md`。新会话 `evolve-reminder` 提示：

```
检测到 pending 条目（含 feedback 快照），建议运行: origin evolve
```

用户输入 `origin evolve`：

1. 若有未 flush 快照，先 `manager.py flush`，再加锁
2. 只保留 `pending`；`homology` 把 MEMORY 子块聚成连通分量
3. 合格条件：`feedback` 且 quality=ok，**或**同源条数 ≥ 2
4. 提议 Append / Merge / Retire（写入前 grep 校验 Anchors 仍在代码里）
5. 逐个审批（拒绝记 `EVOLVE_REJECTION`）
6. 写入 `.castflow-runtime/skills/`，原条目换成一行 `<!-- PROCESSED … -->`，再 `sync`

下次会话新规则生效，不再重复犯这一类错。

### 步骤 6 — 框架升级

```bash
cd CastFlow && git pull
python .castflow-runtime/manager.py update-framework
```

只刷新框架 skill 与核心文件，**不覆盖项目 skill**。`CLAUDE.md` 项目段完全保留。

---

## 文件清单

### `.castflow/manager.py` — 产品主入口

| 模块 | 作用 |
|------|------|
| `cli.py` | launch / setup / unseed / seed / sync / skills / retire / activate / update / evolve / queue / handoff / flush / homology / validate / status / update-framework / coldstart / ui |
| `setup.py` | 向导与无界面冷启动；文件夹选择器；仅勾选时拷贝 Jev；工厂仓拒绝 seed |
| `coldstart.py` | 包原子扫描：一棵合并树、按 target 切开、角色规则。没有 `--select` 就不写文件 |
| `jevmark.py` | 加载可选的 `jev.mark`。先走先验；只有定不了的卡片才问官方 Jev |
| `envfile.py` | 读写 `.castflow-runtime/secrets.env`。绝不写进 `config.json` |
| `adapters.py` | runtime ↔ `.claude/skills` + `.agents/skills`；gitignore 托管；清兼容残留 |
| `skills.py` | 清单、本机停用（`skills-disabled.json`）、从源刷新 |
| `bundle.py` | seed 把 `manager.py` / `manager/` / `installer/` 拷进 runtime，并写项目根 `castflow.bat` / `castflow.sh` / `castflow.command` |
| `catalog.py` / `queue.py` | 控制台队列状态，以及可选的 `/goal` 交接 |
| `evolution.py` | 进化开关：卸 hook 与 origin-evolve 投影 |
| `ui/` | stdlib HTTP 控制台（`127.0.0.1`） |
| `.castflow/jev/` | 可选分类器（`mark.py`、`install.py`）。只有向导勾选才拷到 `.castflow-runtime/jev/` |

### `.castflow/installer/` — 随 seed 拷进 runtime（validate）

只剩 `validate.py`。`manager.py validate` 调它。1.x 的 `bootstrap.py` / Phase A / manifest / `.claude/.backups` 已删除。

| 模块 | 作用 |
|------|------|
| `validate.py` | 无 emoji / 无日期 / 无残留 `{{` `}}` / description 形状 / 字数 warning |

### `.castflow/core/` — seed 进 runtime 的内容

| 路径 | 作用 |
|------|------|
| `GLOBAL_SKILL_MEMORY.md` | 三协议。T1 读全文，T2 不重读 |
| `SKILL_ITERATION.md` | 四角色 + Anchors/Related + 附件指针；机器检查走 `manager.py validate` |
| `MODULE_MARK_SYSTEM_PROMPT.md` | 勾选后 `/goal` 执行的扫描→多选→一次一个生成 |
| `origin-evolve-skill/` | 蒸馏 memory 快照；永不自动跑 |
| `skill-creator/` | catalog 四件套；冷启动禁止评测环 |
| `goal-loop-creator/` | **核心 skill / 长任务转换系统**。冷启动自动装入。把需求编译成 AI 可跑的 Goal Loop Package（loop-engine：一次过完命名系统）。不执行 `/goal` |
| `hooks/trace-collector.py` | 主路径 `.castflow-runtime/memory/*.md`；可选 inbound Claude auto-memory |
| `hooks/trace-flush.py` | 有快照才写 trace；`--selftest` |
| `hooks/_homology.py` | slug / skill / Anchors Jaccard≥0.5 → 连通分量 |
| `templates/root/ROOT_RULES.template.md` | 注入 `CLAUDE.md` / `AGENTS.md`；seed 拷到 runtime `templates/` |
| `traces/` | schema:4 契约、`limits.json`、`hooks.config.json` |
| `rules/module-catalog.md` | 可选 `/goal` 路径的模块约定；seed 拷到 `.castflow-runtime/rules/` |
| `hooks/` | seed 拷到 `.castflow-runtime/hooks/`，hook JSON 指向这里 |

没有域 skill 模板。生成 architect/debug/profiler 时 YAML 召回句写在 `SKILL_ITERATION.md`，正文仍按该文件。模块 skill 不要套已删除的 `*.template.md`。

---

## 渐进式信息披露（T1–T4）

命名 `T<序号>-<动词>`，权威源为项目根 `CLAUDE.md`。

| 时点 | 触发 | AI 主动读什么 |
|------|------|--------------|
| **T1-PREPARE** | 写代码前 | `GLOBAL_SKILL_MEMORY.md` 全文 + 目标 `SKILL_MEMORY.md` + 按需 EXAMPLES |
| **T2-EXECUTE** | 正在写 | 不重读；按已加载的协议 3 决定是否先收集信息 |
| **T3-FEEDBACK** | 用户反馈 | `protocols/validated-protocol.md` |
| **T4-MAINTAIN** | 创建/改 skill 结构 | `SKILL_ITERATION.md` + 目标 `ITERATION_GUIDE.md` |

四角色职责隔离是硬约束：代码示例只放 EXAMPLES、硬性规则只放 SKILL_MEMORY、导航放 SKILL、演进规则放 ITERATION_GUIDE。脚本/数据附件可以有，但不能拿来拆 EXAMPLES。

`description` 是 always-on 召回句（约 200 字符）：做什么 + 何时用 + **一句** NOT。漏召回好过误召回。禁止同义词清单和「即使没点名也要用」。

---

## 自我进化

### 采集（Hook 零 token）

```
模型写 .castflow-runtime/memory/*.md（第一段 frontmatter：name + type）
   │  PostToolUse: Write/Edit
   ▼
trace-collector：围栏解析 → 合法 type → quality ok/thin → .trace_memory_snapshots
   │  Stop（有 .trace_lock 则整段 no-op）
   ▼
trace-flush：有快照才写 trace.md（<!-- MEMORY --> 子块）→ 龄期 compaction
```

代码编辑不再采集、不再打分。日常会话不要去读 `trace.md` 或 `memory/`；提醒只看 `.unflushed` / `.evolve_nudge`。无 Stop hook 的宿主（Codex）请 `manager.py flush`。

| 平台 | 配置 | 采集 | 结束 |
|------|------|------|------|
| Claude Code | `.claude/settings.json` | `PostToolUse(Write/Edit/MultiEdit)` | `Stop` |
| Cursor | `.cursor/hooks.json` | `afterFileEdit` | `stop` |
| Grok | `.grok/hooks/castflow.json` | 同上类 PostToolUse | `Stop` |

### Trace（schema:4）

```
<!-- TRACE status:pending schema:4 -->
timestamp: 2026-07-03T13:00:00Z
type: feedback
validated: _
memory_snapshots: 1
<!-- MEMORY slug:observablelist-ordered-insert type:feedback -->
description: ObservableList 有序插入必须用 Insert 不能用 Add
---
（memory 全文）
<!-- /MEMORY -->
<!-- /TRACE -->
```

旧 schema:1–3 可能仍带 `score` / `modules` / `correction` 等退役字段；evolve 读到不报错、不依赖，随 compaction 淘汰。

### 龄期 Compaction

带 memory 快照或 `validated:true` 的**经验资产永不自动删除**。

| 级 | 触发 | 策略 |
|----|------|------|
| L0 | 每次 flush | 清理过期 PROCESSED 审计行 |
| L1 | — | 移除 `validated:invalid` 骨架 |
| L2 | entries/size 超阈值 | 移除超龄非资产骨架 |
| L3 | L2 后仍超标 | 超龄溢出；始终保留最近 `keep_recent_n`（默认 20） |

阈值见 `traces/config/limits.json`。

### origin-evolve

永不自动执行。合格 MEMORY：`feedback`+ok，或 homology 簇大小 ≥ 2。`validated` 只排序、不授权。

```
Step 0 flush（若需要）→ lock
Step 1 Triage（schema 1–4 / pending / 一批 homology）
Step 2 Distill（grep 校验命名 API）
Step 3 Propose（归属决策树 + Append/Merge/Retire + 容量）
Step 4 逐个审批
Step 5 写入 runtime + PROCESSED 行 + sync；finally 丢锁
```

**Anchors**：`[kind:path-hint:symbol]`，`kind ∈ {class, method, field, api, pattern}`。旧格式 `[BuildingManager, OnUpgrade]` 仍兼容。

业务规则只写入项目 skill 或 `.castflow-runtime/rules/cross-cutting.md`，永不写 GLOBAL / CLAUDE.md / hooks / origin-evolve 自身。

---

## 命令参考

### AI 触发词

| 触发词 | 动作 |
|--------|------|
| 冷启动 | 打开启动器（`castflow.bat` / `castflow.sh` / `castflow.command`） |
| 粘贴的 `/goal` 扫描提示词 | 按 loop-engine：programmer-*，一次一个 |
| `castflow generate skills` | skill-creator：一次写一个（队列项 / programmer / 点名的 architect·debug·profiler）然后停 |
| 生成 loop / `/goal` 长任务 / 需求转长任务 | **goal-loop-creator**：编译 Goal Loop Package，不执行 `/goal` |
| `origin evolve` | 蒸馏 trace（进化开启时） |

### manager.py（主入口）

CastFlow 仓里用 `.castflow/manager.py`。已装架的目标项目只有 `.castflow-runtime/`，用下面第二条。

```bash
CastFlow\castflow.bat                          # Windows
./castflow.sh                                  # macOS / Linux（或双击 castflow.command）
python .castflow/manager.py launch             # CastFlow 仓：向导
python .castflow-runtime/manager.py ui         # 目标项目：控制台
python .castflow/manager.py setup              # 无界面 seed+sync（仓内 + --project-root）
python .castflow-runtime/manager.py unseed
python .castflow-runtime/manager.py update-framework
python .castflow-runtime/manager.py seed
python .castflow-runtime/manager.py skills
python .castflow-runtime/manager.py retire NAME
python .castflow-runtime/manager.py activate NAME
python .castflow-runtime/manager.py update NAME
python .castflow-runtime/manager.py sync
python .castflow-runtime/manager.py evolve on|off
python .castflow-runtime/manager.py queue
python .castflow-runtime/manager.py handoff
python .castflow-runtime/manager.py flush              # 无 Stop hook 时手动落账
python .castflow-runtime/manager.py homology           # stdin JSON → 连通分量
python .castflow-runtime/manager.py validate
python .castflow-runtime/manager.py status
python .castflow-runtime/manager.py coldstart --root PATH [--target N]
python .castflow-runtime/manager.py coldstart --root PATH --select ID --queue
python .castflow-runtime/manager.py coldstart --root PATH --select ID --skill
python .castflow/core/hooks/trace-flush.py --selftest
```

若 `python` 无效果：Windows 检查 PATH 或用 `py -3`；macOS 用 `python3`（python.org 或 `brew install python`）。Finder 双击 `.command` 时启动器会补上 Homebrew / python.org 的 PATH。macOS 文件夹选择器走系统对话框，不依赖 tkinter。

### 文件归属

| 分类 | 管理方 | 更新方式 |
|------|--------|---------|
| `CastFlow/` | 本仓库 | `git pull` / submodule update |
| `CLAUDE.md` 框架段 | seed / ROOT_RULES | 装架合并 |
| `CLAUDE.md` 项目段 | 项目团队 | 直接编辑 |
| `.castflow-runtime/skills/` 核心 | 框架 | `update-framework` / `update NAME` |
| `.castflow-runtime/skills/` 项目 | 团队 + evolve | loop-engine / skill-creator / 审批写入 |
| 适配器 `*/skills/` | sync | 不要手改 |
| `.castflow-runtime/traces/` | Hook + evolve | 不要手改 |
| `.castflow-runtime/memory/` | 你在纠正时写 | 不要写 `type: user` |

不要手改 `CastFlow/.castflow/`（会被 `git pull` 覆盖）。定制写在 runtime 与 `CLAUDE.md` 项目段。

---

## 升级与回滚

```bash
cd CastFlow && git pull
python .castflow-runtime/manager.py update-framework
```

只刷新框架 skill 与核心文件（hooks、根规则模板、`SKILL_ITERATION` 等），**不覆盖** `programmer-*-skill` 等项目 skill。`CLAUDE.md` 项目段完全保留。

`update-framework` **不会**写入 `.claude/.backups/`（1.x 安装器已删除）。

装架级回退：GUI「回退并重新冷启动」或 `python .castflow-runtime/manager.py unseed`（卸 runtime、投影、项目里的启动器，不删工程源码）。然后重新打开框架仓的启动器。

---

## 测试套件

全部在 `CastFlow/test/`（**不分发**），零外部依赖（`unittest`）。每次在临时目录隔离运行。

```bash
cd CastFlow
py test/run_all.py
# 或
py -m unittest discover -s test -p "test_*.py" -t .

py test/hooks/test_evolution.py
py test/hooks/test_homology.py
py test/hooks/test_365day_simulation.py --keep-data
py test/bootstrap/test_validate.py
py test/manager/test_setup.py
py test/origin-evolve/verify_redesign.py

# macOS / Linux：py 换成 python3
```

`run_all.py` 还会跑 `trace-flush.py --selftest`。

| 层级 | 覆盖 | 说明 |
|------|------|------|
| Python 正确性 | 是 | 采集门、compaction、homology、validate、seed/sync |
| 数据格式与流转 | 是 | 真实 `trace.md` 写/读/压缩 |
| Hook 事件触发 | 否 | 测试直接调函数，不模拟宿主 stdin JSON |
| origin-evolve 模式识别 | 否 | AI 行为；确定性部分用 `verify_redesign.py` |
| 用户审批 | 否 | 人在回路 |

测试保证 **数据管道机械正确**：长期写入不会损坏、不会无限膨胀、不会丢掉经验资产。生成质量由 `SKILL_ITERATION` + `validate.py` + 人在回路共同保障。

---

## LICENSE

见 [LICENSE](./LICENSE)（MIT）。
