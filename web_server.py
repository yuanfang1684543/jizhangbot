import os
import asyncio
import threading
from flask import Flask, jsonify, request, render_template_string

from bot.database.db import async_session, init_db
from bot.database.models import Operator, AllMembersFlag, GroupSetting, AdSchedule, AutoReply
from sqlalchemy import select

app = Flask(__name__)

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>记账机器人管理后台</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; color: #1a73e8; margin: 20px 0; }
        .card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h2 { font-size: 18px; margin-bottom: 12px; color: #555; border-bottom: 1px solid #eee; padding-bottom: 8px; }
        .form-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
        .form-row label { min-width: 80px; font-weight: 500; }
        input, select, textarea { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; flex: 1; min-width: 150px; }
        button { padding: 8px 20px; background: #1a73e8; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; }
        button:hover { background: #1557b0; }
        button.danger { background: #d93025; }
        .list-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
        .toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; color: white; z-index: 1000; display: none; }
        .toast.success { background: #0d904f; }
        .toast.error { background: #d93025; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 记账机器人管理后台</h1>

        <div class="card">
            <h2>🔑 群组基本配置</h2>
            <form hx-post="/api/group-settings" hx-target="#result">
                <div class="form-row">
                    <label>群组ID</label>
                    <input type="text" name="group_id" placeholder="-100xxx" required>
                </div>
                <div class="form-row">
                    <label>默认日切(时)</label>
                    <input type="number" name="day_switch_hour" placeholder="0-23" min="0" max="23">
                </div>
                <div class="form-row">
                    <label>默认显示模式</label>
                    <select name="display_mode">
                        <option value="default">默认</option>
                        <option value="show_replier">显示回复人</option>
                        <option value="show_creator">显示入账人</option>
                        <option value="pure">纯净模式</option>
                    </select>
                </div>
                <div class="form-row">
                    <label>试用时长(天)</label>
                    <input type="number" name="trial_duration" placeholder="0">
                </div>
                <div class="form-row">
                    <label>欢迎语</label>
                    <textarea name="welcome_message" rows="2" placeholder="欢迎使用记账机器人！"></textarea>
                </div>
                <button type="submit">💾 保存配置</button>
            </form>
        </div>

        <div class="card">
            <h2>👥 添加成员</h2>
            <form hx-post="/api/members" hx-target="#result">
                <div class="form-row">
                    <label>群组ID</label>
                    <input type="text" name="group_id" placeholder="-100xxx" required>
                </div>
                <div class="form-row">
                    <label>用户ID</label>
                    <input type="text" name="user_id" placeholder="Telegram用户数字ID" required>
                </div>
                <div class="form-row">
                    <label>姓名</label>
                    <input type="text" name="full_name" placeholder="用户名/昵称">
                </div>
                <button type="submit">➕ 添加成员</button>
            </form>
        </div>

        <div class="card">
            <h2>📢 定时广告</h2>
            <form hx-post="/api/ads" hx-target="#result">
                <div class="form-row">
                    <label>群组ID</label>
                    <input type="text" name="group_id" placeholder="-100xxx" required>
                </div>
                <div class="form-row">
                    <label>广告内容</label>
                    <textarea name="content" rows="2" placeholder="广告文案内容..." required></textarea>
                </div>
                <div class="form-row">
                    <label>时间间隔</label>
                    <input type="text" name="cron_expression" placeholder="*/30 * * * *">
                </div>
                <button type="submit">➕ 添加广告</button>
            </form>
        </div>

        <div class="card">
            <h2>🤖 自动回复规则</h2>
            <form hx-post="/api/auto-replies" hx-target="#result">
                <div class="form-row">
                    <label>群组ID</label>
                    <input type="text" name="group_id" placeholder="-100xxx" required>
                </div>
                <div class="form-row">
                    <label>关键字</label>
                    <input type="text" name="keyword" placeholder="触发关键字" required>
                </div>
                <div class="form-row">
                    <label>回复内容</label>
                    <textarea name="reply_content" rows="2" placeholder="自动回复的内容..." required></textarea>
                </div>
                <button type="submit">➕ 添加规则</button>
            </form>
        </div>

        <div id="result"></div>
    </div>
    <div id="toast" class="toast"></div>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script>
        document.body.addEventListener('htmx:afterRequest', function(evt) {
            var toast = document.getElementById('toast');
            if (evt.detail.successful) {
                toast.className = 'toast success';
                toast.textContent = '✅ 操作成功';
            } else {
                toast.className = 'toast error';
                toast.textContent = '❌ 操作失败';
            }
            toast.style.display = 'block';
            setTimeout(function() { toast.style.display = 'none'; }, 3000);
        });
    </script>
</body>
</html>
"""


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return jsonify({"service": "Telegram Accounting Bot", "version": "1.0", "admin": "/admin"})


@app.route("/admin")
@app.route("/admin/")
def admin_panel():
    return render_template_string(ADMIN_TEMPLATE)


@app.route("/api/group-settings", methods=["POST"])
def save_group_settings():
    """保存群组设置"""
    data = request.form
    group_id = int(data.get("group_id", 0))
    day_switch = data.get("day_switch_hour")
    display_mode = data.get("display_mode", "default")
    trial = data.get("trial_duration", "0")
    welcome = data.get("welcome_message", "")

    async def _save():
        async with async_session() as session:
            from bot.services.utils import get_group_setting
            setting = await get_group_setting(session, group_id)
            if day_switch and day_switch.strip():
                setting.day_switch_hour = int(day_switch)
            setting.display_mode = display_mode
            if trial and trial.strip():
                setting.trial_duration = int(trial)
            setting.welcome_message = welcome
            await session.commit()

    asyncio.run(_save())
    return jsonify({"status": "ok"})


@app.route("/api/members", methods=["POST"])
def add_member():
    """添加成员"""
    data = request.form
    group_id = int(data.get("group_id", 0))
    user_id = int(data.get("user_id", 0))
    full_name = data.get("full_name", "")

    async def _add():
        async with async_session() as session:
            existing = await session.scalar(
                select(Operator.id).where(Operator.group_id == group_id, Operator.user_id == user_id)
            )
            if not existing:
                session.add(Operator(group_id=group_id, user_id=user_id, full_name=full_name, username=""))
                await session.commit()

    asyncio.run(_add())
    return jsonify({"status": "ok"})


@app.route("/api/ads", methods=["POST"])
def save_ad():
    """保存定时广告"""
    data = request.form
    group_id = int(data.get("group_id", 0))
    content = data.get("content", "")
    cron = data.get("cron_expression", "")

    async def _save():
        async with async_session() as session:
            session.add(AdSchedule(group_id=group_id, content=content, cron_expression=cron))
            await session.commit()

    asyncio.run(_save())
    return jsonify({"status": "ok"})


@app.route("/api/auto-replies", methods=["POST"])
def save_auto_reply():
    """保存自动回复"""
    data = request.form
    group_id = int(data.get("group_id", 0))
    keyword = data.get("keyword", "")
    reply_content = data.get("reply_content", "")

    async def _save():
        async with async_session() as session:
            session.add(AutoReply(group_id=group_id, keyword=keyword, reply_content=reply_content))
            await session.commit()

    asyncio.run(_save())
    return jsonify({"status": "ok"})


def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run_web()
