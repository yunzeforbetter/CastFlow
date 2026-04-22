# GLOBAL_SKILL_MEMORY - Skill 运行时核心协议

> **性质**：所有 Skill 执行的底层法律。运行时约束，非创建规范。
> **加载时点**：本文档协议 1/2 在 **T1-PREPARE** 加载，协议 3 在 **T2-EXECUTE** 加载。完整时点定义见项目根 `CLAUDE.md`「使用Skill的分层加载」段（唯一权威源）。
> **关联文档**：
> - 创建和迭代规范见 [SKILL_ITERATION.md](./SKILL_ITERATION.md)（仅 T4-MAINTAIN 加载）
> - IDP 写入规则见 [protocols/idp-protocol.md](./protocols/idp-protocol.md)（T2-EXECUTE 按需）
> - validated 信号规则见 [protocols/validated-protocol.md](./protocols/validated-protocol.md)（仅 T3-FEEDBACK）
> - pipeline 扩展协议见 [code-pipeline-skill/config/pipeline_protocol.md](./code-pipeline-skill/config/pipeline_protocol.md)（pipeline 期间附加生效）

---

## 协议 1：物理证据准入制 - P0（T1-PREPARE）

**定义**：使用任何类或 API 前，必须完成三段式验证，缺一不可：

1. **Read 源文件** — 理解该类的职责、成员变量、生命周期（自定义类必须完整读，不能只看签名）
2. **识别真实 API** — 从已打开的源文件中确认 public 方法/属性及其参数类型和返回值
3. **Grep 验证存在** — 在项目中找到该 API 的至少一个真实调用，确认定义在该类（不是别的类）

使用 API 前必须能说出"该 API 在文件 X 的 Y 行定义"。无法完成验证则标 TODO，不生成代码。

**禁止**：跨类假设（A 有此方法所以 B 也有）、记忆假设（基于"通常做法"编码）、部分验证（grep 有结果就认为存在）

---

## 协议 2：学习后强制约束对齐 - P0（T1-PREPARE）

**定义**：学习代码或设计方案后，生成代码前必须执行约束对齐，流程不可跳过。

**执行步骤**（按顺序）：

1. 列出约束来源：GLOBAL_SKILL_MEMORY.md、目标 Skill 的 SKILL_MEMORY.md、CLAUDE.md
2. 逐项对比学习到的实现与约束，标记所有冲突（"违反项 -> 约束来源"）
3. 有冲突则调整实现（如 mLevel 改为 _level）；有未验证 API 则标 TODO
4. 生成代码前明确告知用户应用了哪些约束、做了哪些调整

**检查清单**：
- [ ] 约束来源清单已列出？
- [ ] 冲突已识别并处理？
- [ ] 已向用户说明约束和调整？
- [ ] 未验证的 API 已标 TODO？

---

## 协议 3：执行模式检测 - P0（T2-EXECUTE）

**定义**：每次代码生成前判断执行模式，决定 IDP 写入时机和探索深度。

| 模式 | 触发条件 | 行为 |
|------|---------|------|
| 信息不足 | 需求模糊、影响范围不明 | 先收集信息，不写 IDP，不写代码 |
| 紧急 | 用户要求立刻修复、时间紧迫 | 先写代码，完成后补写回溯 IDP（`retrospective: true`） |
| 高精度 | 要求一次性正确、跨多模块、高风险 | 深度探索 + 风险声明 + 用户确认后再写 IDP 和代码 |
| 标准 | 其他情况 | 写 IDP -> 写代码 |

**检查清单**：
- [ ] 是否判断了模式？
- [ ] 信息不足时是否先收集而非直接写代码？
- [ ] 高精度模式是否等待用户确认？

模式判定后，按 IDP 写入时机加载 [idp-protocol.md](./protocols/idp-protocol.md) 完成 `.pending_idp.json` 写入。

---

*GLOBAL_SKILL_MEMORY | 核心运行时协议 1-3 | IDP/validated 协议按需加载*
