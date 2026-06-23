# nano-agent
A Simple Agent Learning Project. Building an Agent from zero.

## Agent 记忆机制介绍

### 概述

`agent_plus.py` 在 `agent.py` 的基础上新增了**跨会话持久化记忆**功能。当进程结束后，下次启动时 Agent 依然能记住之前保存的信息。

---

### 核心实现

**存储位置**：`.agent_memory/memory.json`

**四个核心函数**：

| 函数 | 作用 |
|------|------|
| `memory_read()` | 读取历史记忆 |
| `memory_write(content)` | 覆盖写入（完全替换旧记忆） |
| `memory_append(text)` | 追加到现有记忆末尾 |
| `memory_clear()` | 清除所有记忆 |

**数据结构**（`memory.json`）：
```json
{
  "content": "User's name is Alice",
  "updated_at": "2026-06-22 20:59:55"
}
```

---

### 工作流程

1. **Agent 启动时** → `agent_loop()` 调用 `memory_read()` 获取上次保存的记忆
2. **记忆内容拼接到 system prompt 开头**，让 LLM 在每次对话时都能看到历史上下文
3. **对话过程中** → LLM 自主决定何时调用 `memory_write/memory_append` 保存重要信息
4. **进程结束** → 记忆已写入磁盘文件，下次启动自动恢复

---

### 使用示例

```bash
# 第一次对话：让 Agent 记住一些事
python agent_plus.py "我的项目叫 nano-agent"

# 第二次对话（进程重启后）：Agent 自动读取了之前的记忆
python agent_plus.py "我的项目叫什么名字？"
# → "你的项目叫 nano-agent"
```

---

### 与 system prompt 的区别

| | System Prompt | Memory |
|--|--------------|--------|
| **生命周期** | 每次对话重置 | 持久化到磁盘 |
| **内容来源** | 硬编码的工具描述 | Agent 动态写入 |
| **用途** | 告知 Agent 有哪些工具 | 保存用户偏好、项目状态等上下文 |

简单说：**system prompt 告诉 Agent "你会什么"，记忆告诉 Agent "用户是谁/要什么"**。
