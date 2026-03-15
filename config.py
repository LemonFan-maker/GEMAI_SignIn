import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

LOGIN_URL = "https://api.gemai.cc/login"
CHECKIN_URL = "https://api.gemai.cc/console/personal"
COOKIE_DIR = Path("cookies")
SCREENSHOT_DIR = Path("screenshots")

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

# 解析配置
_raw = os.environ.get("CHECKIN_CONFIG", "").strip()
if not _raw:
    CONFIG = {}
else:
    try:
        CONFIG = json.loads(_raw)
    except json.JSONDecodeError as e:
        print(f"[!] CHECKIN_CONFIG JSON 解析失败: {e}")
        CONFIG = {}

ACCOUNTS = CONFIG.get("accounts", [])
WECHAT_WEBHOOK_KEY = CONFIG.get("webhook_key", "")


def mask_email(email):
    """脱敏邮箱: 666***999@example.com"""
    parts = email.split("@")
    if len(parts) != 2:
        return email[:3] + "***"
    local = parts[0]
    if len(local) <= 3:
        masked = local[0] + "***"
    else:
        masked = local[:3] + "***" + local[-3:]
    return f"{masked}@{parts[1]}"
