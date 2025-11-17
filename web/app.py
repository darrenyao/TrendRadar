"""
TrendRadar 多用户配置界面
Flask Web 应用
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from config_manager import ConfigManager
import secrets
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# 初始化配置管理器
config_mgr = ConfigManager()

# 管理员密码（通过环境变量设置）
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


# ==================== 认证相关 ====================


@app.before_request
def require_login():
    """要求登录"""
    allowed_endpoints = ["login", "static"]

    if request.endpoint not in allowed_endpoints and not session.get("logged_in"):
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """登录页面"""
    if request.method == "POST":
        password = request.form.get("password", "")

        if password == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("登录成功", "success")
            return redirect(url_for("index"))
        else:
            flash("密码错误", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """登出"""
    session.pop("logged_in", None)
    flash("已退出登录", "info")
    return redirect(url_for("login"))


# ==================== 页面路由 ====================


@app.route("/")
def index():
    """首页 - 用户列表"""
    users = config_mgr.user_mgr.list_users()

    # 为每个用户获取关键词数量
    for user in users:
        user["keyword_count"] = len(config_mgr.keyword_mgr.get_keywords(user["user_id"]))

    return render_template("index.html", users=users)


@app.route("/user/create", methods=["GET", "POST"])
def create_user():
    """创建用户"""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        user_id = request.form.get("user_id", "").strip() or None

        if not name:
            flash("请输入用户名称", "danger")
            return redirect(url_for("create_user"))

        try:
            user = config_mgr.user_mgr.create_user(name, user_id)
            flash(
                f"用户创建成功！Token: {user['token']} （请妥善保管，仅显示一次）", "success"
            )
            return redirect(url_for("edit_user", user_id=user["user_id"]))
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("create_user"))

    return render_template("create_user.html")


@app.route("/user/<user_id>/edit")
def edit_user(user_id):
    """编辑用户配置"""
    user_config = config_mgr.get_user_full_config(user_id)

    if not user_config:
        flash("用户不存在", "danger")
        return redirect(url_for("index"))

    return render_template("edit_user.html", config=user_config)


@app.route("/user/<user_id>/delete", methods=["POST"])
def delete_user(user_id):
    """删除用户"""
    if config_mgr.user_mgr.delete_user(user_id):
        flash("用户已删除", "success")
    else:
        flash("删除失败", "danger")

    return redirect(url_for("index"))


# ==================== API 路由 ====================


@app.route("/api/user/<user_id>")
def api_get_user(user_id):
    """获取用户完整配置"""
    config = config_mgr.get_user_full_config(user_id)

    if not config:
        return jsonify({"error": "用户不存在"}), 404

    return jsonify(config)


@app.route("/api/user/<user_id>/update", methods=["POST"])
def api_update_user(user_id):
    """更新用户基本信息"""
    data = request.json

    name = data.get("name")
    enabled = data.get("enabled")

    if config_mgr.user_mgr.update_user(user_id, name=name, enabled=enabled):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "更新失败"}), 400


@app.route("/api/user/<user_id>/keywords", methods=["GET", "POST", "DELETE"])
def api_keywords(user_id):
    """关键词管理 API"""
    if request.method == "GET":
        keywords = config_mgr.keyword_mgr.get_keywords(user_id)
        return jsonify({"keywords": keywords})

    elif request.method == "POST":
        data = request.json
        keyword = data.get("keyword", "").strip()

        if not keyword:
            return jsonify({"error": "关键词不能为空"}), 400

        if config_mgr.keyword_mgr.add_keyword(user_id, keyword):
            return jsonify({"success": True, "keyword": keyword})
        else:
            return jsonify({"error": "关键词已存在"}), 400

    elif request.method == "DELETE":
        data = request.json
        keyword = data.get("keyword", "")

        if config_mgr.keyword_mgr.remove_keyword(user_id, keyword):
            return jsonify({"success": True})
        else:
            return jsonify({"error": "删除失败"}), 400


@app.route("/api/user/<user_id>/keywords/batch", methods=["POST"])
def api_keywords_batch(user_id):
    """批量添加关键词"""
    data = request.json
    keywords_text = data.get("keywords", "")

    # 按行分割
    keywords = [k.strip() for k in keywords_text.split("\n") if k.strip()]

    count = config_mgr.keyword_mgr.add_keywords_batch(user_id, keywords)

    return jsonify({"success": True, "count": count})


@app.route("/api/user/<user_id>/keywords/clear", methods=["POST"])
def api_keywords_clear(user_id):
    """清空所有关键词"""
    count = config_mgr.keyword_mgr.clear_keywords(user_id)
    return jsonify({"success": True, "count": count})


@app.route("/api/user/<user_id>/notification", methods=["GET", "POST"])
def api_notification_config(user_id):
    """通知配置 API"""
    if request.method == "GET":
        config = config_mgr.notif_mgr.get_config(user_id)
        return jsonify(config)

    elif request.method == "POST":
        data = request.json

        # 验证配置
        errors = config_mgr.validate_notification_config(data)
        if errors:
            return jsonify({"error": "配置验证失败", "details": errors}), 400

        if config_mgr.notif_mgr.update_config(user_id, data):
            return jsonify({"success": True})
        else:
            return jsonify({"error": "更新失败"}), 400


@app.route("/api/user/<user_id>/push", methods=["GET", "POST"])
def api_push_config(user_id):
    """推送配置 API"""
    if request.method == "GET":
        config = config_mgr.push_mgr.get_config(user_id)
        return jsonify(config)

    elif request.method == "POST":
        data = request.json

        if config_mgr.push_mgr.update_config(user_id, data):
            return jsonify({"success": True})
        else:
            return jsonify({"error": "更新失败"}), 400


@app.route("/api/user/<user_id>/export")
def api_export_config(user_id):
    """导出用户配置为 YAML"""
    filepath = config_mgr.export_user_config_to_yaml(user_id)

    if filepath:
        return jsonify({"success": True, "filepath": filepath})
    else:
        return jsonify({"error": "导出失败"}), 400


@app.route("/api/export-all")
def api_export_all():
    """导出所有用户配置"""
    count = config_mgr.export_all_configs()
    return jsonify({"success": True, "count": count})


@app.route("/api/user/<user_id>/token/regenerate", methods=["POST"])
def api_regenerate_token(user_id):
    """重新生成用户 token"""
    new_token = config_mgr.user_mgr.regenerate_token(user_id)

    if new_token:
        return jsonify({"success": True, "token": new_token})
    else:
        return jsonify({"error": "生成失败"}), 400


# ==================== 错误处理 ====================


@app.errorhandler(404)
def page_not_found(e):
    return render_template("error.html", error="页面不存在"), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template("error.html", error="服务器内部错误"), 500


# ==================== 启动应用 ====================

if __name__ == "__main__":
    # 开发模式
    app.run(host="0.0.0.0", port=5000, debug=True)
