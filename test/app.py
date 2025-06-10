import json
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import Config
from database import Database
from wechat_crawler import WeChatCrawler
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('FlaskApp')

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY


# ================= 路由定义 =================

@app.route('/')
def dashboard():
    """仪表盘页面"""
    return render_template('dashboard.html')


@app.route('/accounts')
def accounts():
    """账号管理页面"""
    db = Database()
    accounts = db.get_wechat_accounts()
    return render_template('accounts.html', accounts=accounts)


@app.route('/add-account', methods=['POST'])
def add_account():
    """添加新账号"""
    username = request.form.get('username')
    nickname = request.form.get('nickname')

    if not username:
        flash('用户名不能为空', 'danger')
        return redirect(url_for('accounts'))

    db = Database()
    account_id = db.add_wechat_account(username, nickname)

    if account_id:
        flash(f'账号 {username} 添加成功', 'success')
    else:
        flash('账号添加失败，可能已存在', 'danger')

    return redirect(url_for('accounts'))


@app.route('/update-account/<int:account_id>', methods=['POST'])
def update_account(account_id):
    """更新账号状态"""
    is_active = request.form.get('is_active') == 'true'

    db = Database()
    result = db.update_account_status(account_id, is_active)

    if result:
        action = "启用" if is_active else "禁用"
        flash(f'账号状态已更新: {action}', 'success')
    else:
        flash('账号状态更新失败', 'danger')

    return redirect(url_for('accounts'))


@app.route('/delete-account/<int:account_id>', methods=['POST'])
def delete_account(account_id):
    """删除账号"""
    db = Database()
    result = db.delete_account(account_id)

    if result:
        flash('账号已删除', 'success')
    else:
        flash('账号删除失败', 'danger')

    return redirect(url_for('accounts'))


@app.route('/fetch-account-data', methods=['POST'])
def fetch_account_data():
    """获取指定账号的视频数据"""
    data = request.get_json()
    username = data.get('username')

    if not username:
        return jsonify({'status': 'error', 'message': '缺少用户名'}), 400

    db = Database()
    account = db.get_account_by_username(username)

    if not account:
        return jsonify({'status': 'error', 'message': '账号不存在'}), 404

    crawler = WeChatCrawler()
    added_count = crawler.fetch_account_videos(account['id'], username)

    return jsonify({
        'status': 'success',
        'added_count': added_count
    })


@app.route('/fetch-data', methods=['POST'])
def fetch_data():
    """触发数据获取"""
    crawler = WeChatCrawler()
    added_count = crawler.fetch_all_active_accounts()
    return jsonify({
        'status': 'success',
        'added_count': added_count
    })


@app.route('/api/account-stats')
def account_stats():
    """获取账号和视频统计数据"""
    db = Database()
    accounts = db.get_wechat_accounts()
    total_videos = db.get_wechat_videos_count()

    # 计算平均点赞和转发
    avg_likes = 0
    avg_shares = 0
    if total_videos > 0:
        try:
            # 假设存在直接计算的方法
            avg_likes = db.get_query_results("SELECT AVG(likes) AS avg FROM wechat_videos")[0]['avg']
            avg_shares = db.get_query_results("SELECT AVG(shares) AS avg FROM wechat_videos")[0]['avg']
        except:
            pass

    return jsonify({
        'accounts': accounts,
        'videos_total': total_videos,
        'avg_likes': avg_likes or 0,
        'avg_shares': avg_shares or 0
    })


@app.route('/api/videos')
def get_videos():
    """获取视频数据，支持筛选参数"""
    # 获取DataTables参数
    draw = request.args.get('draw', 1, type=int)
    start = request.args.get('start', 0, type=int)
    length = request.args.get('length', 10, type=int)

    # 获取筛选参数
    account_ids = request.args.getlist('accounts[]', type=int)
    date_filter = request.args.get('date', type=int)
    min_likes = request.args.get('min_likes', type=int)
    region = request.args.get('region', type=str)

    # 计算分页
    page = start // length + 1
    offset = start

    # 基础查询（稍后添加条件）
    db = Database()

    # 获取视频数据
    videos = db.get_wechat_videos(
        account_ids=account_ids,
        offset=offset,
        limit=length
    )

    # 获取符合条件的视频总数
    total_count = db.get_wechat_videos_count(account_ids)

    return jsonify({
        'draw': draw,
        'recordsTotal': total_count,
        'recordsFiltered': total_count,
        'data': videos
    })


@app.route('/video/wechat/<int:video_id>')
def video_detail(video_id):
    """视频详情页面"""
    db = Database()
    video = db.get_video_details(video_id)
    if video:
        return render_template('video_detail.html', video=video)
    else:
        return render_template('404.html'), 404


@app.route('/api/video/delete/<int:video_id>', methods=['DELETE'])
def delete_video(video_id):
    """删除视频"""
    db = Database()
    result = db.delete_video(video_id)
    if result:
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)