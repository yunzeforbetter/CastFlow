# ITERATION_GUIDE - Architect-Skill

格式、体积、职责隔离见 SKILL_ITERATION.md，不要把那份表抄到这里。

### Rule 1：新约束

触发：项目出现新的强制分层、基类或隔离规则。
文件：SKILL_MEMORY.md。先核对是否与现有规则冲突。

### Rule 2：新的已验证模式

触发：仓库里出现经过验证、调用时会照着抄的设计模式。
文件：EXAMPLES.md。代码从项目复制，路径必须能 grep 到。

### Rule 3：职责变化

触发：architect-skill 与 programmer / debug / profiler 的边界变了。
文件：SKILL.md 的 Yield 与职责。
