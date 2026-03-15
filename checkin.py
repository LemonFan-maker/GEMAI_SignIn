import asyncio
import os

from playwright.async_api import async_playwright

from config import ACCOUNTS
from browser import run_account
from notify import send_wechat


async def main():
    if not ACCOUNTS:
        print("[!] 请设置环境变量 CHECKIN_CONFIG")
        print('[!] 格式: {"accounts":[{"username":"a@b.com","password":"xxx"}],"webhook_key":"xxx"}')
        return

    headless = os.environ.get("CI") == "true"

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            for account in ACCOUNTS:
                result = await run_account(browser, account)
                results.append(result)
        finally:
            await browser.close()

    print(f"\n{'='*50}")
    print("[*] 签到汇总")
    print(f"{'='*50}")

    lines = []
    for masked, status, balance in results:
        line = f"{masked} {status}，当前余额 {balance}"
        print(f"  {line}")
        lines.append(line)

    send_wechat("哈基米签到通知\n" + "\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
