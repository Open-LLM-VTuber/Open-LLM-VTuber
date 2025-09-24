## MemU 集成指南（Open-LLM-VTuber）

本文档介绍如何在 Open-LLM-VTuber 中启用与使用 MemU 作为可选的“长期记忆”能力，包括安装、配置、工作原理、调优、排错与安全建议。

### 适用版本
- Open-LLM-VTuber ≥ 1.2.0
- Python ≥ 3.10
- memu-py ≥ 0.1.8（已写入项目依赖）

---

## 快速开始

1) 同步依赖

```bash
uv sync
```

2) 填写配置（其一即可）

- 方式 A：在角色配置 `character_config.agent_config.agent_settings.basic_memory_agent` 下启用：

```yaml
# conf.yaml 片段（示例）
character_config:
  agent_config:
    conversation_agent_choice: 'basic_memory_agent'
    agent_settings:
      basic_memory_agent:
        llm_provider: 'ollama_llm'
        use_mcpp: false
        # -- MemU Long-term Memory (Optional) --
        memu_config:
          enable: true
          base_url: "https://api.memu.so"
          api_key: "your_memu_api_key_here"
          top_k: 3
          min_similarity: 0.7
```

- 方式 B：使用环境变量（便于避免将 Key 写入配置）：

```bash
export MEMU_API_KEY="your_api_key_here"
# 可选：覆盖服务地址（默认 https://api.memu.so）
export MEMU_API_BASE_URL="https://api.memu.so"
```

3) 启动应用，观察日志

出现如下日志说明 MemU 已启用：

```
MemU long-term memory enabled for this agent ✨
```

开始对话后，日志会显示检索/写入状态：

- 检索注入：Injected long-term memories into this turn's context.
- 写入排队：Scheduled conversation for memorization with MemU.

---

## 工作原理

- 检索（在 LLM 推理前）
  - 使用 `retrieve_related_memory_items(user_id, agent_id, query, top_k, min_similarity)` 检索与当前用户输入相关的长期记忆。
  - 将检索到的若干条记忆文本，格式化为一段“前置上下文”，拼接到本轮临时 system prompt 的前部，再调用底层 LLM 进行生成。
  - 该检索在后台线程执行，失败会自动降级且不影响主流程。

- 写入（在本轮完整回复后）
  - 将本轮的「用户输入 + AI 回复」作为结构化对话，异步调用 `memorize_conversation` 写入 MemU，获得任务 ID（不阻塞音频流与 UI）。
  - 可通过输入 `metadata` 传入 `skip_memory=True` 跳过本轮写入（如含敏感内容或临时不想存档）。

这种“只在本轮提示中注入”策略不污染历史会话记忆；即使 MemU 不可用，核心语音对话能力仍可离线运行。

---

## 身份与字段映射

- user_id: 由运行时会话的 `client_uid` 注入。
- user_name: 取自 `character_config.human_name`（默认 “Human”）。
- agent_id: 由当前角色配置的 `conf_uid` 注入（每个角色可视为不同的“Agent”）。
- agent_name: 取自 `character_config.character_name`（或 `conf_name` 作为回退）。

以上均在 `AgentFactory`/`ServiceContext` 层自动传入 `BasicMemoryAgent`，无需手动干预。

---

## 配置项说明（memu_config）

- enable: 是否启用 MemU（默认 false）。
- base_url: MemU 服务地址（默认 `https://api.memu.so`）。
- api_key: MemU API Key。可用环境变量代替。
- top_k: 每次检索的条数（默认 3）。
- min_similarity: 检索相似度阈值，范围 [0,1]（默认 0.7）。

调优建议：
- 若注入内容过多导致提示过长或跑偏，可降低 `top_k` 或提高 `min_similarity`。
- 追求命中率可适当提高 `top_k`、降低 `min_similarity`，但注意上下文污染与 token 成本。

---

## 行为细节与性能

