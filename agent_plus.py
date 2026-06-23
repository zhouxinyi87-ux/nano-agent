from openai import OpenAI
import json
import subprocess
import os
from datetime import datetime

#加载配置
with open("config.json", "r") as f:
    config = json.load(f)

client = OpenAI(
    base_url=config["base_url"],
    api_key=config["api_key"]
)

# ============ 记忆存储路径 ============
MEMORY_DIR = ".agent_memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")

# ============ 记忆工具函数 ============
def _ensure_memory_dir():
    """确保记忆目录存在"""
    if not os.path.exists(MEMORY_DIR):
        os.makedirs(MEMORY_DIR)

def memory_read() -> str:
    """读取当前记忆内容"""
    _ensure_memory_dir()
    if not os.path.exists(MEMORY_FILE):
        return "No memory found. This is a fresh start."

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        memory_content = data.get("content", "")
        last_updated = data.get("updated_at", "unknown")

        if not memory_content:
            return "Memory is empty. This is a fresh start."

        return f"Last updated: {last_updated}\n\nMemory content:\n{memory_content}"
    except Exception as e:
        return f"Error reading memory: {e}"

def memory_write(content: str) -> str:
    """写入记忆内容"""
    _ensure_memory_dir()
    try:
        data = {
            "content": content,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return f"Memory saved at {data['updated_at']}"
    except Exception as e:
        return f"Error writing memory: {e}"

def memory_append(text: str) -> str:
    """向记忆追加内容"""
    _ensure_memory_dir()
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            current_content = data.get("content", "")
        else:
            current_content = ""

        if current_content:
            new_content = current_content + "\n" + text
        else:
            new_content = text

        data = {
            "content": new_content,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return f"Appended to memory at {data['updated_at']}"
    except Exception as e:
        return f"Error appending to memory: {e}"

def memory_clear() -> str:
    """清除记忆"""
    _ensure_memory_dir()
    try:
        if os.path.exists(MEMORY_FILE):
            os.remove(MEMORY_FILE)
        return "Memory cleared"
    except Exception as e:
        return f"Error clearing memory: {e}"

# ============ 文件操作工具 ============
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a specific part of a file using string replacement",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "String to find and replace"},
                    "new_string": {"type": "string", "description": "New string to replace with"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command and return the output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to execute"},
                    "timeout": {"type": "number", "description": "Timeout in seconds (default: 30)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Run a Python program with automatic verification",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the Python file to run"},
                    "expected_output": {"type": "string", "description": "Expected output substring that proves the program works correctly"},
                    "test_input": {"type": "string", "description": "Optional stdin input to pass to the program"}
                },
                "required": ["file_path", "expected_output"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_read",
            "description": "Read the agent's long-term memory from previous sessions",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_write",
            "description": "Write important information to long-term memory (overwrites previous memory)",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The complete memory content to save"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_append",
            "description": "Append new information to existing memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to append to memory"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "memory_clear",
            "description": "Clear all memory (use with caution)",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Create a structured plan BEFORE taking any action. Use this for complex tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "The user's task/goal"},
                    "steps": {"type": "array", "items": {"type": "string"}, "description": "Ordered list of steps to achieve the task"}
                },
                "required": ["task", "steps"]
            }
        }
    }
]

# ============ 工具执行函数 ============
def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f"File content:\n{f.read()}"
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(path: str, content: str) -> str:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {e}"

