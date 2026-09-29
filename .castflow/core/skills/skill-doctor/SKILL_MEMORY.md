### Rule 1: 不改项目内容

Anchors: [pattern:castflow-skills]
Related: Rule 5, Pitfall 1

定义
优化过程只读业务脚本和链路模块。业务仓库里的脚本、预制和资源一律不写。候选先写在 `loop-engine/runs/skill-doctor/<目标技能名>/candidate/`。判定为升之后，才把候选覆盖到目标 skill 的角色文件。

检查清单
- [ ] 业务脚本没有被修改
- [ ] 判定之前，目标 skill 与快照一致

### Rule 2: 先有焦点再探链

Anchors: [pattern:ITERATION_GUIDE.md]
Related: Rule 4, Pitfall 2

定义
先读目标 skill 的 `ITERATION_GUIDE.md`，把这次允许关心的变化写成焦点。没有这份文件，或它给不出可核对的焦点，就停止。不另编一套焦点，也不按产品愿望加触发。

检查清单
- [ ] 每条偏差要么指回指南里的一条焦点，要么指回本轮打开、且技能尚未记录的功能

### Rule 3: 候选出现之前冻住题目

Anchors: [pattern:loop-engine/runs/skill-doctor]
Related: Rule 5, Pitfall 3

定义
偏差写完之后、候选正文写出之前，把题目冻在运行目录。题目只写做完之后必须成立的结果或约束。旧快照和候选各跑一次。同时运行的 subagent 不超过 3。

检查清单
- [ ] 题目早于候选正文
- [ ] 题目没有引用候选的句子
- [ ] 每一题每一边只有一次运行

### Rule 4: 连通性只承认打开过的定义

Anchors: [pattern:EXAMPLES.md]
Related: Rule 2, Pitfall 4

定义
定位脚本要打开。调用只沿本轮打开的定义往下走。没打开的被调方标未证实。文件不在，或该功能已不由这个脚本持有，才标断。没有跑游戏时，不把「仍由该脚本持有」写成「运行时生效」。

检查清单
- [ ] 每条连通结论都写了打开的文件
- [ ] 未打开的调用不是已连通

### Rule 5: 只有升才改目标 skill

Anchors: [pattern:SKILL.md]
Related: Rule 1, Rule 3, Pitfall 1, Pitfall 5

定义
方向是结果、回归、召回、越界、稳定、成本。升必须同时满足：结果有可引用的优势，冻住的旧约束没有被破坏，越界没有变差。召回没有实际跑过时，不能单独撑起升。成本和单次运行的稳定只记录，不改变结论。降、混合、持平、无差异都不写入目标 skill。

检查清单
- [ ] 结论不是升时，目标 skill 与快照一致
- [ ] 稳定没有被写成提升
- [ ] 成本没有把升改成降，也没有把持平改成升

### Rule 6: 三条探索之后只做一次判定

Anchors: [pattern:ITERATION_GUIDE.md]
Related: Rule 2, Pitfall 6

定义
连通性、未记录功能、规则是否盖住指南焦点，这三条可以各派一个只读 subagent。三条齐了就停。偏差、冻题、判定和落盘由这一轮自己做，不再加探索轨道。

检查清单
- [ ] 同时运行的 subagent 不超过 3
- [ ] 没有第四条探索轨道

### Pitfall 1: 没提升也改了正文

Anchors: [pattern:SKILL.md]
Related: Rule 5

现象
偏差看起来有道理，目标 skill 的文件就被改了。

防护
先对比再落盘。无差异就保持原文件。

### Pitfall 2: 探到了无关模块

Anchors: [pattern:EXAMPLES.md]
Related: Rule 2, Rule 4

现象
探索离开该 skill 点名的脚本，编出新职责。

防护
只读已点名的脚本，以及这些脚本里写出、且本轮打开了的调用目标。

### Pitfall 3: 看过候选再补题

Anchors: [pattern:loop-engine/runs/skill-doctor]
Related: Rule 3

现象
题目跟着候选的措辞走，于是一定判升。

防护
题目在候选正文存在之前冻住，并且不引用候选句子。

### Pitfall 4: 把未证实写成失效或生效

Anchors: [pattern:EXAMPLES.md]
Related: Rule 4

现象
没打开被调方，或没跑游戏，结论却是断或已生效。

防护
用未证实。断只用于文件缺失，或功能已不在该脚本。

### Pitfall 5: 并行超过 3

Anchors: [pattern:SKILL.md]
Related: Rule 3, Rule 6

现象
同时开出一串 subagent，请求失败。

防护
同时运行的 subagent 最多 3 个。多出来的排队。没有 subagent 时串行。

### Pitfall 6: 用调用步骤给能力打分

Anchors: [pattern:SKILL.md]
Related: Rule 5

现象
候选多读了几个文件，就被判成提升。

防护
分数只来自冻住题目上的结果、回归和越界。链路步骤不进结论。