- 非阻塞：检索/写入调用使用 `asyncio.to_thread` + 后台任务，避免阻塞 TTS 流与首响（目标 < 500ms）。
- 失败降级：未安装 `memu-py`、缺少 API Key、网络异常等情况将记录日志并自动跳过，不影响主流程。
- 注入范围：仅在本轮生成的临时 system prompt 中添加，不改变已存储的对话历史。

---

## 进阶能力（可选 API）

当前内置流程默认只用到“相关记忆检索 + 对话写入”。若要做更复杂的功能（如 UI 中展示记忆分类/聚类、管理记忆），可在你的扩展代码中直接使用 `memu-py`：

```python
# Example only. Do not paste API keys in code.
import os
from memu import MemuClient

client = MemuClient(base_url=os.getenv("MEMU_API_BASE_URL", "https://api.memu.so"),
                    api_key=os.getenv("MEMU_API_KEY"))

# 1) 检索默认分类摘要
cats = client.retrieve_default_categories(user_id="user123", agent_id="agent456",
                                          include_inactive=False, want_summary=True)
for c in cats.categories:
    print(c.name, c.memory_count, c.summary)

# 2) 搜索相关记忆
mems = client.retrieve_related_memory_items(user_id="user123", query="favorite food",
                                            top_k=5, min_similarity=0.5,
                                            include_categories=["preferences"]) 
for r in mems.related_memories:
    print(r.memory.content, r.similarity_score)

# 3) 聚类后的相关分类（摘要）
clusters = client.retrieve_related_clustered_categories(user_id="user123",
                                                        category_query="personal preferences",
                                                        top_k=3, want_summary=True)
for g in clusters.clustered_categories:
    print(g.name, g.similarity_score, g.summary)

# 4) 删除记忆（谨慎）
client.delete_memories(user_id="user123", agent_id="agent456")
```

---

## 常见问题与排错

### 1. 已配置但无效？
- 确认 `memu_config.enable: true`。
- 确认 `api_key` 有效（或通过 `MEMU_API_KEY` 注入）。
- 启动日志若出现 “MemU is enabled but 'memu-py' is not installed” 请执行 `uv sync`（或 `uv add memu-py`）。

### 2. 远端错误码
- 401/403：鉴权失败或权限不足 → 核对 API Key / 项目权限。
- 422：参数校验失败 → 校验 `user_id/agent_id/query/top_k/min_similarity` 等字段。
- 5xx：服务端错误 → 稍后重试或联系服务方。

### 3. 延迟或跑偏
- 降低 `top_k` 或提高 `min_similarity`，减少注入的长期记忆数量与噪声。
- 若 LLM 输出明显受“陈年记忆”干扰，考虑提高阈值、或将敏感回合通过 `skip_memory=True` 禁止写入。

### 4. 离线可用性
- MemU 为远端服务。即便网络不可用，Open-LLM-VTuber 的核心离线语音链路仍可工作；MemU 检索/写入会自动跳过。

---

## 安全与隐私

- 对话写入 MemU 会将文本发送到远端服务；请勿写入敏感或受限数据。
- 可通过输入的 `metadata.skip_memory=True` 针对单回合跳过写入。
- 若对隐私敏感，建议：
  - 使用环境变量而非将 Key 写入配置文件。
  - 自行搭建/选择受控的 MemU 部署（如官方支持）。

---

## 变更与兼容性

- 依赖：`memu-py>=0.1.8`。
- 新配置：`basic_memory_agent.memu_config`（可选，默认关闭）。
- 与 MCP、群聊等功能互不冲突；未启用 MemU 时行为与旧版一致。

---

## 附录：与系统内部映射关系（参考）

- `user_id` ← `ServiceContext.client_uid`
- `agent_id` ← `character_config.conf_uid`
- `user_name` ← `character_config.human_name`
- `agent_name` ← `character_config.character_name`

以上映射用于在多角色/多会话下隔离与组织长期记忆。


