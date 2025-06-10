import requests
import json
import time
import logging
from datetime import datetime
from config import Config
from database import Database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('WeChatCrawler')


class WeChatCrawler:
    def __init__(self):
        self.url = Config.WECHAT_API_URL
        self.headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()

    def fetch_all_active_accounts(self):
        """获取所有活跃账号的视频数据"""
        logger.info("🚀 开始获取所有活跃账号的视频数据...")
        db = Database()
        accounts = db.get_wechat_accounts(only_active=True)
        total_count = 0

        if not accounts:
            logger.warning("⚠️ 没有找到活跃账号")
            return total_count

        for account in accounts:
            logger.info(f"🔄 正在获取账号: {account['nickname'] or account['username']} (ID: {account['id']})")
            count = self.fetch_account_videos(account['id'], account['username'])
            total_count += count
            time.sleep(1)  # 账号间请求间隔

        logger.info(f"✅ 获取完成! 总计获取 {len(accounts)} 个账号的 {total_count} 条视频数据")
        return total_count

    def fetch_account_videos(self, account_id, username):
        """获取指定账号的视频数据并存储"""
        logger.info(f"🔗 开始获取用户视频: account_id={account_id}, username={username}")

        db = Database()
        account_info = db.get_account_by_id(account_id)
        if not account_info:
            logger.error(f"❌ 账号ID {account_id} 不存在!")
            return 0

        last_buffer = ""
        videos_count = 0
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            # 准备请求数据
            payload = {
                "key": Config.WECHAT_API_KEY,
                "username": username,
                "last_buffer": last_buffer
            }

            try:
                logger.info(f"📤 请求接口: {self.url}, last_buffer: '{last_buffer}'")

                response = self.session.post(
                    self.url,
                    headers=self.headers,
                    data=json.dumps(payload),
                    timeout=15
                )

                logger.info(f"📥 收到响应: HTTP {response.status_code}")

                # 处理HTTP错误
                if response.status_code != 200:
                    logger.error(f"❌ 请求失败: HTTP {response.status_code}, {response.text[:300]}")
                    time.sleep(2 ** retry_count)  # 指数退避
                    retry_count += 1
                    continue

                # 解析响应
                try:
                    response_data = response.json()
                except ValueError as e:
                    logger.error(f"❌ JSON解析失败: {e}, 响应内容: {response.text[:300]}...")
                    retry_count += 1
                    continue

                # 检查接口响应状态
                if response_data.get('code') != 200:
                    error_msg = response_data.get('msg', '未知错误')
                    logger.error(f"❌ 接口返回错误: {error_msg}")
                    break

                # 获取data部分
                data = response_data.get('data', {})

                # 获取视频列表
                videos = data.get('video_list', [])
                if not videos:
                    logger.info("ℹ️ 该账号没有视频数据")
                    break

                videos_count += len(videos)
                logger.info(f"🎬 获取到 {len(videos)} 条视频数据")

                # 处理视频数据
                for i, video in enumerate(videos):
                    try:
                        # 获取时间戳，确保值有效
                        publish_timestamp = video.get('create_time')
                        if not publish_timestamp or publish_timestamp <= 0:
                            publish_timestamp = int(time.time())  # 如果时间戳无效，使用当前时间
                            logger.warning(f"⚠️ 视频 {i + 1} 创建时间无效，使用当前时间")

                        # 创建视频数据对象
                        video_info = {
                            'title': video.get('title', '无标题'),
                            'publish_time': datetime.fromtimestamp(publish_timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                            'likes': video.get('like_count', 0),
                            'shares': video.get('forward_count', 0),
                            'comments': video.get('comment_count', 0),
                            'region': video.get('poster_location', '未知')
                        }

                        # 记录视频信息
                        logger.info(
                            f"  {i + 1}. {video_info['title'][:20]}... (点赞: {video_info['likes']}, 转发: {video_info['shares']}, 地区: {video_info['region']})")

                        # 存储视频数据
                        if not db.insert_wechat_video(account_id, video_info):
                            logger.warning("⚠️ 视频存储失败")

                    except KeyError as e:
                        logger.error(f"❌ 视频数据缺少关键字段: {e}, 视频数据: {video}")
                    except Exception as e:
                        logger.error(f"❌ 处理视频失败: {str(e)}")

                # 更新last_buffer用于下次请求
                last_buffer = data.get('last_buffer', '')
                logger.info(f"📝 获取到的last_buffer: '{last_buffer}'")

                # 检查是否还有更多数据
                continue_flag = data.get('continue_flag', 0)
                if not last_buffer or continue_flag == 0:
                    logger.info(f"✅ 账号 {username} 获取完成，共获取 {videos_count} 条视频数据")
                    break

                # 分页请求间隔
                time.sleep(1)

            except requests.Timeout:
                logger.error("⌛ 请求超时")
                retry_count += 1
                time.sleep(5)
            except requests.ConnectionError:
                logger.error("🔌 网络连接错误")
                retry_count += 1
                time.sleep(10)
            except Exception as e:
                logger.error(f"❌ 未知错误: {e}")
                retry_count += 1
                time.sleep(5)

        # 检查是否超过重试次数
        if retry_count >= max_retries:
            logger.error(f"❌ 账号 {username} 请求失败次数超过限制，停止尝试")

        return videos_count