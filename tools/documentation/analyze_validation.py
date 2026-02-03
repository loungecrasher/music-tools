#!/usr/bin/env python3
"""
Analyze validation results and create summary
"""

import json
from pathlib import Path
from collections import defaultdict

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR

# Load results
with open(BASE_DIR / "validation_results.json", 'r') as f:
    results = json.load(f)

print("=" * 80)
print("VALIDATION RESULTS ANALYSIS")
print("=" * 80)
print()

# Summary
print("## SUMMARY")
print(f"Files processed: {results['total_files']}")
print(f"Total links found: {results['total_links']}")
print()

# Internal Links
print("## INTERNAL LINKS")
print(f"Total: {results['internal_links']['total']}")
print(f"Working: {len(results['internal_links']['working'])} ({len(results['internal_links']['working'])/results['internal_links']['total']*100:.1f}%)")
print(f"Broken: {len(results['internal_links']['broken'])} ({len(results['internal_links']['broken'])/results['internal_links']['total']*100:.1f}%)")
print()

if results['internal_links']['broken']:
    print("### BROKEN INTERNAL LINKS (Sample):")
    # Group by file
    by_file = defaultdict(list)
    for link in results['internal_links']['broken']:
        by_file[link['file']].append(link['url'])

    for file, urls in sorted(by_file.items())[:10]:
        print(f"\n{file}:")
        for url in urls[:5]:
            print(f"  - {url}")
    print()

# External Links
print("## EXTERNAL LINKS")
print(f"Total: {results['external_links']['total']}")
print()
print("### External URLs (Sample):")
unique_domains = set()
for link in results['external_links']['urls'][:20]:
    from urllib.parse import urlparse
    domain = urlparse(link['url']).netloc
    unique_domains.add(domain)
for domain in sorted(unique_domains):
    print(f"  - {domain}")
print()

# Code References
print("## CODE REFERENCES")
print(f"Total: {results['code_references']['total']}")
print(f"Valid: {len(results['code_references']['valid'])} ({len(results['code_references']['valid'])/results['code_references']['total']*100:.1f}%)")
print(f"Invalid: {len(results['code_references']['invalid'])} ({len(results['code_references']['invalid'])/results['code_references']['total']*100:.1f}%)")
print()

if results['code_references']['invalid']:
    print("### INVALID CODE REFERENCES (Sample):")
    invalid_refs = defaultdict(int)
    for ref in results['code_references']['invalid']:
        invalid_refs[ref['reference']] += 1

    for ref, count in sorted(invalid_refs.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  - {ref} ({count} occurrences)")
    print()

# TODOs
print("## TODOs AND INCOMPLETE SECTIONS")
print(f"TODO markers found: {len(results['todos_found'])}")
print(f"'Coming soon' sections: {len(results['coming_soon'])}")
print()

if results['todos_found']:
    print("### TODO Markers:")
    for todo in results['todos_found'][:10]:
        print(f"  - {todo['file']}:{todo['line']} - {todo['content'][:80]}")
    print()

if results['coming_soon']:
    print("### 'Coming Soon' Sections (Sample):")
    by_file = defaultdict(int)
    for cs in results['coming_soon']:
        by_file[cs['file']] += 1

    for file, count in sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {file}: {count} sections")
    print()

# Critical Issues
print("=" * 80)
print("CRITICAL ISSUES REQUIRING ATTENTION")
print("=" * 80)
print()

critical_broken_links = [link for link in results['internal_links']['broken']
                         if 'README.md' in link['url'] or 'getting-started' in link['url']]

if critical_broken_links:
    print(f"CRITICAL: {len(critical_broken_links)} broken links to important documentation")
    print()

# Most common broken link patterns
print("## MOST COMMON BROKEN LINK PATTERNS")
broken_patterns = defaultdict(int)
for link in results['internal_links']['broken']:
    # Extract pattern
    if '/' in link['url']:
        pattern = link['url'].split('/')[0]
    else:
        pattern = link['url']
    broken_patterns[pattern] += 1

for pattern, count in sorted(broken_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
    print(f"  - {pattern}*: {count} broken links")
print()

# Save summary
summary = {
    "total_files": results['total_files'],
    "total_links": results['total_links'],
    "internal_links_working": len(results['internal_links']['working']),
    "internal_links_broken": len(results['internal_links']['broken']),
    "external_links": results['external_links']['total'],
    "code_refs_valid": len(results['code_references']['valid']),
    "code_refs_invalid": len(results['code_references']['invalid']),
    "todos_found": len(results['todos_found']),
    "coming_soon": len(results['coming_soon']),
}

with open(BASE_DIR / "validation_summary.json", 'w') as f:
    json.dump(summary, f, indent=2)

print(f"Summary saved to: {BASE_DIR / 'validation_summary.json'}")
