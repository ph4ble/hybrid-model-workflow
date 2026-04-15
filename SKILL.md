---
name: hybrid-model-workflow
description: "HAL 分层混合模型工作流 V6 — 强模型(Claude)负责理解/拆解/验收，低成本模型(DeepSeek V3.1)负责检索/提取/清洗。包含路由规则、Prompt 模板、验收协议、回写规则。Notion+GitHub 已同步（2026-04-16）。"
version: 6.0.0
author: F & HAL
license: MIT
metadata:
  hermes:
    tags: [workflow, multi-model, routing, cost-optimization, chinese]
    homepage: https://www.notion.so/fable/Gemma-4-340fda578bda81648fece9c8107b7705
prerequisites:
  env_vars: []
---

# HAL 分层混合模型工作流

## 设计理念

不是所有任务都值得用最贵的模型。这套工作流把任务按复杂度分层：
- **强模型**：负责理解、拆解、判断、最终校验、对外交付
- **低成本模型**：负责检索、提取、清洗、摘要、分类，产出中间件

核心原则：**低成本模型只产出中间件，不主导最终结论；强模型对所有交付结果负责。**

---

## ⚙️ 用户配置（必读，首次使用前完成）

### 第一步：选择你的模型

你需要选定两个模型：

| 角色 | 推荐选项 | 说明 |
|------|----------|------|
| 强模型（Strong Model） | Claude Opus / Sonnet、GPT-4o 等 | 复杂推理、最终校验、高风险任务 |
| 低成本模型（Cheap Model） | DeepSeek V3、Gemini Flash、GPT-4o-mini 等 | 检索、提取、清洗、摘要 |

选好后，把模型名填入下方配置。

### 第二步：配置 Hermes config.yaml

在 `~/.hermes/config.yaml` 的 `custom_providers` 部分添加你的 provider：

```yaml
custom_providers:
  # 低成本模型（执行层）
  - name: my-cheap-model
    base_url: https://YOUR_API_ENDPOINT/v1   # 替换为你的 API 地址
    api_key: YOUR_API_KEY_HERE               # 替换为你的 Token
    api_mode: chat_completions
    model: YOUR_CHEAP_MODEL_NAME             # 例如：DeepSeek-V3.1、gemini-2.0-flash

  # 强模型（可选，如果你的强模型和默认模型不同）
  - name: my-strong-model
    base_url: https://YOUR_API_ENDPOINT/v1
    api_key: YOUR_API_KEY_HERE
    api_mode: chat_completions
    model: YOUR_STRONG_MODEL_NAME            # 例如：claude-opus-4-6、gpt-4o
```

### 第三步：启用 Smart Model Routing（可选）

如果你希望简单消息自动走低成本模型，在 config.yaml 里配置：

```yaml
smart_model_routing:
  enabled: true
  max_simple_chars: 160    # 消息字符数阈值
  max_simple_words: 28     # 消息词数阈值
  cheap_model:
    provider: my-cheap-model   # 对应上面 custom_providers 的 name
    model: YOUR_CHEAP_MODEL_NAME
```

> 安全提醒：编辑 config.yaml 时不要用 terminal 读取后再粘贴 API key，会导致 key 被截断。直接用文本编辑器编辑，或用 execute_code 中的 Python yaml 库安全写入。

---

## 任务路由决策

收到任务后，先做四个判断：

1. **任务清晰吗？** 目标、输入、输出形式是否明确
2. **任务高风险吗？** 正式结论、复杂判断、多来源冲突、高精度要求
3. **能拆成执行层子任务吗？** 检索、提取、清洗、摘要、分类
4. **结果要直接交付吗？** 是的话必须强模型最终过一遍

### Route A：直接执行
条件：任务清晰 + 风险低 + 检索/提取/格式处理类
→ 低成本模型执行 → 强模型快速复核 → 交付

### Route B：先拆解再执行
条件：复合任务 / 多步骤 / 步骤间有依赖
→ 强模型先拆解 → 分派低成本层 → 强模型汇总验收

### Route C：强模型主导
条件：高风险 / 高模糊 / 策略/架构/判断类
→ 强模型直接主导，低成本层仅做资料预处理

### Route D：信息不足
条件：目标不明确 / 输入严重缺失
→ 先请求澄清，或做已知范围内的初步整理

---

## 低成本执行层 Prompt 模板

调用低成本模型时，用以下模板包装指令：

