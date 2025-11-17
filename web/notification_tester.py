"""
通知测试模块 - 发送测试消息到各个通知渠道
"""

import requests
from datetime import datetime
from typing import Dict, Tuple


class NotificationTester:
    """通知渠道测试器"""

    @staticmethod
    def test_telegram(bot_token: str, chat_id: str) -> Tuple[bool, str]:
        """
        测试 Telegram 通知

        Returns:
            (成功/失败, 消息)
        """
        if not bot_token or not chat_id:
            return False, "请先配置 Bot Token 和 Chat ID"

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        test_message = f"""
🧪 <b>TrendRadar 推送测试</b>

这是一条测试消息，用于验证 Telegram 通知配置是否正确。

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ 如果你看到这条消息，说明配置成功！
        """.strip()

        payload = {
            "chat_id": chat_id,
            "text": test_message,
            "parse_mode": "HTML"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            if result.get("ok"):
                return True, "✅ Telegram 测试成功！消息已发送"
            else:
                error_msg = result.get("description", "未知错误")
                return False, f"❌ Telegram 发送失败: {error_msg}"

        except requests.exceptions.Timeout:
            return False, "❌ 请求超时，请检查网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"❌ 网络错误: {str(e)}"
        except Exception as e:
            return False, f"❌ 发送失败: {str(e)}"

    @staticmethod
    def test_dingtalk(webhook_url: str) -> Tuple[bool, str]:
        """测试钉钉通知"""
        if not webhook_url:
            return False, "请先配置 Webhook URL"

        test_message = f"""
### 🧪 TrendRadar 推送测试

这是一条测试消息，用于验证钉钉通知配置是否正确。

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**状态**: ✅ 如果你看到这条消息，说明配置成功！

---

> 💡 提示：确保机器人安全设置中包含关键词 "热点" 或 "TrendRadar"
        """.strip()

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": "TrendRadar 推送测试",
                "text": test_message
            }
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            result = response.json()

            if result.get("errcode") == 0:
                return True, "✅ 钉钉测试成功！消息已发送"
            else:
                errcode = result.get("errcode")
                errmsg = result.get("errmsg", "未知错误")

                # 常见错误提示
                if errcode == 310000:
                    return False, "❌ 安全设置校验失败：请检查关键词配置（需包含 '热点' 或 'TrendRadar'）"
                elif errcode == 400101:
                    return False, "❌ access_token 无效，请检查 Webhook URL"
                elif errcode == 410100:
                    return False, "❌ 发送频率超限，请稍后再试"
                else:
                    return False, f"❌ 钉钉发送失败 (错误码: {errcode}): {errmsg}"

        except requests.exceptions.Timeout:
            return False, "❌ 请求超时，请检查网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"❌ 网络错误: {str(e)}"
        except Exception as e:
            return False, f"❌ 发送失败: {str(e)}"

    @staticmethod
    def test_wework(webhook_url: str) -> Tuple[bool, str]:
        """测试企业微信通知"""
        if not webhook_url:
            return False, "请先配置 Webhook URL"

        test_message = f"""
## 🧪 TrendRadar 推送测试

这是一条测试消息，用于验证企业微信通知配置是否正确。

**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**状态**: <font color="info">✅ 配置成功！</font>
        """.strip()

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": test_message
            }
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            result = response.json()

            if result.get("errcode") == 0:
                return True, "✅ 企业微信测试成功！消息已发送"
            else:
                errmsg = result.get("errmsg", "未知错误")
                return False, f"❌ 企业微信发送失败: {errmsg}"

        except requests.exceptions.Timeout:
            return False, "❌ 请求超时，请检查网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"❌ 网络错误: {str(e)}"
        except Exception as e:
            return False, f"❌ 发送失败: {str(e)}"

    @staticmethod
    def test_feishu(webhook_url: str) -> Tuple[bool, str]:
        """测试飞书通知"""
        if not webhook_url:
            return False, "请先配置 Webhook URL"

        test_message = f"""
**🧪 TrendRadar 推送测试**

这是一条测试消息，用于验证飞书通知配置是否正确。

<font color='grey'>测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</font>

<font color='green'>✅ 如果你看到这条消息，说明配置成功！</font>
        """.strip()

        payload = {
            "msg_type": "text",
            "content": {
                "text": test_message
            }
        }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            result = response.json()

            if result.get("StatusCode") == 0 or result.get("code") == 0:
                return True, "✅ 飞书测试成功！消息已发送"
            else:
                error_msg = result.get("msg") or result.get("StatusMessage", "未知错误")
                return False, f"❌ 飞书发送失败: {error_msg}"

        except requests.exceptions.Timeout:
            return False, "❌ 请求超时，请检查网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"❌ 网络错误: {str(e)}"
        except Exception as e:
            return False, f"❌ 发送失败: {str(e)}"

    @staticmethod
    def test_email(email_from: str, email_password: str, email_to: str,
                   smtp_server: str = "", smtp_port: str = "") -> Tuple[bool, str]:
        """测试邮件通知"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        if not all([email_from, email_password, email_to]):
            return False, "请先配置完整的邮件信息（发件人、密码、收件人）"

        # 自动识别 SMTP 服务器
        if not smtp_server:
            domain = email_from.split('@')[1].lower()
            smtp_servers = {
                'gmail.com': ('smtp.gmail.com', '587'),
                'qq.com': ('smtp.qq.com', '587'),
                '163.com': ('smtp.163.com', '465'),
                '126.com': ('smtp.126.com', '465'),
                'outlook.com': ('smtp-mail.outlook.com', '587'),
                'hotmail.com': ('smtp-mail.outlook.com', '587'),
            }

            if domain in smtp_servers:
                smtp_server, smtp_port = smtp_servers[domain]
            else:
                return False, f"❌ 无法自动识别 SMTP 服务器，请手动配置（邮箱域名: {domain}）"

        smtp_port = int(smtp_port) if smtp_port else 587

        # 创建测试邮件
        msg = MIMEMultipart()
        msg['From'] = email_from
        msg['To'] = email_to
        msg['Subject'] = '🧪 TrendRadar 推送测试'

        body = f"""
        <html>
        <body>
            <h2>🧪 TrendRadar 推送测试</h2>
            <p>这是一条测试邮件，用于验证邮件通知配置是否正确。</p>
            <p><strong>测试时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>发件人:</strong> {email_from}</p>
            <p><strong>收件人:</strong> {email_to}</p>
            <p><strong>SMTP服务器:</strong> {smtp_server}:{smtp_port}</p>
            <hr>
            <p style="color: green;">✅ 如果你看到这封邮件，说明配置成功！</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html', 'utf-8'))

        try:
            # 根据端口选择连接方式
            if smtp_port == 465:
                # SSL 连接
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
            else:
                # TLS 连接
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
                server.starttls()

            server.login(email_from, email_password)

            # 发送邮件
            recipients = [r.strip() for r in email_to.split(',')]
            server.send_message(msg)
            server.quit()

            return True, f"✅ 邮件测试成功！已发送到 {email_to}"

        except smtplib.SMTPAuthenticationError:
            return False, "❌ 认证失败：请检查邮箱地址和授权码（不是登录密码）"
        except smtplib.SMTPException as e:
            return False, f"❌ SMTP 错误: {str(e)}"
        except Exception as e:
            return False, f"❌ 发送失败: {str(e)}"

    @staticmethod
    def test_ntfy(server_url: str, topic: str, token: str = "") -> Tuple[bool, str]:
        """测试 ntfy 通知"""
        if not topic:
            return False, "请先配置 Topic 名称"

        server_url = server_url or "https://ntfy.sh"
        url = f"{server_url}/{topic}"

        test_message = f"""🧪 TrendRadar 推送测试

这是一条测试消息，用于验证 ntfy 通知配置是否正确。

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ 如果你看到这条消息，说明配置成功！"""

        headers = {
            "Title": "TrendRadar 推送测试",
            "Priority": "default",
            "Tags": "white_check_mark,test"
        }

        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            response = requests.post(
                url,
                data=test_message.encode('utf-8'),
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return True, "✅ ntfy 测试成功！消息已发送"
            elif response.status_code == 401:
                return False, "❌ 认证失败：Token 无效"
            elif response.status_code == 403:
                return False, "❌ 权限不足：无法访问该 Topic"
            else:
                return False, f"❌ 发送失败 (HTTP {response.status_code})"

        except requests.exceptions.Timeout:
            return False, "❌ 请求超时，请检查服务器地址和网络连接"
        except requests.exceptions.RequestException as e:
            return False, f"❌ 网络错误: {str(e)}"
        except Exception as e:
            return False, f"❌ 发送失败: {str(e)}"

    @staticmethod
    def test_all_channels(notification_config: Dict) -> Dict[str, Tuple[bool, str]]:
        """
        测试所有配置的通知渠道

        Returns:
            {
                "telegram": (True/False, "消息"),
                "dingtalk": (True/False, "消息"),
                ...
            }
        """
        results = {}

        # Telegram
        if notification_config.get("telegram_bot_token") and notification_config.get("telegram_chat_id"):
            results["telegram"] = NotificationTester.test_telegram(
                notification_config["telegram_bot_token"],
                notification_config["telegram_chat_id"]
            )

        # 钉钉
        if notification_config.get("dingtalk_url"):
            results["dingtalk"] = NotificationTester.test_dingtalk(
                notification_config["dingtalk_url"]
            )

        # 企业微信
        if notification_config.get("wework_url"):
            results["wework"] = NotificationTester.test_wework(
                notification_config["wework_url"]
            )

        # 飞书
        if notification_config.get("feishu_url"):
            results["feishu"] = NotificationTester.test_feishu(
                notification_config["feishu_url"]
            )

        # 邮件
        if notification_config.get("email_from") and notification_config.get("email_password"):
            results["email"] = NotificationTester.test_email(
                notification_config["email_from"],
                notification_config["email_password"],
                notification_config.get("email_to", ""),
                notification_config.get("email_smtp_server", ""),
                notification_config.get("email_smtp_port", "")
            )

        # ntfy
        if notification_config.get("ntfy_topic"):
            results["ntfy"] = NotificationTester.test_ntfy(
                notification_config.get("ntfy_server_url", "https://ntfy.sh"),
                notification_config["ntfy_topic"],
                notification_config.get("ntfy_token", "")
            )

        if not results:
            results["error"] = (False, "未配置任何通知渠道")

        return results
