import pymysql
import logging
from datetime import datetime
from config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('Database')


class Database:
    def __init__(self):
        try:
            self.conn = pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self.cursor = self.conn.cursor()
            logger.info("✅ 成功连接到数据库")
        except pymysql.Error as e:
            logger.error(f"❌ 数据库连接失败: ({e.args[0]}) {e.args[1]}")
            raise e

    def __del__(self):
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    # ================= 账号管理方法 =================

    def get_wechat_accounts(self, only_active=False):
        """获取所有账号信息"""
        try:
            query = "SELECT * FROM wechat_accounts"
            if only_active:
                query += " WHERE is_active = TRUE"
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"❌ 获取账号列表失败: ({e.args[0]}) {e.args[1]}")
            return []

    def add_wechat_account(self, username, nickname=None):
        """添加视频号账号"""
        logger.info(f"📝 添加账号: username={username}, nickname={nickname}")

        if nickname == "":
            nickname = None

        query = """INSERT INTO wechat_accounts (username, nickname) 
                   VALUES (%s, %s)
                   ON DUPLICATE KEY UPDATE nickname = COALESCE(%s, nickname)"""
        try:
            self.cursor.execute(query, (username, nickname, nickname))
            self.conn.commit()
            account_id = self.cursor.lastrowid
            logger.info(f"✅ 账号添加成功, ID: {account_id}")
            return account_id
        except pymysql.Error as e:
            logger.error(f"❌ 添加账号失败: ({e.args[0]}) {e.args[1]}")
            self.conn.rollback()
            return None

    def get_account_by_username(self, username):
        """根据用户名获取账号信息"""
        query = "SELECT * FROM wechat_accounts WHERE username = %s"
        try:
            self.cursor.execute(query, (username,))
            return self.cursor.fetchone()
        except pymysql.Error as e:
            logger.error(f"❌ 获取账号信息失败: ({e.args[0]}) {e.args[1]}")
            return None

    def get_account_by_id(self, account_id):
        """根据ID获取账号信息"""
        query = "SELECT * FROM wechat_accounts WHERE id = %s"
        try:
            self.cursor.execute(query, (account_id,))
            return self.cursor.fetchone()
        except pymysql.Error as e:
            logger.error(f"❌ 获取账号信息失败: ({e.args[0]}) {e.args[1]}")
            return None

    def update_account_status(self, account_id, is_active):
        """更新账号启用状态"""
        query = "UPDATE wechat_accounts SET is_active = %s WHERE id = %s"
        try:
            self.cursor.execute(query, (is_active, account_id))
            self.conn.commit()
            return self.cursor.rowcount
        except pymysql.Error as e:
            logger.error(f"❌ 更新账号状态失败: ({e.args[0]}) {e.args[1]}")
            self.conn.rollback()
            return 0

    def delete_account(self, account_id):
        """删除账号"""
        try:
            # 先删除账号相关的视频
            self.cursor.execute("DELETE FROM wechat_videos WHERE account_id = %s", (account_id,))
            # 再删除账号
            self.cursor.execute("DELETE FROM wechat_accounts WHERE id = %s", (account_id,))
            self.conn.commit()
            return self.cursor.rowcount
        except pymysql.Error as e:
            logger.error(f"❌ 删除账号失败: ({e.args[0]}) {e.args[1]}")
            self.conn.rollback()
            return 0

    # ================= 视频管理方法 =================

    def insert_wechat_video(self, account_id, video_data):
        """插入微信视频号数据（关联账号）"""
        title = video_data['title']
        logger.info(f"💾 存储视频: 账号ID={account_id}, 标题={title[:30]}...")

        query = """INSERT INTO wechat_videos 
                   (account_id, title, publish_time, likes, shares, comments, region) 
                   VALUES (%(account_id)s, %(title)s, %(publish_time)s, %(likes)s, %(shares)s, %(comments)s, %(region)s)
                   ON DUPLICATE KEY UPDATE 
                   title=VALUES(title),
                   likes=VALUES(likes),
                   shares=VALUES(shares),
                   comments=VALUES(comments),
                   region=VALUES(region)"""
        video_data['account_id'] = account_id

        try:
            self.cursor.execute(query, video_data)
            self.conn.commit()
            video_id = self.cursor.lastrowid
            if video_id:
                logger.info(f"✅ 视频存储成功, ID: {video_id}")
            else:
                logger.info("🔄 视频已存在，更新数据")
            return video_id
        except pymysql.Error as e:
            error_msg = f"❌ 存储视频失败: ({e.args[0]}) {e.args[1]}"
            if e.args[0] == 1452:  # 外键约束错误
                error_msg += f" - 检查账号ID {account_id} 是否存在"
            logger.error(error_msg)
            self.conn.rollback()
            return None
        except Exception as e:
            logger.error(f"❌ 存储视频失败: {e}")
            self.conn.rollback()
            return None

    def get_wechat_videos_count(self, account_ids=None):
        """获取微信视频总数，可指定账号"""
        try:
            if account_ids:
                placeholders = ', '.join(['%s'] * len(account_ids))
                query = f"SELECT COUNT(*) AS total FROM wechat_videos WHERE account_id IN ({placeholders})"
                self.cursor.execute(query, account_ids)
            else:
                query = "SELECT COUNT(*) AS total FROM wechat_videos"
                self.cursor.execute(query)

            result = self.cursor.fetchone()
            return result['total'] if result else 0
        except pymysql.Error as e:
            logger.error(f"❌ 获取视频总数失败: ({e.args[0]}) {e.args[1]}")
            return 0

    def get_wechat_videos(self, account_ids=None, offset=0, limit=10):
        """获取微信视频数据，支持分页和账号筛选"""
        try:
            if account_ids and len(account_ids) > 0:
                placeholders = ', '.join(['%s'] * len(account_ids))
                query = f"""SELECT wv.*, wa.username, wa.nickname 
                            FROM wechat_videos wv
                            JOIN wechat_accounts wa ON wv.account_id = wa.id
                            WHERE wv.account_id IN ({placeholders})
                            ORDER BY wv.publish_time DESC 
                            LIMIT %s OFFSET %s"""
                params = account_ids + [limit, offset]
            else:
                query = """SELECT wv.*, wa.username, wa.nickname 
                           FROM wechat_videos wv
                           JOIN wechat_accounts wa ON wv.account_id = wa.id
                           ORDER BY wv.publish_time DESC 
                           LIMIT %s OFFSET %s"""
                params = [limit, offset]

            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"❌ 获取视频列表失败: ({e.args[0]}) {e.args[1]}")
            return []

    def get_video_details(self, video_id):
        """获取单个视频详情"""
        query = """SELECT wv.*, wa.username, wa.nickname 
                   FROM wechat_videos wv
                   JOIN wechat_accounts wa ON wv.account_id = wa.id
                   WHERE wv.id = %s"""
        try:
            self.cursor.execute(query, (video_id,))
            return self.cursor.fetchone()
        except pymysql.Error as e:
            logger.error(f"❌ 获取视频详情失败: ({e.args[0]}) {e.args[1]}")
            return None

    def delete_video(self, video_id):
        """删除视频"""
        query = "DELETE FROM wechat_videos WHERE id = %s"
        try:
            self.cursor.execute(query, (video_id,))
            self.conn.commit()
            return self.cursor.rowcount
        except pymysql.Error as e:
            logger.error(f"❌ 删除视频失败: ({e.args[0]}) {e.args[1]}")
            self.conn.rollback()
            return 0

    # ================= 通用查询方法 =================

    def get_query_results(self, query, params=None):
        """执行查询并返回结果"""
        try:
            self.cursor.execute(query, params or ())
            return self.cursor.fetchall()
        except pymysql.Error as e:
            logger.error(f"❌ 查询执行失败: ({e.args[0]}) {e.args[1]}")
            return []