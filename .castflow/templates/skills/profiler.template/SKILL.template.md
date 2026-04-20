---
name: profiler-skill
description: Performance detection and optimization guidance - code review checklist and performance bottleneck diagnosis
---

# Profiler-Skill - 性能瓶颈诊断

**定位**: 性能守卫 (Performance Guard)，通过识别代码反模式定位性能隐患。

**使用方式**:
- **直接使用**: "用 profiler-skill 检查这段代码的性能问题"
- **Agent 加载**: 任何 agent 在优化性能时可加载此 skill
- **Pipeline 编排**: code-pipeline 在 Step 8 中调用

**核心职责**:
1. **热路径诊断**: 识别高频调用路径中的低效操作
2. **内存压力核查**: 定位不必要的内存分配和泄漏
3. **资源占用评估**: 检查缓存未清理、数据结构膨胀
4. **决策反馈**: 生成带有性能收益预估的报告

---

## 快速导航

| 需要了解 | 查看 |
|---------|------|
| 优化示例 | EXAMPLES.md |
| 硬性规则和陷阱 | SKILL_MEMORY.md |
| 迭代和维护 | ITERATION_GUIDE.md |

---

## 性能调度参数 (L1)

在启动前需确定以下指令：

- **target_platform**:
  - Mobile: 采用严格的耗时与内存门控
  - PC: 允许适度的分配，关注吞吐量
  - Server: 关注并发和延迟
  - Web: 关注包体积和首屏加载

- **optimization_goal**:
  - Battery: 侧重减少 CPU 逻辑次数（脏标记、降频）
  - HighPerformance: 侧重极限帧率提升（缓存预取、循环解构）
  - MemorySavings: 侧重减少内存占用（对象池、集合收缩）

- **check_depth**: Audit（通用模式）/ DeepScan（逐行代码审查）

---

## 性能红线 (L2)

{{PERFORMANCE_BUDGETS}}

<!--
bootstrap 根据项目技术栈和平台填入，例如：

Unity Mobile:
  - 单帧耗时红线: > 0.5ms 的热路径逻辑必须优化
  - GC 红线: 禁止在每帧代码中分配内存

React Web:
  - 首次渲染: < 3s
  - 重渲染: 避免不必要的 re-render
  - 包体积: 关注 tree-shaking 和代码分割

Go Server:
  - P99 延迟: < 100ms
  - 内存: 避免 goroutine 泄漏
-->

---

## 优化检查矩阵

| 问题类别 | 典型反模式 | 建议优化方案 | 预期影响 |
|:---|:---|:---|:---|
| **内存分配** | 高频路径中创建临时对象 | 对象池/缓存/预分配 | 减少 GC 抖动 |
| **CPU 热路径** | 高频调用中的低效操作 | 缓存引用/减少查找 | 降低单帧耗时 |
| **内存泄漏** | 订阅未取消/引用未释放 | 成对使用订阅/取消 | 防止长时间运行崩溃 |
| **逻辑冗余** | 高频重复计算 | 脏标记/缓存结果 | 大规模场景流畅度 |

---

## 项目特定优化项

{{PROJECT_SPECIFIC_OPTIMIZATIONS}}

---
