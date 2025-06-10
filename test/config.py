import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
class Config:
        # 数据库配置
        DB_HOST = os.getenv('DB_HOST', 'localhost')
        DB_PORT = int(os.getenv('DB_PORT', 3306))
        DB_USER = os.getenv('DB_USER', 'root')
        DB_PASSWORD = os.getenv('DB_PASSWORD', 'root123')
        DB_NAME = os.getenv('DB_NAME', 'video_analysis')

        # 微信API配置
        WECHAT_API_URL = os.getenv('WECHAT_API_URL', 'http://14.103.176.76:5000/wechat/video/getUserInfo')
        WECHAT_API_KEY = os.getenv('WECHAT_API_KEY', 'e04cd554e5a0528e303cb645f3d652a3')

        # Flask配置
        SECRET_KEY = os.getenv('SECRET_KEY', 'secret-key')
        DEBUG = os.getenv('DEBUG', 'False') == 'True'