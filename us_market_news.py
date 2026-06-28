"""
Crypto News → Telegram (English)
Fetches crypto headlines from Bloomberg, Financial Times, WSJ
and sends to Telegram daily.
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
import json
import os

# ============================================================
# CONFIG — read from Environment Variables (GitHub Secrets)
# ============================================================
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

RSS_FEEDS = {
    "Bloomberg": "https://feeds.bloomberg.com/crypto/news.rss",
    "Financial Times": "https://news.google.com/rss/search?q=crypto+cryptocurrency+site:ft.com&hl=en-US&gl=US&ceid=US:en",
    "WSJ": "https://news.google.com/rss/search?q=crypto+cryptocurrency+site:wsj.com&hl=en-US&gl=US&ceid=US:en",
}

MAX_ITEMS_PER_SOURCE = 3
CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain",
    "coinbase", "binance", "defi", "nft", "altcoin", "stablecoin",
    "token", "digital asset", "web3", "xrp", "solana", "ripple",
]
# ============================================================


def fetch_rss(name, url):
    headlines = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
        root = tree.getroot()
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)
        count = 0
        for item in items:
            if count >= MAX_ITEMS_PER_SOURCE:
                break
            title = item.findtext("title") or item.findtext("atom:title", namespaces=ns) or ""
            title = title.strip()
            if name != "Bloomberg" and not any(kw in title.lower() for kw in CRYPTO_KEYWORDS):
                continue
            if title:
                headlines.append(title)
                count += 1
        if not headlines:
            headlines.append("(No new crypto headlines today)")
    except Exception as e:
        headlines.append(f"(Error fetching: {e})")
    return headlines


def build_message(all_news):
    today = datetime.now().strftime("%d %b %Y")
    lines = ["\U0001fa99 *Crypto News — " + today + "*\n"]
    emoji_map = {"Bloomberg": "\U0001f535", "Financial Times": "\U0001f7e3", "WSJ": "\U0001f7e0"}
    for source, items in all_news.items():
        lines.append(f"{emoji_map.get(source, '📰')} *{source}*")
        for item in items:
            lines.append(f"• {item}")
        lines.append("")
    lines.append("_Auto-updated daily at 09:00 ICT_")
    return "\n".join(lines)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp).get("ok", False)


def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Crypto news...")
    all_news = {name: fetch_rss(name, url) for name, url in RSS_FEEDS.items()}
    message = build_message(all_news)
    print(message)
    success = send_telegram(message)
    print("Sent OK" if success else "Send FAILED")


if __name__ == "__main__":
    main()
