import importlib.util
import inspect
import logging
import os
import sys
import textwrap

logger = logging.getLogger(__name__)


def extract_code_blocks(docstring: str) -> list[str]:
    """Extract code blocks from a docstring."""
    code_blocks = []
    in_code_block = False
    code_block = []

    for line in docstring.split("\n"):
        if line.strip().startswith("```python"):
            in_code_block = True
            continue
        elif line.strip().startswith("```"):
            in_code_block = False
            if code_block:
                code_blocks.append("\n".join(code_block))
                code_block = []
            continue

        if in_code_block:
            code_block.append(line)

    return code_blocks


def exec_example(example: str) -> None:
    """Execute a code example."""
    example = textwrap.dedent(example)
    namespace = {"__name__": "__not_main__"}
    try:
        code = compile(example, "<string>", "exec")
        exec(code, namespace)
    except Exception:
        raise Exception(f"Failed to execute example:\n\n{example}")


def process_object(name: str, obj: object, module_name: str, library_name: str) -> None:
    """Process a single object, extracting and executing code examples."""
    docstring = inspect.getdoc(obj)
    if docstring:
        examples = extract_code_blocks(docstring)
        for example in examples:
            exec_example(example)

    # Recursively process class methods only if they belong to the same library
    if inspect.isclass(obj):
        for method_name, method_obj in inspect.getmembers(obj, inspect.isfunction):
            if method_obj.__module__ and method_obj.__module__.startswith(library_name):
                process_object(f"{name}.{method_name}", method_obj, module_name, library_name)


def process_module(module_path: str) -> None:
    """Process a single Python module."""
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise Exception(f"Could not load module: {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    library_name = "aioclock"

    for name, obj in inspect.getmembers(
        module, lambda o: inspect.isfunction(o) or inspect.isclass(o)
    ):
        if obj.__module__ and obj.__module__.startswith(library_name):
            process_object(name, obj, module_name, library_name)


def process_markdown(markdown_path: str) -> None:
    """Process a markdown file and execute code blocks."""
    with open(markdown_path, "r") as file:
        content = file.read()

    code_blocks = extract_code_blocks(content)
    for example in code_blocks:
        exec_example(example)


def traverse_library(library_path: str) -> None:
    """Traverse the library directory and process each Python module."""
    original_sys_path = sys.path.copy()
    sys.path.insert(0, os.path.abspath(library_path))  # Prioritize the library path

    for root, _, files in os.walk(library_path):
        for file in files:
            if file.endswith(".py"):
                module_path = os.path.join(root, file)
                process_module(module_path)

    sys.path = original_sys_path  # Restore the original sys.path


def traverse_docs(docs_path: str) -> None:
    """Traverse the docs directory and process each markdown file."""
    for root, _, files in os.walk(docs_path):
        for file in files:
            if file.endswith(".md"):
                markdown_path = os.path.join(root, file)
                process_markdown(markdown_path)


def test_examples():
    docs_path = "../aioclock/docs"
    traverse_docs(docs_path)

    library_path = "../aioclock/aioclock"
    traverse_library(library_path)
