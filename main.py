from openai import OpenAI
import json
import subprocess

client = OpenAI()

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
    }
]

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
    return f"Unknown tool: {tool_name}"

def agent_loop(user_message: str, max_iterations: int = 10):
    messages = [
        {"role": "system", "content": """You are a helpful coding assistant with file operation and bash tools.
Available tools:
- read_file(path): Read a file's content
- write_file(path, content): Write content to a file (creates or overwrites)
- edit_file(path, old_string, new_string): Replace text in a file (old_string must match exactly)
- bash(command, timeout?: number): Execute a bash command and return the output
- run_python(file_path, expected_output, test_input?): Run a Python file and verify output contains expected substring

When writing Python programs:
1. Use write_file to create the .py file
2. Use run_python to execute and verify with expected_output
3. If verification fails, edit and try again

Be careful with edit_file - the old_string must match exactly. Use read_file first if unsure."""},
        {"role": "user", "content": user_message}
    ]

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

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = "Create a file called hello.txt with content 'Hello, World!' and then read it to confirm"

    print(f"Task: {task}\n")
    result = agent_loop(task)
    print(f"\nFinal result: {result}")