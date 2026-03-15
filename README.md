# GEMAI SignIn

哈基米 API 站 (api.gemai.cc) 自动签到工具，支持多账户、企业微信通知，可通过 GitHub Actions 每日自动执行。

## 功能

- 自动登录并完成每日签到
- 支持多账户批量签到
- 签到后自动读取账户余额
- 智能判断今日是否已签到，避免重复操作
- 企业微信群机器人通知签到结果
- 失败自动重试（最多 3 次）
- 每一步操作前等待页面加载，稳定可靠

## 快速开始（GitHub Actions）

### 1. Fork 本仓库

点击右上角 **Fork** 按钮将仓库复制到你的账户下。

### 2. 生成配置

打开 [配置生成器](https://lemonfan-maker.github.io/GEMAI_SignIn)，填入账号密码和企业微信 Webhook Key，点击生成，复制生成的 JSON 字符串。

配置格式如下：

```json
{
  "accounts": [
    { "username": "your_email@example.com", "password": "your_password" },
    { "username": "another@example.com", "password": "another_password" }
  ],
  "webhook_key": "your_wechat_webhook_key"
}
```

> `webhook_key` 为可选项，不需要通知可以不填。

### 3. 配置 Secret

1. 进入你 Fork 的仓库，点击 **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. **Name** 填写 `CHECKIN_CONFIG`
4. **Secret** 粘贴上一步生成的 JSON 字符串
5. 点击 **Add secret**

> 如果你的 workflow 配置了 `environment: production`，需要在 **Settings** → **Environments** → **production** 中添加 Secret。

### 4. 启用 Actions

1. 进入仓库的 **Actions** 页面
2. 如果提示需要启用，点击 **I understand my workflows, go ahead and enable them**
3. 点击左侧 **Daily Checkin** → **Run workflow** 手动触发一次测试

之后每天北京时间 8:00 会自动执行签到。

## 本地调试

```bash
# 克隆仓库
git clone https://github.com/LemonFan-maker/GEMAI_SignIn.git
cd GEMAI_SignIn

# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 创建配置文件
cp .env.example .env
# 编辑 .env，填入你的配置 JSON

# 运行（会弹出浏览器窗口）
python checkin.py
```

本地运行时会打开浏览器窗口，方便观察操作过程。GitHub Actions 中自动以无头模式运行。

## 企业微信通知

签到完成后会通过企业微信群机器人发送汇总通知，格式如下：

```
哈基米签到通知
account1@example.com 签到成功，当前余额 ¥550.00
account2@example.com 已签到，当前余额 ¥500.00
```

### 获取 Webhook Key

1. 在企业微信中创建或进入一个群聊
2. 点击右上角 **...** → **群机器人** → **添加机器人**
3. 创建后会得到 Webhook URL：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxx`
4. 复制 `key=` 后面的部分即为 Webhook Key

## 项目结构

```
.
├── .github/workflows/checkin.yml   # GitHub Actions 工作流
├── .env.example                    # 环境变量模板
├── .gitignore
├── checkin.py                      # 签到主脚本
├── config-generator.html           # 配置生成器页面
├── requirements.txt                # Python 依赖
└── README.md
```

## 许可证

MIT
