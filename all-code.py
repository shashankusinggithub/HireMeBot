import os
import fnmatch


def should_ignore(path):
    ignore_patterns = [
        "*node_modules*",
        "*all-code*",
        "*aggregated_code*",
        "*.git*",
        "*venv*",
        "*.vscode*",
        "*__pycache__*",
        "*build*",
        "*dist*",
        "*public*",
        "*static*",
        "*templates*",
        "*__pycache__*",
        "*migrations*",
        "*pytest_cache*",
    ]
    return any(fnmatch.fnmatch(path, pattern) for pattern in ignore_patterns)


def get_file_structure(start_path):
    structure = []
    for root, dirs, files in os.walk(start_path):
        if should_ignore(root):
            continue
        level = root.replace(start_path, "").count(os.sep)
        indent = " " * 4 * level
        structure.append(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 4 * (level + 1)
        for file in files:
            if not should_ignore(file):
                structure.append(f"{sub_indent}{file}")
    return "\n".join(structure)


def aggregate_code(start_path):
    aggregated_code = []
    for root, dirs, files in os.walk(start_path):
        if should_ignore(root):
            continue
        for file in files:
            if file.endswith(
                (
                    ".py",
                    ".js",
                    ".html",
                    ".css",
                    ".java",
                    ".cpp",
                    ".h",
                    ".ts",
                    ".tsx",
                    ".prisma",
                    "yml",
                    "md",
                    "package.json",
                    "config",
                    "file",
                )
            ):  # Add or remove extensions as needed
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, start_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        aggregated_code.append(
                            f"\n\n{'='*80}\nFile: {relative_path}\n{'='*80}\n\n{content}"
                        )
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    return "".join(aggregated_code)


def main():
    start_path = "."  # Current directory, change this if needed
    output_file = "aggregated_code.txt"

    print("Generating file structure...")
    file_structure = get_file_structure(start_path)

    print("Aggregating code...")
    aggregated_code = aggregate_code(start_path)

    print(f"Writing to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Project Structure:\n\n")
        f.write(file_structure)
        f.write("\n\nAggregated Code:\n")
        f.write(aggregated_code)

    print("Done!")


if __name__ == "__main__":
    main()
