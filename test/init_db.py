import pymysql
from config import Config


def init_database():
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        cursor = conn.cursor()

        # 创建数据库
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME}")
        cursor.execute(f"USE {Config.DB_NAME}")

        # 创建视频号账号表
        cursor.execute('''CREATE TABLE IF NOT EXISTS wechat_accounts (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        nickname VARCHAR(255),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )''')

        # 创建抖音数据表
        cursor.execute('''CREATE TABLE IF NOT EXISTS douyin_videos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        author VARCHAR(255) NOT NULL,
                        video_id VARCHAR(255) UNIQUE NOT NULL,
                        description TEXT,
                        publish_time DATETIME NOT NULL,
                        comments INT DEFAULT 0,
                        likes INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )''')

        # 创建微信视频号数据表（关联账号）
        cursor.execute('''CREATE TABLE IF NOT EXISTS wechat_videos (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        account_id INT NOT NULL,
                        title TEXT NOT NULL,
                        publish_time DATETIME NOT NULL,
                        likes INT DEFAULT 0,
                        shares INT DEFAULT 0,
                        comments INT DEFAULT 0,
                        region VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (account_id) REFERENCES wechat_accounts(id) ON DELETE CASCADE
                        )''')

        conn.commit()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    init_database()