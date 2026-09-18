# Bootstrap-Skill 示例库

展示 seed / scan / UI / 队列生成。勾选扫描时由 AI 按 `MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` 划分**业务**模块并弹出多选（不扫 CastFlow / 装架目录）。

---

## 示例 1：冷启动

### GUI 冷启动（第一条消息）

```
AI: 冷启动请双击 CastFlow\castflow.bat（或运行 python CastFlow/.castflow/manager.py launch）。
    在打开的页面里选语言 / 适配器 / 进化，点「开启冷启动」。我不会代跑 seed。
用户: 好，我打开了
AI: 未勾选「扫描模块并生成 skill」就只是拷文件，不用给我提示词。勾选了就把页面上的提示词粘过来（默认 `/goal 读取并按照 .castflow-runtime/skills/MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md 执行`）。
```

### 命令（GUI 打不开时的后备）

```
CastFlow\castflow.bat
python CastFlow/.castflow/manager.py launch
python CastFlow/.castflow/manager.py setup
python CastFlow/.castflow/manager.py ui
```

勾选扫描生成时，默认交接是一行：`/goal 读取并按照 .castflow-runtime/skills/MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md 执行`。`/goal` 启动长任务。用户可改提示词；留空用这条。未勾选则无交接提示词。

重新冷启动：GUI「回退并重新冷启动」或 `python .castflow/manager.py unseed`，不必手删拷过去的文件。

### 粘贴 /goal 之后（模块 skill）

AI 按 `MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md`：多选 -> 把选中短卡落到 `.castflow-runtime/_skill-gen-queue/` -> 清上下文 -> 一次只写一个 programmer skill -> 该卡标 `status: done` -> 再清上下文。全部完成后删除队列目录。禁止并行子代理。不要跑评测环。

### 之后生成 architect / debug / profiler

GUI「队列」页把已勾选的核心 skill 入队，或用户输入：

```
castflow generate skills
```

主 agent 只写 JSON 队列第一项，validate + sync，然后停。下一轮再取下一项。不要和 `/goal` 模块生成同一回合并行。

---

## 示例 2：进化开关

```
python .castflow/manager.py evolve off
```

或在 UI 点「关闭进化」。hook、origin-evolve 投影、根规则进化段全部卸下。再 `evolve on` 恢复。不删除 traces。

---

## 示例 3：核心更新

已有 `.castflow-runtime/` 时，`bootstrap castflow` 走更新：复用 config.language，`manager.py sync` 刷新核心 skill 与投影，不覆盖用户 catalog 与已生成的 programmer skill。
