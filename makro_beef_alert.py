"""
Makro PRO — Beef Discount Alert → Telegram
ตรวจสอบเนื้อวัวลดราคา ≥40% และแจ้งเตือนทาง Telegram
"""

import asyncio
import json
import os
import urllib.request
from datetime import datetime
from playwright.async_api import async_playwright

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
DISCOUNT_THRESHOLD = 40
SEARCH_URL = "https://www.makro.pro/c/search?q=%E0%B9%80%E0%B8%99%E0%B8%B7%E0%B9%89%E0%B8%AD%E0%B8%A7%E0%B8%B1%E0%B8%A7&sortBy=discount"


async def get_beef_deals():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="th-TH",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        await page.goto("https://www.makro.pro", wait_until="domcontentloaded")
        await page.evaluate("""
            localStorage.setItem('postalCode', '10240');
            localStorage.setItem('subDistrict', 'คลองจั่น');
            localStorage.setItem('storeCode', '1090');
        """)

        await page.goto(SEARCH_URL, wait_until="domcontentloaded")

        try:
            await page.wait_for_selector(".isProductCardV2", timeout=15000)
        except Exception:
            print("Timeout waiting for products — site may have changed")
            await browser.close()
            return []

        await page.wait_for_timeout(2000)

        products = await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('.isProductCardV2');
                const results = [];
                cards.forEach(card => {
                    const allLeafs = [...card.querySelectorAll('*')].filter(
                        el => el.children.length === 0
                    );
                    const discLeaf = allLeafs.find(el => /^-\\d+%$/.test(el.textContent.trim()));
                    const discount = discLeaf
                        ? parseInt(discLeaf.textContent.replace('-','').replace('%',''))
                        : 0;

                    if (discount === 0) return;

                    const cardParent = card.closest('a') ||
                                       card.parentElement?.parentElement?.parentElement;
                    const nameEls = cardParent
                        ? [...cardParent.querySelectorAll('*')].filter(el =>
                            el.children.length === 0 &&
                            el.textContent.trim().length > 5 &&
                            el.textContent.trim().length < 120 &&
                            !el.textContent.match(/^-\\d+%$|พอยท์|฿|\\d{2}:\\d{2}/)
                          )
                        : [];

                    const name = nameEls[0]?.textContent.trim() || 'ไม่ทราบชื่อ';
                    results.push({ discount, name });
                });
                return results;
            }
        """)

        await browser.close()
        return products


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = json.dumps({
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp).get("ok", False)


async def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking Makro beef discounts...")
    all_products = await get_beef_deals()
    print(f"Found {len(all_products)} products with discounts")

    deals = [p for p in all_products if p["discount"] >= DISCOUNT_THRESHOLD]

    if deals:
        today = datetime.now().strftime("%d %b %Y")
        lines = [f"🥩 *Makro เนื้อวัวลดราคา >= {DISCOUNT_THRESHOLD}%!* — {today}\n"]
        for p in sorted(deals, key=lambda x: -x["discount"]):
            lines.append(f"• {p['name']} — *ลด {p['discount']}%*")
        lines.append(f"\n-> ดูทั้งหมดที่ Makro PRO: {SEARCH_URL}")
        message = "\n".join(lines)
        ok = send_telegram(message)
        print(f"Alert sent: {ok} ({len(deals)} deals)")
    else:
        max_d = max((p["discount"] for p in all_products), default=0)
        print(f"No deals >= {DISCOUNT_THRESHOLD}% today (max found: {max_d}%)")


if __name__ == "__main__":
    asyncio.run(main())