def edit_file(path: str, old_string: str, new_string: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old_string not in content:
            return f"Error: String not found in file"
        new_content = content.replace(old_string, new_string, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Successfully edited {path}"
    except FileNotFoundError:
        return f"Error: File '{path}' not found"
    except Exception as e:
        return f"Error editing file: {e}"

def bash(command: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = ""
        if result.stdout:
            output += f"[stdout]\n{result.stdout}"
        if result.stderr:
            output += f"[stderr]\n{result.stderr}"
        if result.returncode != 0 and not output:
            output = f"Command exited with code {result.returncode}"
        return output if output else "Command executed successfully (no output)"
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"

def run_python(file_path: str, expected_output: str, test_input: str = None) -> str:
    try:
        if not file_path.endswith(".py"):
            return "Error: run_python requires a .py file"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        result = subprocess.run(
            ["python", file_path],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=30
        )

        actual_output = result.stdout + result.stderr

        if expected_output in actual_output:
            return f"✓ Verification passed! Output contains expected substring '{expected_output}'\n\n[stdout]\n{result.stdout}\n[stderr]\n{result.stderr}"
        else:
            return f"✗ Verification failed! Expected '{expected_output}' not found in output.\n\n[stdout]\n{result.stdout}\n[stderr]\n{result.stderr}"
    except FileNotFoundError:
        return f"Error: File '{file_path}' not found"
    except subprocess.TimeoutExpired:
        return "Error: Program timed out after 30 seconds"
    except Exception as e:
        return f"Error running Python: {e}"

def execute_tool(tool_name: str, arguments: dict) -> str:
    if tool_name == "read_file":
        return read_file(**arguments)
    elif tool_name == "write_file":
        return write_file(**arguments)
    elif tool_name == "edit_file":
        return edit_file(**arguments)
    elif tool_name == "bash":
        return bash(**arguments)
    elif tool_name == "run_python":
        return run_python(**arguments)
    elif tool_name == "memory_read":
        return memory_read()
    elif tool_name == "memory_write":
        return memory_write(**arguments)
    elif tool_name == "memory_append":
        return memory_append(**arguments)
    elif tool_name == "memory_clear":
        return memory_clear()
    elif tool_name == "create_plan":
        return create_plan(**arguments)
    return f"Unknown tool: {tool_name}"

# ============ Agent Loop ============
def agent_loop(user_message: str, max_iterations: int = 10, planning_mode: bool = False):
    # 读取记忆并构建 system prompt
    memory_content = memory_read()

    planning_instruction = """IMPORTANT: For complex tasks, use create_plan FIRST before using other tools.
Break down the task into clear, ordered steps. After creating the plan,
execute each step using appropriate tools in order.""" if planning_mode else ""

    system_prompt = f"""You are a helpful coding assistant with file operation and bash tools.
{memory_content}

{planning_instruction}


Available tools:
- read_file(path): Read a file's content
- write_file(path, content): Write content to a file (creates or overwrites)
- edit_file(path, old_string, new_string): Replace text in a file (old_string must match exactly)
- bash(command, timeout?): Execute a bash command and return the output
- run_python(file_path, expected_output, test_input?): Run a Python file and verify output contains expected substring
- memory_read(): Read the agent's long-term memory from previous sessions
- memory_write(content): Write important information to long-term memory (overwrites previous memory)
- memory_append(text): Append new information to existing memory
- memory_clear(): Clear all memory (use with caution)
- create_plan(task, steps): Create a structured plan BEFORE taking any action

When writing Python programs:
1. Use write_file to create the .py file
2. Use run_python to execute and verify with expected_output
3. If verification fails, edit and try again

Important memory guidelines:
- Use memory_write or memory_append to save important context, decisions, or progress
- If the user asks you to remember something, use memory_write immediately
- When starting a task related to previous work, use memory_read first to check context
- memory_clear should only be used when explicitly requested or when memory is no longer relevant

Be careful with edit_file - the old_string must match exactly. Use read_file first if unsure."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    print(f"[Memory] Current memory:\n{memory_read()[:200]}...\n")

    for i in range(max_iterations):
        response = client.chat.completions.create(
            model="MiniMax-M2.7",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            extra_body={"reasoning_split": True}
        )

        assistant_message = response.choices[0].message

        if assistant_message.reasoning_details:
            print(f"[Think] {assistant_message.reasoning_details[0]['text'][:200]}...")

        if assistant_message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in assistant_message.tool_calls
                ]
            })

            for tc in assistant_message.tool_calls:
                tool_name = tc.function.name
                arguments = json.loads(tc.function.arguments)
                print(f"\n[Tool] Calling {tool_name} with {arguments}")
                result = execute_tool(tool_name, arguments)
                print(f"[Result] {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })
        else:
            print(f"\n[Final Response] {assistant_message.content}")
            return assistant_message.content

    return "Max iterations reached"

# ============ 规划状态 ============
current_plan = {
    "task": "",
    "steps": [],
    "current_step": 0
}

def create_plan(task: str, steps: list) -> str:
    """Save a plan for the current task"""
    current_plan["task"] = task
    current_plan["steps"] = steps
    current_plan["current_step"] = 0

    plan_text = "\n".join([f"{i+1}. {s}" for i, s in enumerate(steps)])
    return f"Plan created for '{task}':\n{plan_text}"

# ============ 主程序 ============
if __name__ == "__main__":
    import sys

    # 解析命令行参数
    planning_mode = False
    task_args = []

    for arg in sys.argv[1:]:
        if arg == "--plan":
            planning_mode = True
        else:
            task_args.append(arg)

    if task_args:
        task = " ".join(task_args)
    else:
        task = input("Enter your task: ")

    print(f"Task: {task}")
    print(f"Planning mode: {'ON' if planning_mode else 'OFF'}\n")

    result = agent_loop(task, planning_mode=planning_mode)
    print(f"\nFinal result: {result}")