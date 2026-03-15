import json
import urllib.request

from config import WECHAT_WEBHOOK_KEY


def send_wechat(message):
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
