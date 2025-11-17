# TrendRadar Web 配置管理系统

多用户配置管理界面，支持每个用户独立配置关键词和通知渠道。

## 快速开始

### 本地运行

```bash
# 启动服务
./start.sh

# 访问 http://localhost:5000
# 默认密码: admin123
```

### Docker 运行

```bash
# 构建
docker build -t trendradar-web .

# 运行
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/../config:/app/config \
  -e ADMIN_PASSWORD=your_password \
  --name trendradar-web \
  trendradar-web
```

## 主要功能

- ✅ 多用户管理
- ✅ 个性化关键词配置
- ✅ 独立通知渠道
- ✅ 推送配置
- ✅ 配置导出

## 详细文档

查看 [完整使用指南](../WEB_CONFIG_GUIDE.md)

## 环境变量

- `ADMIN_PASSWORD`: 管理员密码（默认: admin123）
- `SECRET_KEY`: Flask 密钥（自动生成）

## 文件结构

```
web/
├── app.py              # Flask 应用
├── models.py           # 数据模型
├── config_manager.py   # 配置管理器
├── templates/          # HTML 模板
├── requirements.txt    # Python 依赖
├── Dockerfile          # Docker 镜像
└── start.sh            # 启动脚本
```

## 数据存储

- 数据库: `../config/users.db` (SQLite)
- 导出配置: `../config/users/*.yaml`

## 技术栈

- 后端: Flask 3.0+
- 前端: Bootstrap 5 + Vanilla JS
- 数据库: SQLite 3
- Python: 3.10+
