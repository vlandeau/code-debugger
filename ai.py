import subprocess
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text


console = Console()
load_dotenv()


@tool
def modify_file_content(file_name: str, new_content: str) -> None:
    """Change file content with given content."""
    console.print(Panel(f"Changing content of file {file_name} to:", style="purple", expand=False))
    console.print(Syntax(new_content, "python"))
    write_file_content(file_name, new_content)


def write_file_content(file_name: str, new_content: str) -> None:
    current_path = Path(__file__).parent.absolute()
    with open(current_path / file_name, "w") as file:
        file.write(new_content)


def get_file_content(file_name: str) -> str:
    current_path = Path(__file__).parent.absolute()
    with open(current_path / file_name, "r") as file:
        return file.read()


def run_tests() -> (bool, str):
    current_path = Path(__file__).parent.absolute()
    tests_results = subprocess.run(
        f"cd {current_path} && poetry run pytest test_utils.py",
        shell=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    return tests_results.returncode == 0, tests_results.stdout


def fix_code(remaining_retries: int = 5, iteration: int = 1):
    if remaining_retries == 0:
        console.print(Panel("Failed to fix the code. Please fix it manually.", style="red", expand=False))
        return
    tests_success, tests_error = run_tests()
    if tests_success:
        console.print(Panel("Tests passed successfully!", style="green", expand=False))
        return
    else:
        console.print(Panel(f"Tests are failing with the following error on iteration {iteration}:", style="yellow",
                            expand=False))
        console.print(Syntax(tests_error, "python"))
        console.print(
            Text(f"Trying to fix them ({remaining_retries} retries remaining)", style="blue", justify="center"))

        llm = ChatOpenAI(model="gpt-4o")
        llm_with_tools = llm.bind_tools([modify_file_content])

        chain = llm_with_tools | (lambda x: x.tool_calls[0]["args"]) | modify_file_content

        code_content = get_file_content("utils.py")
        tests_content = get_file_content("test_utils.py")
        chain.invoke(f"""The tests of our program are currently failing..
Our program currently contains two files : "utils.py" and "test_utils.py".
The file "utils.py" contains the following code:
```python
{code_content}
```
The file "test_utils.py" contains the following code:
```python
{tests_content}
```

The tests are failing with the following error message:
```
{tests_error}
```

Please fix the tests so that they pass.
""")
        fix_code(remaining_retries - 1, iteration + 1)


if __name__ == "__main__":
    initial_code = get_file_content("utils.py")
    initial_tests = get_file_content("test_utils.py")
    try:
        console.print(Panel("Starting to check and fix the code", style="blue", expand=False))
        fix_code()
    finally:
        write_file_content("utils.py", initial_code)
        write_file_content("test_utils.py", initial_tests)
