
import requests
from bs4 import BeautifulSoup

url = "https://sharing-db.club/djs-chart/555423_beatport-weekend-picks-2025-week-47/"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(f"\nPage Title Tag: {soup.title.string if soup.title else 'No title'}")
    
    # Check for title candidates
    print("\nChecking for title candidates:")
    for tag in ['h1', 'h2', 'h3']:
        elements = soup.find_all(tag)
        print(f"{tag} elements found: {len(elements)}")
        for el in elements[:3]:
            print(f"  {tag} class={el.get('class', [])}: {el.get_text().strip()[:100]}")

    # Check for date candidates
    print("\nChecking for date candidates:")
    # Common date classes
    for cls in ['date', 'time', 'published', 'entry-date', 'post-date', 'metadata', 'postmeta']:
        elements = soup.select(f'.{cls}')
        print(f"Class '.{cls}' found: {len(elements)}")
        for el in elements[:1]:
            print(f"  Text: {el.get_text().strip()[:100]}")

    # Check for download links
    print("\nChecking for download links:")
    links = soup.find_all('a', href=True)
    print(f"Total links found: {len(links)}")
    
    print("\nFirst 20 links:")
    for l in links[:20]:
        print(f"  {l['href']} (Text: {l.get_text().strip()[:30]})")
        
    dl_candidates = [l['href'] for l in links if any(x in l['href'] for x in ['zippyshare', 'krakenfiles', 'wetransfer', 'drive.google', 'mega.nz', 'mediafire', 'sendspace', 'turbobit', 'rapidgator', 'uploaded', 'hybeddit', 'hypeddit', 'nfile', 'novafile'])]
    print(f"\nFound {len(dl_candidates)} potential download links (filtered):")
    for l in dl_candidates:
        print(f"  {l}")

    # Check for content container
    print("\nChecking for content container:")
    for selector in ['div.entry', 'div.post', 'article', 'div.content', 'div.entry-content']:
        elements = soup.select(selector)
        print(f"Selector '{selector}' found: {len(elements)}")

except Exception as e:
    print(f"Error: {e}")
