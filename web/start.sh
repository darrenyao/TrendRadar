#!/bin/bash

# TrendRadar Web 配置界面启动脚本

echo "=================================="
echo "   TrendRadar 配置管理系统"
echo "=================================="
echo ""

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.10+"
    exit 1
fi

# 检查并安装依赖
if [ ! -d "venv" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv venv
fi

echo "📦 激活虚拟环境..."
source venv/bin/activate

echo "📦 安装依赖..."
pip install -q -r requirements.txt

echo ""
echo "🚀 启动 Web 服务..."
echo ""
echo "   访问地址: http://localhost:5000"
echo "   默认密码: admin123"
echo ""
echo "   修改密码: export ADMIN_PASSWORD=你的密码"
echo ""

# 设置环境变量（如果没有设置）
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}

# 启动 Flask
python app.py
