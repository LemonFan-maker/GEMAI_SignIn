import asyncio
import json
from pathlib import Path

from config import (
    COOKIE_DIR, SCREENSHOT_DIR, ELEMENT_TIMEOUT, MAX_RETRIES,
    XPATH_USERNAME, XPATH_PASSWORD, XPATH_AGREE, XPATH_LOGIN_BTN,
    XPATH_CHECKIN_BTN, XPATH_CHECKIN_TEXT, XPATH_BALANCE,
    LOGIN_URL, CHECKIN_URL, mask_email,
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


def _cookie_path(username):
    COOKIE_DIR.mkdir(exist_ok=True)
    safe = username.replace("@", "_at_").replace(".", "_")
    return COOKIE_DIR / f"{safe}.json"


async def save_cookies(context, username):
    cookies = await context.cookies()
    _cookie_path(username).write_text(json.dumps(cookies, indent=2))
    print(f"[+] Cookies 已保存 ({mask_email(username)})")


async def load_cookies(context, username):
    cf = _cookie_path(username)
    if cf.exists():
        cookies = json.loads(cf.read_text())
        if cookies:
            await context.add_cookies(cookies)
            print(f"[+] Cookies 已加载 ({mask_email(username)})")
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
    masked = mask_email(username)
    print(f"[*] 正在打开登录页面... ({masked})")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded")

    await wait_and_fill(page, XPATH_USERNAME, username, "账号")
    await wait_and_fill(page, XPATH_PASSWORD, password, "密码")
    await wait_and_click(page, XPATH_AGREE, "同意协议")
    await wait_and_click(page, XPATH_LOGIN_BTN, "登录按钮")

    await page.wait_for_url("**/console*", timeout=30000)
    print(f"[+] 登录成功 ({masked})")

    await save_cookies(context, username)


async def get_balance(page):
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
    username = account["username"]
    password = account["password"]
    masked = mask_email(username)
    print(f"\n{'='*50}")
    print(f"[*] 开始处理账户: {masked}")
    print(f"{'='*50}")

    async def attempt():
        context = await browser.new_context()
        page = await context.new_page()
        try:
            cookies_loaded = await load_cookies(context, username)

            if cookies_loaded:
                status, balance = await checkin(page)
                if status:
                    await screenshot(page, f"{masked}_checkin")
                    return status, balance
                print("[*] Cookies 失效，重新登录...")

            if not cookies_loaded:
                print("[*] 没有已保存的 Cookies，先登录...")

            await login(page, context, username, password)
            status, balance = await checkin(page)
            await screenshot(page, f"{masked}_checkin")
            return status if status else "签到失败", balance
        except Exception:
            await screenshot(page, f"{masked}_error")
            raise
        finally:
            await context.close()

    try:
        status, balance = await retry(attempt, retries=MAX_RETRIES, delay=5)
    except Exception as e:
        status, balance = f"失败: {e}", "未知"

    return masked, status, balance
