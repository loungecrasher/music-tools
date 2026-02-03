# Documentation Validation Tools

This directory contains automated tools for validating the Music Tools documentation.

## Quick Start

**Note:** All scripts now use relative paths and are fully portable. Run them from the project root directory.

```bash
# Run complete validation
python3 validate_docs.py

# Analyze results
python3 analyze_validation.py

# Check external links
python3 check_external_links.py

# Fix broken links (use with caution)
python3 fix_broken_links.py
```

## Available Tools

### 1. validate_docs.py
**Purpose:** Main validation engine - extracts and validates all documentation links

**What it does:**
- Scans all markdown files in `docs/`
- Extracts all markdown links `[text](url)`
- Validates internal links point to existing files
- Identifies external links
- Checks code file references
- Finds TODO markers and "coming soon" sections

**Output:** `validation_results.json` (complete validation data)

**Runtime:** ~30 seconds

### 2. analyze_validation.py
**Purpose:** Analyzes validation results and creates human-readable summary

**What it does:**
- Reads `validation_results.json`
- Summarizes link statistics
- Groups broken links by pattern
- Identifies most common issues
- Shows sample of problems

**Output:**
- Console output with formatted report
- `validation_summary.json` (summary statistics)

**Runtime:** <1 second

### 3. check_external_links.py
**Purpose:** Verifies external links are accessible

**What it does:**
- Checks HTTP/HTTPS accessibility
- Tests 20 URLs (sample basis)
- Reports success/failure rate
- Identifies dead links

**Output:** `external_links_check.json`

**Runtime:** ~20 seconds (depends on network)

**Note:** Some sites block bots (403 errors), these may work in browsers

### 4. fix_broken_links.py
**Purpose:** Automatically fixes common broken link patterns

**What it does:**
- Identifies fixable broken links
- Updates paths to correct locations
- Converts unfixable links to "coming soon" text
- Creates backup before modifying files

**Output:** `link_fixes_report.json`

**Runtime:** ~5 seconds

**Caution:** Review changes before committing!

## Validation Results

After running validation, you'll have these files:

```
validation_results.json       # Complete validation data (large)
validation_summary.json       # Summary statistics
external_links_check.json    # External link check results
link_fixes_report.json       # Applied fixes log
```

## Typical Workflow

### Regular Validation
```bash
# Step 1: Validate
python3 validate_docs.py

# Step 2: Review results
python3 analyze_validation.py
```

### After Documentation Changes
```bash
# Step 1: Validate
python3 validate_docs.py

# Step 2: Check if fixes needed
python3 analyze_validation.py

# Step 3: Apply automatic fixes (if needed)
python3 fix_broken_links.py

# Step 4: Re-validate
python3 validate_docs.py

# Step 5: Verify improvements
python3 analyze_validation.py
```

### Before Release
```bash
# Full validation including external links
python3 validate_docs.py
python3 analyze_validation.py
python3 check_external_links.py

# Review all reports
cat validation_summary.json
cat external_links_check.json
```

## Interpreting Results

### Link Success Rate
- **90%+:** Excellent
- **70-89%:** Good (check what's broken)
- **50-69%:** Needs attention
- **<50%:** Critical issues

### Common Broken Link Types

1. **Planned Documentation:** Links to docs marked "coming soon" - expected
2. **Archive References:** Historical links - may be intentional
3. **Invalid Patterns:** Placeholders like "link" or "path" - need fixing
4. **Moved Files:** Old paths - should be fixed

### External Link Failures

Common reasons:
- **403 Forbidden:** Bot protection (may work in browsers)
- **404 Not Found:** Dead link (needs updating)
- **Timeout:** Slow server (may work on retry)
- **Connection Error:** Network issue or dead domain

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Validate Documentation

on:
  pull_request:
    paths:
      - 'docs/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Validate Documentation
        run: |
          python3 validate_docs.py
          python3 analyze_validation.py

      - name: Check Link Success Rate
        run: |
          # Parse validation_summary.json and fail if <70%
          python3 -c "
          import json
          with open('validation_summary.json') as f:
              data = json.load(f)
          total = data['internal_links_working'] + data['internal_links_broken']
          rate = data['internal_links_working'] / total * 100
          print(f'Link success rate: {rate:.1f}%')
          if rate < 70:
              exit(1)
          "
```

### Pre-commit Hook Example

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Check if any docs changed
if git diff --cached --name-only | grep -q '^docs/'; then
    echo "Validating documentation..."
    python3 validate_docs.py
    python3 analyze_validation.py

    # Check if validation passed
    if [ $? -ne 0 ]; then
        echo "Documentation validation failed!"
        exit 1
    fi
fi
```

## Customization

### Adding Link Fix Rules

Edit `fix_broken_links.py` and add to `LINK_FIXES` dictionary:

```python
LINK_FIXES = {
    # Add your custom fix rules
    "old/path.md": "new/path.md",
    "broken/link.md": None,  # Remove link (mark as coming soon)
}
```

### Adjusting Validation

Edit `validate_docs.py` to:
- Change docs directory: Update `DOCS_DIR`
- Add file patterns: Modify `*.md` glob
- Skip directories: Add to exclusion list

### External Link Sampling

Edit `check_external_links.py` to:
- Check more/fewer URLs: Change `if checked >= 20`
- Adjust timeout: Modify `timeout=10` parameter
- Change user agent: Update request headers

## Maintenance

### Regular Tasks
- Run validation weekly
- Check external links monthly
- Review "coming soon" markers quarterly
- Update fix rules as structure changes

### After Major Changes
- Monorepo restructuring: Full validation required
- Documentation reorganization: Re-validate all links
- New section added: Validate cross-references
- Archive creation: Validate archive links

## Troubleshooting

### "File not found" errors
- Check file paths are absolute
- Verify you're in project root
- Ensure docs/ directory exists

### "Permission denied"
- Make scripts executable: `chmod +x *.py`
- Check file ownership

### Large validation_results.json
- This is normal (contains all link data)
- Use analyze_validation.py for summaries
- Can be added to .gitignore if needed

### False positive broken links
- Check if path is relative vs absolute
- Verify anchor links (not validated)
- Review path resolution logic

## Help and Support

### Documentation
- See `docs/VALIDATION_REPORT.md` for latest results
- See `docs/DOCUMENTATION_CLEANUP_COMPLETE.md` for process overview

### Questions
- Review validation script comments
- Check validation report recommendations
- Consult `docs/guides/developer/contributing.md`

## Version History

- **v1.1 (2025-11-19):** Scripts now use relative paths
  - Replaced hardcoded absolute paths with `Path(__file__).parent.resolve()`
  - Scripts are now fully portable across systems
  - No system-specific paths required
  - Works from any location when run from project root

- **v1.0 (2025-11-19):** Initial validation tools created
  - Complete link validation
  - External link checking
  - Automated fixing
  - Comprehensive reporting

---

**Last Updated:** 2025-11-19
**Status:** Production Ready
**Maintainer:** Documentation Team
