# TrendRadar 多用户配置系统使用指南

支持多个用户独立配置关键词和推送渠道的 Web 管理界面。

---

## 📋 目录

- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [使用教程](#使用教程)
- [API 文档](#api-文档)
- [部署方式](#部署方式)
- [常见问题](#常见问题)

---

## ✨ 功能特性

### 1. 多用户管理
- ✅ 创建/编辑/删除用户
- ✅ 每个用户独立的 Token 认证
- ✅ 启用/禁用用户
- ✅ Token 重新生成

### 2. 个性化关键词配置
- ✅ 每个用户独立的关键词列表
- ✅ 单个添加或批量导入
- ✅ 实时添加/删除关键词
- ✅ 关键词数量统计

### 3. 独立通知渠道
每个用户可以配置自己的通知方式：
- Telegram
- 钉钉
- 企业微信
- 飞书
- 邮件
- ntfy

### 4. 通知测试功能
- ✅ 单个渠道即时测试
- ✅ 批量测试所有渠道
- ✅ 详细的错误提示和解决方案
- ✅ 实时显示测试结果

### 5. 推送配置
- 推送模式（daily/incremental/current）
- 排名高亮阈值
- 推送时间窗口控制

### 6. 配置导出
- 导出单个用户配置为 YAML
- 批量导出所有用户配置
- 兼容 TrendRadar 主程序格式

---

## 🚀 快速开始

### 方式1：本地运行（推荐开发）

```bash
# 进入 web 目录
cd web

# 启动服务（自动安装依赖）
./start.sh
```

访问：http://localhost:5000
默认密码：`admin123`

### 方式2：Docker 运行

```bash
# 构建镜像
docker build -t trendradar-web ./web

# 运行容器
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/config:/app/config \
  -e ADMIN_PASSWORD=your_password \
  --name trendradar-web \
  trendradar-web
```

### 方式3：Python 虚拟环境

```bash
cd web

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动
python app.py
```

---

## 📖 使用教程

### 第1步：登录系统

1. 访问 http://localhost:5000
2. 输入管理员密码（默认：`admin123`）
3. 点击"登录"

### 第2步：创建用户

1. 点击顶部导航栏的"创建用户"
2. 填写用户信息：
   - **用户名称**（必填）：例如"张三"
   - **用户ID**（可选）：留空则自动生成
3. 点击"创建用户"
4. **重要**：记录显示的 Token（仅显示一次）

### 第3步：配置关键词

1. 在用户列表中点击"编辑"
2. 切换到"关键词配置"标签页
3. 添加关键词：
   - **单个添加**：输入关键词 → 点击"添加"
   - **批量添加**：每行一个关键词 → 点击"批量添加"

示例关键词：
```
AI
科技
程序员
创业
投资
```

### 第4步：配置通知渠道

1. 切换到"通知配置"标签页
2. 至少配置一种通知方式：

#### Telegram 配置
```
Bot Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
Chat ID: 123456789
```

#### 钉钉配置
```
Webhook URL: https://oapi.dingtalk.com/robot/send?access_token=xxx
⚠️ 记得设置安全关键词为 "热点"
```

#### 邮件配置
```
发件人邮箱: your-email@gmail.com
邮箱授权码: abcdefghijklmnop
收件人: recipient@example.com
```

3. 点击"保存通知配置"

### 第5步：测试通知配置

在保存配置后，建议立即测试通知是否正常工作：

1. **测试单个渠道**：
   - 在每个通知渠道卡片右上角点击"测试"按钮
   - 系统会发送测试消息到对应渠道
   - 成功或失败信息会立即显示

2. **测试所有渠道**：
   - 点击"测试所有渠道"按钮
   - 系统会逐一测试所有已配置的渠道
   - 在弹窗中查看每个渠道的测试结果

3. **常见测试错误**：

   **Telegram 测试失败**：
   ```
   ❌ Bot Token 无效或 Chat ID 错误
   ✅ 解决：检查 Bot Token 格式和 Chat ID 是否正确
   ```

   **钉钉测试失败**：
   ```
   ❌ 安全设置校验失败
   ✅ 解决：确保机器人安全设置中添加了关键词"热点"
   ```

   **邮件测试失败**：
   ```
   ❌ SMTP 认证失败
   ✅ 解决：确认使用的是邮箱授权码，而非登录密码
   ```

   **企业微信/飞书测试失败**：
   ```
   ❌ Webhook URL 无效
   ✅ 解决：重新复制完整的 Webhook 地址
   ```

4. **测试消息内容**：
   - 测试消息会显示配置的用户ID和当前时间
   - 成功收到测试消息即表示配置正确

### 第6步：配置推送选项

1. 切换到"推送配置"标签页
2. 设置推送模式：
   - **Daily**：当日汇总模式
   - **Current**：当前榜单模式
   - **Incremental**：增量监控模式（推荐）
3. 设置排名阈值（默认：5）
4. 可选：启用推送时间窗口
5. 点击"保存推送配置"

### 第7步：导出配置

1. 点击"导出配置"按钮
2. 配置将保存到 `config/users/用户ID.yaml`
3. 或点击首页的"导出所有配置"批量导出

---

## 🔌 API 文档

### 用户管理

#### 获取用户信息
```http
GET /api/user/<user_id>
```

#### 更新用户信息
```http
POST /api/user/<user_id>/update
Content-Type: application/json

{
  "name": "新名称",
  "enabled": true
}
```

#### 重新生成 Token
```http
POST /api/user/<user_id>/token/regenerate
```

### 关键词管理

#### 获取关键词列表
```http
GET /api/user/<user_id>/keywords
```

#### 添加单个关键词
```http
POST /api/user/<user_id>/keywords
Content-Type: application/json

{
  "keyword": "AI"
}
```

#### 批量添加关键词
```http
POST /api/user/<user_id>/keywords/batch
Content-Type: application/json

{
  "keywords": "AI\n科技\n程序员"
}
```

#### 删除关键词
```http
DELETE /api/user/<user_id>/keywords
Content-Type: application/json

{
  "keyword": "AI"
}
```

### 配置管理

#### 更新通知配置
```http
POST /api/user/<user_id>/notification
Content-Type: application/json

{
  "telegram_bot_token": "xxx",
  "telegram_chat_id": "123456",
  "dingtalk_url": "https://..."
}
```

#### 测试通知配置
```http
POST /api/user/<user_id>/test-notification
Content-Type: application/json

{
  "channel": "telegram"  // telegram | dingtalk | wework | feishu | email | ntfy | all
}
```

**响应示例（单个渠道）**：
```json
{
  "success": true,
  "message": "✅ Telegram 测试消息发送成功！",
  "channel": "telegram"
}
```

**响应示例（所有渠道）**：
```json
{
  "success": true,
  "results": {
    "telegram": {"success": true, "message": "✅ 测试消息发送成功！"},
    "dingtalk": {"success": false, "message": "❌ 安全设置校验失败"},
    "email": {"success": true, "message": "✅ 测试邮件发送成功！"}
  },
  "summary": "测试完成：2/3 个渠道成功"
}
```

#### 更新推送配置
```http
POST /api/user/<user_id>/push
Content-Type: application/json

{
  "mode": "incremental",
  "rank_threshold": 5,
  "push_window_enabled": true
}
```

#### 导出用户配置
```http
GET /api/user/<user_id>/export
```

---

## 📦 部署方式

### Docker Compose 部署（推荐生产）

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  web:
    build: ./web
    container_name: trendradar-web
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./config:/app/config
    environment:
      - ADMIN_PASSWORD=your_secure_password
      - SECRET_KEY=your_secret_key_here
```

启动：
```bash
docker-compose up -d
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name trendradar.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 使用 systemd 服务

创建 `/etc/systemd/system/trendradar-web.service`：

```ini
[Unit]
Description=TrendRadar Web Config
After=network.target

[Service]
Type=simple
User=trendradar
WorkingDirectory=/path/to/TrendRadar/web
Environment="ADMIN_PASSWORD=your_password"
ExecStart=/path/to/TrendRadar/web/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable trendradar-web
sudo systemctl start trendradar-web
```

---

## 🔒 安全建议

### 1. 修改默认密码

```bash
# 通过环境变量设置
export ADMIN_PASSWORD=your_secure_password

# 或在 Docker 中
-e ADMIN_PASSWORD=your_secure_password
```

### 2. 使用 HTTPS

生产环境务必使用 HTTPS，可以使用 Nginx + Let's Encrypt：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d trendradar.yourdomain.com
```

### 3. 限制访问

使用防火墙限制只允许特定 IP 访问：

```bash
# UFW 示例
sudo ufw allow from 192.168.1.0/24 to any port 5000
```

### 4. 定期备份数据库

```bash
# 备份数据库
cp config/users.db config/users.db.backup

# 自动备份脚本
0 2 * * * cp /path/to/config/users.db /path/to/backup/users_$(date +\%Y\%m\%d).db
```

---

## ❓ 常见问题

### 1. 忘记管理员密码怎么办？

重新设置环境变量：
```bash
export ADMIN_PASSWORD=new_password
python app.py
```

### 2. 配置导出后如何使用？

导出的配置保存在 `config/users/` 目录，可以：
- 直接被 TrendRadar 主程序读取
- 备份或迁移到其他服务器
- 手动编辑 YAML 文件

### 3. 如何批量导入用户？

目前需要通过 Web 界面逐个创建。如需批量导入，可以：
1. 直接操作数据库（高级用户）
2. 使用 API 编写导入脚本

### 4. 数据库在哪里？

默认位置：`config/users.db`（SQLite 数据库）

查看数据库：
```bash
sqlite3 config/users.db
.tables
SELECT * FROM users;
```

### 5. 如何迁移到新服务器？

复制以下文件：
- `config/users.db`（数据库）
- `config/users/*.yaml`（导出的配置）
- `web/` 目录（Web 应用）

### 6. 支持多管理员吗？

当前版本只支持单个管理员密码。如需多管理员，建议：
- 使用统一的强密码
- 通过 IP 白名单控制访问
- 或自行扩展认证系统

### 7. 如何查看日志？

```bash
# Flask 开发模式会输出到终端
python app.py

# Docker 查看日志
docker logs -f trendradar-web

# systemd 查看日志
sudo journalctl -u trendradar-web -f
```

---

## 🎯 使用场景

### 场景1：团队使用

多个团队成员各自配置关心的关键词：

```
用户A：产品经理
关键词：产品、用户体验、竞品
通知：Telegram

用户B：技术负责人
关键词：AI、技术架构、开源
通知：邮件

用户C：市场人员
关键词：营销、增长、品牌
通知：企业微信
```

### 场景2：多项目监控

为不同项目配置不同的监控：

```
项目A：AI 项目
关键词：AI、机器学习、大模型
通知：项目A 钉钉群

项目B：区块链项目
关键词：区块链、加密货币、Web3
通知：项目B 飞书群
```

### 场景3：客户服务

为 VIP 客户提供定制化监控：

```
客户1：token_abc123
关键词：客户指定的行业关键词
通知：客户的邮箱

客户2：token_def456
关键词：另一组关键词
通知：客户的 Telegram
```

---

## 🔧 高级功能

### 自定义配置存储路径

修改 `app.py`：

```python
config_mgr = ConfigManager(db_path="path/to/your/db.db")
```

### 添加自定义字段

扩展数据库模型（`models.py`），添加新字段。

### 集成现有认证系统

替换 `app.py` 中的登录逻辑，集成 OAuth、LDAP 等。

---

## 📚 相关文档

- [TrendRadar 主项目文档](readme.md)
- [VPS 部署指南](DEPLOY_VPS.md)
- [钉钉配置指南](DINGTALK_GUIDE.md)

---

## 💡 最佳实践

1. **定期备份数据库**：避免数据丢失
2. **使用强密码**：保护管理界面安全
3. **限制访问**：通过防火墙或 VPN 限制访问
4. **监控日志**：定期查看日志发现异常
5. **测试配置**：修改配置后先测试再正式使用

---

## 🎉 快速体验

```bash
# 1. 启动配置界面
cd web && ./start.sh

# 2. 访问 http://localhost:5000，使用默认密码 admin123

# 3. 创建第一个用户

# 4. 配置关键词和通知渠道

# 5. 导出配置

# 6. 运行主程序测试
python main.py
```

祝你使用愉快！🚀
