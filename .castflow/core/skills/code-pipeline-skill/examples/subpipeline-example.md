# 子 Pipeline 示例

## 父 pipeline 中的状态与派发

当 M8 被认定为不适合继续按单模块推进时，先回写状态：

| Module | Type | ArtifactState | DependsOn | CurrentBarrier | LastCheckpoint |
|---|---|---|---|---|---|
| M8 | DomainComplex | NeedsSubpipeline | MI_EVENT,M4,M5 | LocalBarrier | CP-04 |

再更新当前派发表。这里的 `sub-pipeline` 行不是普通模块配对派发，而是升级后的显式子流程派发：

| Wave | Module | ArtifactState | Barrier | DispatchTarget | Inputs | ExpectedOutput | Fallback |
|---|---|---|---|---|---|---|---|
| Wave 3 | M8 | NeedsSubpipeline | LocalBarrier=Blocked | sub-pipeline | Parent Scope, Shared Core, Parent Summary 模板 | Parent Summary | hold |

## Step 3 模块 summary 与 `Parent Summary`

### 普通模块的 `PIPELINE_SUMMARY`

```md
<!-- PIPELINE_SUMMARY -->
## AllianceMember
- Implemented Provides: AllianceMemberList
- Remaining Blocks: None
<!-- /PIPELINE_SUMMARY -->
```

### 子 pipeline 的 `Parent Summary`

```md
### Parent Summary
- Provides 已兑现：GatheringPlace / AllianceMark / Milestone APIs
- Requires 已闭合：事件协议、城市边界映射
- Remaining Blocks：资源结算仍为 caution
- Module Verdict：GO-WITH-CAUTION
```

## 关键区别

- `PIPELINE_SUMMARY`：用于 Step 3 模块归并
- `Parent Summary`：用于父 pipeline 消费子 pipeline 结果

父 pipeline 不应把子 pipeline 的全量细节重新展开到主上下文。
