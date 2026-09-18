# ITERATION_GUIDE - Profiler-Skill

格式、体积、职责隔离见 SKILL_ITERATION.md，不要把那份表抄到这里。

### Rule 1：新反模式

触发：出现新的性能反模式，且有判定条件和优化方向。
文件：SKILL.md 检查矩阵；热路径场景补 EXAMPLES.md。

### Rule 2：平台红线调整

触发：项目性能预算变化。
文件：SKILL.md 性能红线，按平台给量化值。

### Rule 3：项目特定优化项

触发：本仓库技术栈有通用清单盖不住的热点。
文件：SKILL.md 项目特定段。与通用项重复则不写。
