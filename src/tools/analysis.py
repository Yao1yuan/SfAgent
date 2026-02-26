from langchain_core.tools import tool
from tree_sitter import Language, Parser
import tree_sitter_python
import src.tools.base as base

# Initialize Tree-sitter for Python
try:
    PY_LANGUAGE = Language(tree_sitter_python.language())
    parser = Parser(PY_LANGUAGE)
except Exception as e:
    # Fallback or error if initialization fails
    PY_LANGUAGE = None
    parser = None
    print(f"Warning: Failed to initialize tree-sitter: {e}")

@tool
def analyze_code_structure(path: str) -> str:
    """
    Analyze the structure of a Python file using AST (Tree-sitter).
    Returns a skeletal outline (Classes, Methods, Functions) without implementation details.
    Args:
        path: Relative path to the file to analyze.
    """
    if not parser:
        return "Error: Tree-sitter parser not initialized."

    target_path = (base.PROJECT_ROOT / path).resolve()

    if not base.is_safe_path(target_path):
        return f"Error: Access denied. Path must be within project root: {base.PROJECT_ROOT}"

    if not target_path.exists():
        return f"Error: File not found: {path}"

    if not target_path.is_file():
        return f"Error: Not a file: {path}"

    try:
        content = target_path.read_text(encoding="utf-8")
        tree = parser.parse(bytes(content, "utf8"))

        # Traverse and build outline
        cursor = tree.walk()

        outline = []

        def traverse(node, depth=0):
            indent = "  " * depth

            if node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    outline.append(f"{indent}class {name}:")

                    # Process body
                    body_node = node.child_by_field_name("body")
                    if body_node:
                        for child in body_node.children:
                            traverse(child, depth + 1)

            elif node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                params_node = node.child_by_field_name("parameters")

                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    params = ""
                    if params_node:
                        params = content[params_node.start_byte:params_node.end_byte]

                    outline.append(f"{indent}def {name}{params}: ...")

            # For module level functions/classes, we need to iterate children if it's the module
            elif node.type == "module":
                for child in node.children:
                    traverse(child, depth)

        traverse(tree.root_node)

        return "\n".join(outline) if outline else "(No classes or functions found)"

    except Exception as e:
        return f"Error analyzing code: {str(e)}"
