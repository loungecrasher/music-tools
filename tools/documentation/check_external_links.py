#!/usr/bin/env python3
"""
Check external links (sample basis)
"""

import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR

# Load validation results
with open(BASE_DIR / "validation_results.json", "r") as f:
    results = json.load(f)

# Create SSL context that doesn't verify certificates (for testing)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


def check_url(url, timeout=10):
    """Check if URL is accessible"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
            return True, response.getcode()
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"URL Error: {e.reason}"
    except Exception as e:
        return False, f"Error: {str(e)}"


print("=" * 80)
print("CHECKING EXTERNAL LINKS (Sample)")
print("=" * 80)
print()

# Get unique external URLs
external_urls = {}
for link in results["external_links"]["urls"]:
    url = link["url"]
    if url not in external_urls:
        external_urls[url] = []
    external_urls[url].append(link["file"])

print(f"Found {len(external_urls)} unique external URLs")
print()

# Check each URL (sample - first 20)
checked = 0
working = 0
broken = 0

for url in sorted(external_urls.keys()):
    if checked >= 20:
        break

    print(f"Checking: {url[:70]}...")
    is_accessible, status = check_url(url)

    if is_accessible:
        print(f"  ✓ Working ({status})")
        working += 1
    else:
        print(f"  ✗ Failed ({status})")
        broken += 1

    checked += 1

print()
print("=" * 80)
print(f"Sample check: {checked} URLs")
print(f"Working: {working}")
print(f"Failed: {broken}")
print("=" * 80)

# Save summary
summary = {
    "total_unique_urls": len(external_urls),
    "checked": checked,
    "working": working,
    "failed": broken,
    "all_urls": list(external_urls.keys()),
}

with open(BASE_DIR / "external_links_check.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"Results saved to: {BASE_DIR / 'external_links_check.json'}")
