import asyncio
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

LOGIN_URL = "https://api.gemai.cc/login"
CHECKIN_URL = "https://api.gemai.cc/console/personal"
COOKIE_DIR = Path("cookies")
SCREENSHOT_DIR = Path("screenshots")

# 统一配置: 从单个 JSON 读取所有敏感信息
# 格式: {"accounts":[{"username":"a@b.com","password":"xxx"}],"webhook_key":"xxx"}
_raw = os.environ.get("CHECKIN_CONFIG", "").strip()
if not _raw:
    CONFIG = {}
else:
    try:
        CONFIG = json.loads(_raw)
    except json.JSONDecodeError as e:
        print(f"[!] CHECKIN_CONFIG JSON 解析失败: {e}")
        print(f"[!] 原始值: {_raw[:80]}...")
        CONFIG = {}
ACCOUNTS = CONFIG.get("accounts", [])
WECHAT_WEBHOOK_KEY = CONFIG.get("webhook_key", "")

MAX_RETRIES = 3
ELEMENT_TIMEOUT = 15000

# XPath 选择器
XPATH_USERNAME = '//*[@id="username"]'
XPATH_PASSWORD = '//*[@id="password"]'
XPATH_AGREE = (
    'xpath=/html/body/div/section/section/section/main/div/div[3]'
    '/div/div/div[2]/div/div[2]/form/div[3]/span/span/span'
)
XPATH_LOGIN_BTN = (
    'xpath=/html/body/div/section/section/section/main/div/div[3]'
    '/div/div/div[2]/div/div[2]/form/div[4]/button[1]'
)
XPATH_CHECKIN_BTN = (
    'xpath=/html/body/div/section/section/section/main'
    '/div/div/div/div[2]/div/div/div[1]/button'
)
XPATH_CHECKIN_TEXT = (
    'xpath=/html/body/div/section/section/section/main'
    '/div/div/div/div[2]/div/div/div[1]/button/span/span'
)
XPATH_BALANCE = (
    'xpath=/html/body/div/section/section/section/main'
    '/div/div/div/div[1]/div[2]/div[1]/span/div'
)


async def retry(func, *args, retries=MAX_RETRIES, delay=5):
    for attempt in range(1, retries + 1):
        try:
            return await func(*args)
        except Exception as e:
            print(f"[!] 第 {attempt}/{retries} 次尝试失败: {e}")
            if attempt == retries:
                raise
            print(f"[*] {delay} 秒后重试...")
            await asyncio.sleep(delay)


def cookie_file_for(username):
    COOKIE_DIR.mkdir(exist_ok=True)
    safe_name = username.replace("@", "_at_").replace(".", "_")
    return COOKIE_DIR / f"{safe_name}.json"


async def save_cookies(context, username):
    cookies = await context.cookies()
    cookie_file_for(username).write_text(json.dumps(cookies, indent=2))
    print(f"[+] Cookies 已保存 ({username})")


async def load_cookies(context, username):
    cf = cookie_file_for(username)
    if cf.exists():
        cookies = json.loads(cf.read_text())
        if cookies:
            await context.add_cookies(cookies)
            print(f"[+] Cookies 已加载 ({username})")
            return True
    return False


async def screenshot(page, name):
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    path = SCREENSHOT_DIR / f"{name}.png"
    try:
        await page.screenshot(path=str(path))
        print(f"[*] 截图已保存: {path}")
    except Exception:
        pass


async def wait_and_fill(page, selector, value, label):
    print(f"[*] 等待 {label} 输入框加载...")
    locator = page.locator(selector)
    await locator.wait_for(state="visible", timeout=ELEMENT_TIMEOUT)
    await locator.fill(value)
    print(f"[+] {label} 已填入")


async def wait_and_click(page, selector, label):
    print(f"[*] 等待 {label} 加载...")
    locator = page.locator(selector)
    await locator.wait_for(state="visible", timeout=ELEMENT_TIMEOUT)
    await locator.click()
    print(f"[+] 已点击 {label}")


