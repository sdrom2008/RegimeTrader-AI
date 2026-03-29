import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import html

def fetch_crypto_rss():
    print("📰 Fetching latest Crypto News from Top Publishers...")
    feeds = [
        ("CoinTelegraph", "https://cointelegraph.com/rss"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/")
    ]
    
    news_items = []
    
    for source, url in feeds:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                # Parse RSS items (limit to top 5 from each)
                count = 0
                for item in root.findall('.//item'):
                    if count >= 10:
                        break
                    title = item.find('title').text
                    pub_date = item.find('pubDate').text
                    # Clean up HTML entities in title
                    clean_title = html.unescape(title)
                    news_items.append({"source": source, "title": clean_title, "date": pub_date})
                    count += 1
        except Exception as e:
            print(f"Error fetching from {source}: {e}")
            
    print(f"\n✅ Successfully fetched {len(news_items)} recent headlines:\n")
    for i, news in enumerate(news_items, 1):
        print(f"{i}. [{news['source']}] {news['title']}")
        
    return news_items

if __name__ == "__main__":
    fetch_crypto_rss()
