#!/usr/bin/env python3
"""
Documentation Validation Script
Validates all markdown links, cross-references, and technical accuracy
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

# Base directory - use relative path from script location
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR
DOCS_DIR = BASE_DIR / "docs"

# Results storage
results = {
    "total_files": 0,
    "total_links": 0,
    "internal_links": {"total": 0, "working": [], "broken": []},
    "external_links": {"total": 0, "urls": []},
    "cross_references": {"total": 0, "valid": [], "invalid": []},
    "code_references": {"total": 0, "valid": [], "invalid": []},
    "todos_found": [],
    "coming_soon": [],
    "formatting_issues": [],
    "files_processed": [],
}


def extract_links_from_file(file_path):
    """Extract all markdown links from a file"""
    links = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find markdown links: [text](url)
        link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
        matches = re.findall(link_pattern, content)

        for text, url in matches:
            links.append(
                {"text": text, "url": url, "line": None}  # Could enhance to track line numbers
            )

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return links


def is_external_url(url):
    """Check if URL is external (http/https)"""
    return url.startswith("http://") or url.startswith("https://")


def is_anchor_link(url):
    """Check if URL is just an anchor (#section)"""
    return url.startswith("#")


def resolve_relative_path(current_file, link_url):
    """Resolve relative path from current file to linked file"""
    # Remove anchor if present
    link_url = link_url.split("#")[0]
    if not link_url:
        return None

    current_dir = Path(current_file).parent

    # Handle absolute paths from docs root
    if link_url.startswith("/"):
        target_path = DOCS_DIR / link_url[1:]
    else:
        # Relative path
        target_path = current_dir / link_url

    # Normalize path
    try:
        target_path = target_path.resolve()
    except:
        return None

    return target_path


def validate_internal_link(current_file, link_url):
    """Validate an internal link points to existing file"""
    target_path = resolve_relative_path(current_file, link_url)

    if target_path is None:
        return False, "Could not resolve path"

    if target_path.exists():
        return True, str(target_path)
    else:
        return False, f"File not found: {target_path}"


def find_todos_and_coming_soon(file_path):
    """Find TODO markers and 'coming soon' sections"""
    todos = []
    coming_soon = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Look for TODO markers
            if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", line, re.IGNORECASE):
                todos.append({"file": str(file_path), "line": i, "content": line.strip()})

            # Look for "coming soon"
            if re.search(r"coming soon", line, re.IGNORECASE):
                coming_soon.append({"file": str(file_path), "line": i, "content": line.strip()})

    except Exception as e:
        print(f"Error scanning {file_path}: {e}")

    return todos, coming_soon


def check_code_references(file_path):
    """Check for references to code files"""
    code_refs = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for patterns like "in file.py" or "file.py line 45"
        patterns = [
            r"`([a-zA-Z0-9_\-/]+\.py)`",
            r"`([a-zA-Z0-9_\-/]+\.js)`",
            r"`([a-zA-Z0-9_\-/]+\.ts)`",
            r"\b([a-zA-Z0-9_\-/]+\.py)\s+line\s+\d+",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                code_refs.append(match)

    except Exception as e:
        print(f"Error checking code refs in {file_path}: {e}")

    return code_refs


def validate_code_file(code_path):
    """Check if a referenced code file exists"""
    # Try various locations
    possible_paths = [
        BASE_DIR / code_path,
        BASE_DIR / "apps" / "music-tools" / code_path,
        BASE_DIR / "packages" / "common" / code_path,
    ]

    for path in possible_paths:
        if path.exists():
            return True, str(path)

    return False, None


def main():
    """Main validation process"""
    print("=" * 80)
    print("Documentation Validation Process")
    print("=" * 80)
    print()

    # Get all markdown files
    md_files = list(DOCS_DIR.rglob("*.md"))
    results["total_files"] = len(md_files)

    print(f"Found {len(md_files)} markdown files in docs/")
    print()

    # Process each file
    for md_file in md_files:
        rel_path = md_file.relative_to(BASE_DIR)
        print(f"Processing: {rel_path}")
        results["files_processed"].append(str(rel_path))

        # Extract links
        links = extract_links_from_file(md_file)
        results["total_links"] += len(links)

        # Validate each link
        for link in links:
            url = link["url"]

            if is_external_url(url):
                # External link
                results["external_links"]["total"] += 1
                results["external_links"]["urls"].append(
                    {"file": str(rel_path), "url": url, "text": link["text"]}
                )

            elif is_anchor_link(url):
                # Anchor link - skip for now
                pass

            else:
                # Internal link
                results["internal_links"]["total"] += 1
                is_valid, message = validate_internal_link(md_file, url)

                if is_valid:
                    results["internal_links"]["working"].append(
                        {"file": str(rel_path), "url": url, "target": message}
                    )
                else:
                    results["internal_links"]["broken"].append(
                        {"file": str(rel_path), "url": url, "error": message}
                    )

        # Find TODOs and coming soon
        todos, coming_soon = find_todos_and_coming_soon(md_file)
        results["todos_found"].extend(todos)
        results["coming_soon"].extend(coming_soon)

        # Check code references
        code_refs = check_code_references(md_file)
        for code_ref in code_refs:
            results["code_references"]["total"] += 1
            is_valid, path = validate_code_file(code_ref)

            if is_valid:
                results["code_references"]["valid"].append(
                    {"file": str(rel_path), "reference": code_ref, "resolved": path}
                )
            else:
                results["code_references"]["invalid"].append(
                    {"file": str(rel_path), "reference": code_ref}
                )

    # Save results
    output_file = BASE_DIR / "validation_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print()
    print("=" * 80)
    print("Validation Complete!")
    print("=" * 80)
    print()
    print(f"Files processed: {results['total_files']}")
    print(f"Total links: {results['total_links']}")
    print(f"Internal links: {results['internal_links']['total']}")
    print(f"  - Working: {len(results['internal_links']['working'])}")
    print(f"  - Broken: {len(results['internal_links']['broken'])}")
    print(f"External links: {results['external_links']['total']}")
    print(f"Code references: {results['code_references']['total']}")
    print(f"  - Valid: {len(results['code_references']['valid'])}")
    print(f"  - Invalid: {len(results['code_references']['invalid'])}")
    print(f"TODOs found: {len(results['todos_found'])}")
    print(f"'Coming soon' found: {len(results['coming_soon'])}")
    print()
    print(f"Results saved to: {output_file}")

    return results


if __name__ == "__main__":
    main()
