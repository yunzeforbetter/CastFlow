# Handoff Protocol - 轻量模块交接质量门

> **性质**：仅在 code-pipeline 涉及多 agent / 多模块协作时生效。Handoff 不是重型 contract；它是模块间的最小交接任务单，用于提升边界质量、集成质量和业务完成度。

## 什么时候读这个文件

当你已经进入多模块协作，但还不清楚**模块边界怎么锁、依赖怎么对、验收怎么闭环**时，读这个文件。

它主要回答：
- 这次协作该用 L0 / L1 / L2 / L3 哪个 Handoff Level
- Handoff Draft 应该写哪些字段
- 进入 Step 3 前，Freeze Gate 要过哪些门
- Step 3 结束后，Handoff Update 怎么回写
- Step 4 / Step 5 分别基于什么做 Closure / Coverage / Verdict
- Step 6 补全后为什么必须回到验证闭环

如果你关心的是 PCB、run_id、L1×L2 合成等执行期机制，回到 `config/pipeline_protocol.md`。

---

## 1. Handoff Level

**何时读这节**：Step 1 正在决定 Handoff 要写到什么粒度时。

| Level | 适用场景 | 要求 |
|-------|---------|------|
| L0 | 单模块 / 单 agent / 小改动 | 不需要 Handoff |
| L1 Basic | 2-3 个模块，依赖简单 | `Owns / Provides / Requires / Blocks` |
| L2 Quality | 3+ 模块、并行实现、业务风险或 API 边界复杂 | L1 + `Goal / Constraints / Done Criteria / Open Questions` |
| L3 Recursive | 某个模块内部仍需拆分为子 pipeline | L2 + `Sub-pipeline Trigger / Parent Summary` |

**选择原则**：用刚好足够的 Level。低风险不加负担，高风险不省质量门。

---

## 2. Handoff Template

**何时读这节**：已经确定要写 Handoff，但还不确定模板字段时。

### L1 Basic

```md
## Handoff: {ModuleName}

### Owns
- 本模块负责的职责边界。

### Provides
- 本模块对外提供的 API / 数据 / 事件。

### Requires
- 本模块依赖其他模块提供的 API / 数据 / 事件。

### Blocks
- 当前阻塞项；没有则写 `None`。
```

### L2 Quality

```md
## Handoff: {ModuleName}

### Goal
- 本模块在本次需求中的目标。

### Owns
- 本模块负责的职责边界。

### Provides
- 本模块对外提供的 API / 数据 / 事件。

### Requires
- 本模块依赖其他模块提供的 API / 数据 / 事件。

### Blocks
- 当前阻塞项；标记 `completable` / `blocking` / `unknown`。

### Constraints
- 必须遵守的 skill / 项目约束。

### Done Criteria
- 本模块完成后必须满足的业务条件。

### Open Questions
- `UserDecision`：必须用户确认。
- `TODO`：可占位推进。
- `Risk`：记录风险后可推进。
```

### L3 Recursive

在 L2 后追加：

```md
### Sub-pipeline Trigger
- 为什么该模块需要子 pipeline。

### Parent Summary
- 子 pipeline 完成后回传给父 pipeline 的摘要格式。
```

---

## 3. Freeze Gate

**何时读这节**：准备从 Step 1 / Step 2 进入 Step 3 前。

**解决的问题**：在并行实现前先锁职责边界，避免各 agent 边写边漂移。

进入 Step 3 前，Handoff 必须满足：

- [ ] Handoff Level 已确定。
- [ ] 每个模块的 `Owns` 不重叠。
- [ ] `Provides` 明确到 API / 数据 / 事件形态。
- [ ] `Requires` 有候选 Provider，或明确标记 `unknown`。
- [ ] `Blocks` 已分类；无阻塞写 `None`。
- [ ] L2/L3 的 `Constraints` 已绑定相关 skill / 项目约束。
- [ ] L2/L3 的 `Done Criteria` 能验证业务完成度。
- [ ] `Open Questions` 中不存在未解决的 `UserDecision`。

状态只使用三种：`Draft` / `Frozen` / `Blocked`。

---

## 4. Handoff Update

**何时读这节**：Step 3 模块实现完成后，需要把新增依赖、剩余阻塞和证据回写时。

每个 programmer-agent 完成 Step 3 后输出：

```md
## Handoff Update: {ModuleName}

### Implemented Provides
- 已兑现的 Provides。

### Added Requires
- 实现中新增的依赖；没有则写 `None`。

### Remaining Blocks
- 仍存在的阻塞；没有则写 `None`。

### TODO
- 规范 TODO；没有则写 `None`。

### Evidence
- 修改文件：
- 参考 API：
- 已验证 API：
```

**规则**：新增 `Requires` / `Blocks` 只能通过 Handoff Update 暴露，禁止隐式跨模块依赖。

---

## 5. Dependency Closure

**何时读这节**：Step 4 需要统一 Closure 分类口径时。

**解决的问题**：把“依赖有没有闭合”与“哪里还缺口”结构化输出，而不是凭感觉总结。

Step 4 输出：

```md
## Dependency Closure Report

### Closed
- A.Requires X -> B.Provides X

### MissingProvider
- Requires 找不到 Provider 的项。

### SignatureMismatch
- 签名、参数、返回值不一致的项。

### BoundaryViolation
- 模块实现越出 Owns 的项。

### CompletableBlocks
- 可在 Step 6 补全的阻塞。

### BlockingBlocks
- 必须返工或用户决策的阻塞。

### ImplicitRequires
- 实现中出现但 Handoff 未声明的依赖。
```

---

## 6. Done Criteria Coverage

**何时读这节**：Step 5 需要统一 Coverage 检查口径时。

**解决的问题**：把“业务是否完成”从代码存在与否里剥离出来，单独验证。

Step 5 检查 L2/L3 的 `Done Criteria`：

```md
## Done Criteria Coverage

### {ModuleName}
- [x] 已覆盖的业务条件。
- [ ] 未覆盖的业务条件；说明修复方向。
```

模块 GO 需要同时满足：Dependency Closure 无阻塞问题，且 Done Criteria 已覆盖或仅剩明确可补全的 caution。

---

## 7. Step 6 Re-closure

**何时读这节**：Step 5 判成 `GO-WITH-CAUTION`，准备补全 `CompletableBlocks` 时。

**解决的问题**：防止 Step 6 补完代码后直接宣布结束，却没重新验证闭环。

Step 6 补全 `CompletableBlocks` 后必须回到验证闭环：

- 至少重新执行 Step 4，确认 Dependency Closure 不再产生新增阻塞。
- 如果 Step 4 输出变化影响 Done Criteria 或 Module Verdict，必须重新执行 Step 5。
- Step 6 不得直接把 GO-WITH-CAUTION 改为 GO，最终状态只能由 Step 5 判定。

---

## 8. Recursive Pipeline Summary

**何时读这节**：某个模块内部继续拆子 pipeline，需要把结果回传给父 pipeline 时。

父 pipeline 只读取子 pipeline 的 `Parent Summary`，不读取子 pipeline 全量细节：

```md
### Parent Summary
- Provides 已兑现：
- Requires 已闭合：
- Remaining Blocks：
- Module Verdict：GO / GO-WITH-CAUTION / NO-GO
```