async def login(page, context, username, password):
    print(f"[*] 正在打开登录页面... ({username})")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")

    await wait_and_fill(page, XPATH_USERNAME, username, "账号")
    await wait_and_fill(page, XPATH_PASSWORD, password, "密码")
    await wait_and_click(page, XPATH_AGREE, "同意协议")
    await wait_and_click(page, XPATH_LOGIN_BTN, "登录按钮")

    await page.wait_for_url("**/console*", timeout=30000)
    print(f"[+] 登录成功 ({username})")

    await save_cookies(context, username)


async def get_balance(page):
    """刷新页面并读取余额"""
    print("[*] 刷新页面获取最新余额...")
    await page.reload(wait_until="networkidle")
    await page.wait_for_timeout(2000)

    balance_el = page.locator(XPATH_BALANCE)
    await balance_el.wait_for(state="visible", timeout=ELEMENT_TIMEOUT)
    balance = (await balance_el.text_content()).strip()
    print(f"[+] 当前余额: {balance}")
    return balance


async def checkin(page):
    print("[*] 正在打开签到页面...")
    await page.goto(CHECKIN_URL, wait_until="domcontentloaded")

    await page.wait_for_timeout(3000)
    if "/login" in page.url:
        print("[-] 登录态已失效")
        return False, ""

    print("[*] 等待签到按钮加载...")
    btn = page.locator(XPATH_CHECKIN_BTN)
    await btn.wait_for(state="visible", timeout=ELEMENT_TIMEOUT)

    # 检查按钮文字判断是否已签到
    btn_text_el = page.locator(XPATH_CHECKIN_TEXT)
    await btn_text_el.wait_for(state="visible", timeout=ELEMENT_TIMEOUT)
    btn_text = (await btn_text_el.text_content()).strip()

    if btn_text in ("Checked in today", "今日已签到"):
        print("[*] 今日已签到，无需重复操作")
        balance = await get_balance(page)
        return "已签到", balance

    await btn.click()
    print("[+] 已点击签到按钮，等待结果...")
    await page.wait_for_timeout(3000)
    print("[+] 签到完成!")

    balance = await get_balance(page)
    return "签到成功", balance


async def run_account(browser, account):
    """单个账户的完整签到流程，返回 (用户名, 状态, 余额)"""
    username = account["username"]
    password = account["password"]
    print(f"\n{'='*50}")
    print(f"[*] 开始处理账户: {username}")
    print(f"{'='*50}")

    async def attempt():
        context = await browser.new_context()
        page = await context.new_page()
        try:
            cookies_loaded = await load_cookies(context, username)

            if cookies_loaded:
                status, balance = await checkin(page)
                if status:
                    await screenshot(page, f"{username}_checkin")
                    return status, balance
                print("[*] Cookies 失效，重新登录...")

            if not cookies_loaded:
                print("[*] 没有已保存的 Cookies，先登录...")

            await login(page, context, username, password)
            status, balance = await checkin(page)
            await screenshot(page, f"{username}_checkin")
            return status if status else "签到失败", balance
        except Exception:
            await screenshot(page, f"{username}_error")
            raise
        finally:
            await context.close()

    try:
        status, balance = await retry(attempt, retries=MAX_RETRIES, delay=5)
    except Exception as e:
        status, balance = f"失败: {e}", "未知"

    return username, status, balance


def send_wechat(message):
    """通过企业微信群机器人 webhook 发送通知"""
    if not WECHAT_WEBHOOK_KEY:
        print("[*] 未配置企业微信 webhook，跳过通知")
        return

    url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WECHAT_WEBHOOK_KEY}"
    data = json.dumps({"msgtype": "text", "text": {"content": message}}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("errcode") == 0:
                print("[+] 企业微信通知发送成功")
            else:
                print(f"[!] 企业微信通知发送失败: {result}")
    except Exception as e:
        print(f"[!] 企业微信通知发送异常: {e}")


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

    # 汇总结果
    print(f"\n{'='*50}")
    print("[*] 签到汇总")
    print(f"{'='*50}")

    lines = []
    for username, status, balance in results:
        line = f"{username} {status}，当前余额 {balance}"
        print(f"  {line}")
        lines.append(line)

    send_wechat("哈基米签到通知\n" + "\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
