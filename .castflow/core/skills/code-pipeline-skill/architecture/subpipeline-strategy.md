# Sub-pipeline Strategy

子 pipeline 的主定义页。

## 什么时候升级为子 pipeline

满足任一条件时，优先考虑子 pipeline：

- Handoff Level 已达到 `L3`
- 模块内部仍需拆成 3+ 子职责
- 模块长期处于 `Exploring` 或 `Stalled`
- Shared Core 已稳定，但该模块仍无法冻结
- 该模块需要独立的 closure / coverage / verdict 语义

## 父 pipeline 提供什么

父 pipeline 至少提供：

- 该模块在父级的职责边界
- 已冻结的 Shared Core
- 期望消费的 Provides / Verdict 范围
- `Parent Summary` 模板

## 子 pipeline 回传什么

```md
### Parent Summary
- Provides 已兑现：
- Requires 已闭合：
- Remaining Blocks：
- Module Verdict：GO / GO-WITH-CAUTION / NO-GO
```

## `Parent Summary` 与 Step 3 模块 summary 的区别

- `Parent Summary`：子 pipeline 回传父 pipeline
- `PIPELINE_SUMMARY`：普通 Step 3 模块实现归并

二者不可混用。

## 父 pipeline 如何消费

父 pipeline 只基于 `Parent Summary` 做三类决策：

- 是否允许依赖该模块的下一波启动
- 是否把 Remaining Blocks 升级为父级阻塞
- 是否在全局 Step 4 / Step 5 增加额外检查

父 pipeline 不应把子 pipeline 的全部细节重新展开到主上下文。

## 什么时候不要开子 pipeline

- 只是代码量大，但边界并不复杂
- 没有独立的 contract / closure / verdict 语义
- 继续在一个模块配对执行单元内就能收敛
