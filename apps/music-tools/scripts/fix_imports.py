#!/usr/bin/env python3
"""
Automatically fix missing imports in Python files.
"""

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Map of common undefined names to their import statements
IMPORT_MAP = {
    # Standard library - basic
    "os": "import os",
    "sys": "import sys",
    "json": "import json",
    "re": "import re",
    "time": "import time",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "Path": "from pathlib import Path",
    "defaultdict": "from collections import defaultdict",
    "Counter": "from collections import Counter",
    "OrderedDict": "from collections import OrderedDict",
    "argparse": "import argparse",
    "subprocess": "import subprocess",
    "shutil": "import shutil",
    "glob": "import glob",
    "csv": "import csv",
    "traceback": "import traceback",
    "logging": "import logging",
    "sqlite3": "import sqlite3",
    "importlib": "import importlib",
    # Typing imports
    "Dict": "from typing import Dict",
    "List": "from typing import List",
    "Set": "from typing import Set",
    "Tuple": "from typing import Tuple",
    "Optional": "from typing import Optional",
    "Any": "from typing import Any",
    "Union": "from typing import Union",
    "Callable": "from typing import Callable",
    "TypeVar": "from typing import TypeVar",
    "Iterable": "from typing import Iterable",
    # Third-party
    "requests": "import requests",
    "spotipy": "import spotipy",
    "dotenv": "from dotenv import load_dotenv",
    "load_dotenv": "from dotenv import load_dotenv",
    "pytest": "import pytest",
    "BeautifulSoup": "from bs4 import BeautifulSoup",
    "mutagen": "import mutagen",
    "click": "import click",
    # Error types
    "ConnectionError": "",  # Built-in
    "TimeoutError": "",  # Built-in
    "PermissionError": "",  # Built-in
    "FileNotFoundError": "",  # Built-in
    "NotADirectoryError": "",  # Built-in
    "UnicodeDecodeError": "",  # Built-in
    "UnicodeError": "",  # Built-in
}


class ImportFixer:
    """Fix missing imports in Python files."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.content = ""
        self.lines = []
        self.imports = set()
        self.from_imports = defaultdict(set)
        self.missing_imports = set()

    def read_file(self):
        """Read the file content."""
        with open(self.file_path, "r", encoding="utf-8") as f:
            self.content = f.read()
            self.lines = self.content.split("\n")

    def analyze_imports(self):
        """Analyze existing imports."""
        try:
            tree = ast.parse(self.content, filename=self.file_path)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        self.imports.add(name)

                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        self.from_imports[module].add(name)

        except SyntaxError:
            print(f"  Syntax error in {self.file_path}")
            return False
        return True

    def find_missing_imports(self) -> Set[str]:
        """Find names that need imports."""
        missing = set()

        # Check for common patterns that need imports
        patterns = {
            r"\bos\.": "os",
            r"\bsys\.": "sys",
            r"\bjson\.": "json",
            r"\bre\.": "re",
            r"\btime\.": "time",
            r"\bPath\(": "Path",
            r"\bdatetime\.": "datetime",
            r"\bdefaultdict\(": "defaultdict",
            r"\bargparse\.": "argparse",
            r"\bsubprocess\.": "subprocess",
            r"\blogging\.": "logging",
            r"\bsqlite3\.": "sqlite3",
            r"\brequests\.": "requests",
            r"\bspotipy\.": "spotipy",
            r"\bcsv\.": "csv",
            r"\btraceback\.": "traceback",
            r"\bimportlib\.": "importlib",
        }

        for pattern, module in patterns.items():
            if re.search(pattern, self.content):
                # Check if already imported
                if module not in self.imports and module not in self.from_imports:
                    missing.add(module)

        return missing

    def add_import(self, import_name: str) -> bool:
        """Add a missing import to the file."""
        if import_name not in IMPORT_MAP:
            return False

        import_statement = IMPORT_MAP[import_name]
        if not import_statement:  # Empty means it's a built-in
            return False

        # Find the right place to add the import
        insert_pos = 0
        in_docstring = False
        shebang_line = False

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # Skip shebang
            if i == 0 and stripped.startswith("#!"):
                shebang_line = True
                continue

            # Skip module docstring
            if i == (1 if shebang_line else 0) and (
                stripped.startswith('"""') or stripped.startswith("'''")
            ):
                in_docstring = True
                continue

            if in_docstring and (stripped.endswith('"""') or stripped.endswith("'''")):
                in_docstring = False
                insert_pos = i + 1
                continue

            # Skip comments and blank lines at the top
            if stripped.startswith("#") or not stripped:
                continue

            # Found first non-comment, non-blank line
            if not stripped.startswith("import") and not stripped.startswith("from"):
                insert_pos = i
                break

            # If we're already in imports, find the end
            if stripped.startswith("import") or stripped.startswith("from"):
                insert_pos = i + 1

        # Check if import already exists
        if import_statement in self.lines:
            return False

        # Add the import
        self.lines.insert(insert_pos, import_statement)
        return True

    def fix_file(self) -> Tuple[bool, List[str]]:
        """Fix missing imports in the file."""
        self.read_file()

        if not self.analyze_imports():
            return False, []

        missing = self.find_missing_imports()
        if not missing:
            return False, []

        added = []
        for import_name in sorted(missing):
            if self.add_import(import_name):
                added.append(import_name)

        if added:
            # Write the fixed content
            new_content = "\n".join(self.lines)
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True, added

        return False, []


def fix_directory(directory: Path, pattern: str = "**/*.py") -> Dict[str, List[str]]:
    """Fix all Python files in a directory."""
    results = {}

    for py_file in directory.glob(pattern):
        if py_file.is_file():
            fixer = ImportFixer(str(py_file))
            try:
                fixed, added = fixer.fix_file()
                if fixed:
                    results[str(py_file.relative_to(directory.parent))] = added
            except Exception as e:
                print(f"Error fixing {py_file}: {e}")

    return results


def main():
    """Main function."""
    base_dir = Path("/home/claude-flow/projects/ActiveProjects/Music Tools/Music Tools Dev")

    directories = ["Music Tools", "Tag Country Origin Editor", "EDM Sharing Site Web Scrapper"]

    all_results = {}

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"\n{'='*60}")
        print(f"Fixing: {directory}")
        print("=" * 60)

        results = fix_directory(dir_path)

        if results:
            all_results.update(results)
            for file, imports in results.items():
                print(f"\n✓ {file}")
                for imp in imports:
                    print(f"  + {IMPORT_MAP[imp]}")
        else:
            print("  No fixes needed")

    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files fixed: {len(all_results)}")

    if all_results:
        print("\nFiles modified:")
        for file in sorted(all_results.keys()):
            print(f"  - {file}")


if __name__ == "__main__":
    main()