```
你是一个受限执行器。严格按照指令完成信息处理工作。

## 你的身份
- 你不是最终决策者
- 你只产出中间件，不产出最终结论
- 你的输出会被强模型审核

## 硬性规则
1. 只基于给定材料工作，不引入外部知识
2. 不做价值判断、不给建议、不下结论
3. 找不到就说"Not Found"，不确定就说"Uncertain"
4. 不把推测写成事实
5. 不在信息不足时硬凑完整答案
6. 置信度只填 Low 或 Medium，不允许 High

## 当前任务
{在此填写具体任务描述}

## 允许范围
{在此填写允许处理的材料/内容范围}

## 输出格式（必须严格遵守）

### Task Type
{检索 / 提取 / 清洗 / 摘要 / 分类 / 对比 / 归纳}

### Source Scope
{本次基于哪些材料}

### Evidence Found
{实际找到的证据、片段、关键词、来源位置}

### Extracted Facts
{从证据中明确提取的事实，不写推测}

### Uncertain Points
{证据不足、无法确认、可能冲突的点}

### Missing Information
{还缺什么才能进入下一步}

### Suggested Next Step
{补检索 / 补提取 / 升级强模型 / 可以进入最终汇总}

### Confidence
{Low / Medium}
```

---

## 强模型 Reviewer Prompt 模板

强模型对执行层输出做验收时使用：

```
你现在需要对以下执行层中间件进行验收。

## 用户原始任务
{填写用户的原始需求}

## 执行层输出
{填写低成本模型的中间件输出}

## 验收维度

1. 事实一致性：中间输出是否真的来自输入证据？有没有编造、扩写、误引？
2. 任务完成度：用户真正的问题是否被回答？是否遗漏关键要求？
3. 逻辑与冲突：多个子结果之间是否矛盾？结论是否跳步？
4. 风险与边界：有没有超出证据边界的说法？语气是否过度自信？
5. 表达与可交付性：结果是否清楚、可用？是否区分了事实/推断/建议？

## 你的判定（三选一）

- **Pass**：证据足够、结论边界清晰、可以直接交付 → 生成最终答复
- **Revise**：有缺口但可补 → 明确指出缺什么，打回执行层补充
- **Take Over**：中间件质量太差或任务超出执行层能力 → 强模型直接接管
```

---

## 最终校验 Checklist（强模型交付前必过）

1. 用户原问题是否被完整回答？
2. 所有重要结论是否能回指到证据？
3. 是否有任何一句话超出证据边界？
4. 是否有遗漏的限制条件？
5. 是否有未处理的冲突？
6. 是否明确区分了事实、推断、建议？
7. 是否标出了不确定性？
8. 当前输出是否达到"可以直接交付"的标准？

只要有一项不能明确回答"是"，就不应直接交付。

---

## 结果回写规则

| 目标 | 写什么 | 不写什么 |
|------|--------|----------|
| memory | 稳定用户偏好、环境事实、长期约束 | 一次性任务过程、临时中间结果 |
| Notion | 成熟方法论、学习记录、结构化知识 | 工作底稿、未定稿内容 |
| Obsidian | 词汇分析、词根关联、学习笔记 | 临时摘要 |
| 本地缓存 | 中间清洗结果、工作底稿、临时材料 | 最终结论（那个进 Notion/memory）|

---

## 典型适用场景

1. **英语学习资料整理**：低成本层提取单词/例句/主题 → 强模型校验词义边界和重要度
2. **Notion 词库批量维护**：低成本层扫描异常字段、批量清洗 → 强模型抽样校验
3. **长文档总结**：低成本层切分长文提取要点 → 强模型做最终可交付总结
4. **历史会话召回**：低成本层召回旧会话并提炼 → 强模型判断哪些值得写入 memory/Notion
5. **方法论设计**：强模型先主导框架 → 低成本层补充资料 → 强模型校验定稿

---

## Pitfalls

- 低成本模型绝对不能直接输出最终高价值结论，哪怕它"看起来回答得很好"
- 强模型的验收不是"润色"，是真正的事实复核和边界控制
- 证据不足时宁可不完整，不要为了看起来完整而乱补
- smart_model_routing 只对消息字符/词数做简单判断，复杂任务仍需手动路由
- 编辑 config.yaml 含 API key 的行时，必须用 Python yaml 库直接操作，不能用 terminal cat/grep 读出来再粘贴
