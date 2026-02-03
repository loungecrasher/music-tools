#!/usr/bin/env python3
"""
Analyze all Python files for missing imports and other issues.
"""
import ast
from collections import defaultdict
from pathlib import Path
from typing import Dict


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze Python code for imports and undefined names."""

    def __init__(self, filename: str):
        self.filename = filename
        self.imports = set()
        self.from_imports = defaultdict(set)
        self.undefined_names = set()
        self.defined_names = set()
        self.used_names = set()

    def visit_Import(self, node):
        """Track import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.imports.add(name)
            self.defined_names.add(name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from ... import statements."""
        module = node.module or ''
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.from_imports[module].add(name)
            self.defined_names.add(name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Track function definitions."""
        self.defined_names.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track class definitions."""
        self.defined_names.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node):
        """Track name usage."""
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Track assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.defined_names.add(target.id)
        self.generic_visit(node)


def analyze_file(filepath: str) -> Dict:
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=filepath)
        analyzer = ImportAnalyzer(filepath)
        analyzer.visit(tree)

        # Built-in names that don't need imports
        builtins = {
            'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set',
            'tuple', 'range', 'enumerate', 'zip', 'map', 'filter', 'sum', 'max',
            'min', 'abs', 'all', 'any', 'sorted', 'reversed', 'open', 'input',
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'AttributeError',
            'ImportError', 'RuntimeError', 'NotImplementedError', 'IndexError',
            'FileNotFoundError', 'OSError', 'IOError', 'StopIteration',
            'True', 'False', 'None', 'type', 'isinstance', 'hasattr', 'getattr',
            'setattr', 'super', 'property', 'staticmethod', 'classmethod',
            'object', 'repr', 'format', 'iter', 'next', 'bytes', 'bytearray'
        }

        # Find potentially undefined names
        undefined = analyzer.used_names - analyzer.defined_names - builtins

        return {
            'filepath': filepath,
            'imports': analyzer.imports,
            'from_imports': dict(analyzer.from_imports),
            'undefined': undefined,
            'used_names': analyzer.used_names,
            'defined_names': analyzer.defined_names
        }
    except SyntaxError as e:
        return {
            'filepath': filepath,
            'error': f'Syntax error: {e}'
        }
    except Exception as e:
        return {
            'filepath': filepath,
            'error': f'Error: {e}'
        }


def main():
    """Main function."""
    base_dir = Path("/home/claude-flow/projects/ActiveProjects/Music Tools/Music Tools Dev")

    # Directories to analyze
    directories = [
        "Music Tools",
        "Tag Country Origin Editor",
        "EDM Sharing Site Web Scrapper"
    ]

    results = {
        'files_with_issues': [],
        'total_files': 0,
        'files_with_errors': [],
        'files_with_undefined': []
    }

    for directory in directories:
        dir_path = base_dir / directory
        if not dir_path.exists():
            continue

        print(f"\n{'='*60}")
        print(f"Analyzing: {directory}")
        print('='*60)

        for py_file in dir_path.rglob("*.py"):
            results['total_files'] += 1
            analysis = analyze_file(str(py_file))

            relative_path = py_file.relative_to(base_dir)

            if 'error' in analysis:
                results['files_with_errors'].append({
                    'file': str(relative_path),
                    'error': analysis['error']
                })
                print(f"\n❌ {relative_path}")
                print(f"   Error: {analysis['error']}")
            elif analysis.get('undefined'):
                results['files_with_undefined'].append({
                    'file': str(relative_path),
                    'undefined': analysis['undefined']
                })
                print(f"\n⚠️  {relative_path}")
                print(f"   Potentially undefined: {', '.join(sorted(analysis['undefined']))}")

    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Total files analyzed: {results['total_files']}")
    print(f"Files with errors: {len(results['files_with_errors'])}")
    print(f"Files with undefined names: {len(results['files_with_undefined'])}")

    if results['files_with_errors']:
        print("\n\nFiles with errors:")
        for item in results['files_with_errors']:
            print(f"  - {item['file']}: {item['error']}")

    if results['files_with_undefined']:
        print("\n\nFiles with potentially undefined names:")
        for item in results['files_with_undefined'][:20]:  # Show first 20
            print(f"  - {item['file']}")
            print(f"    Missing: {', '.join(sorted(item['undefined']))}")


if __name__ == "__main__":
    main()
