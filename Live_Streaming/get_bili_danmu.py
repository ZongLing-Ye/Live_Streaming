import requests
import sys
import time
from config import BILIBILI_CONFIG
from logging_config import setup_logging

class Danmu():
    def __init__(self):
        self.logger = setup_logging('bili_danmu')
        # 定义三个列表存放爬取的三种数据
        self.chatlist = []
        self.chatname = []
        self.timelist = []
        
        # 使用集合存储消息ID和内容的组合
        self.processed_msgs = set()
        # 清理计数器
        self.clear_counter = 0
        # 每处理100条消息清理一次历史记录
        self.CLEAR_THRESHOLD = 100

        # 弹幕url
        self.url = 'https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory'
        # 定义请求头
        self.headers = {
            'Host': 'api.live.bilibili.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0',
        }
        
        # 从配置文件获取房间ID
        self.room_id = BILIBILI_CONFIG.get("room_id")
        if not self.room_id:
            self.logger.error("未设置B站直播间ID，请在配置文件中设置BILIBILI_CONFIG['room_id']")
            raise ValueError("未设置B站直播间ID")
            
        # 定义POST传递的参数
        self.data = {
            'roomid': str(self.room_id),
            'csrf_token': '',
            'csrf': '',
            'visit_id': '',
        }
        self.logger.info(f"已初始化弹幕获取器，房间ID: {self.room_id}")

    def _generate_msg_key(self, nickname, text, timeline):
        """生成消息唯一标识,使用昵称、内容和时间的组合"""
        return f"{nickname}:{text}:{timeline}"

    def _parse_timeline(self, timeline):
        """解析B站返回的时间格式
        处理可能的重复日期问题，返回标准格式的时间字符串
        """
        try:
            # 移除可能重复的日期部分
            if timeline.count('2025-05-14') > 1:
                timeline = timeline.replace('2025-05-14 ', '', 1)
            # 解析时间字符串
            time_obj = time.strptime(timeline, '%Y-%m-%d %H:%M:%S')
            # 返回格式化的时间字符串
            return time.strftime('%Y-%m-%d %H:%M:%S', time_obj)
        except Exception as e:
            self.logger.error(f"解析时间失败: {e}")
            # 如果解析失败，返回当前时间
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def get_danmu(self):
        """获取直播间弹幕"""
        try:
            html = requests.post(url=self.url, headers=self.headers, data=self.data).json()
            room_data = html['data']['room']
            
            new_messages = []
            for content in room_data:
                nickname = content['nickname']
                text = content['text']
                timeline = self._parse_timeline(content['timeline'])
                
                # 生成消息唯一标识
                msg_key = self._generate_msg_key(nickname, text, timeline)
                
                # 检查是否已处理过这条消息
                if msg_key not in self.processed_msgs:
                    self.chatlist.append(text)
                    self.chatname.append(nickname)
                    self.timelist.append(timeline)
                    new_messages.append(f"用户: {nickname}, 内容: {text}, 时间: {timeline}")
                    
                    # 记录已处理的消息标识
                    self.processed_msgs.add(msg_key)
                    
                    # 增加计数器
                    self.clear_counter += 1
                # else:
                #     self.logger.info(f"检测到重复弹幕 - 用户: {nickname}, 内容: {text}")
            
            # 如果处理的消息数量达到阈值，清理历史记录
            if self.clear_counter >= self.CLEAR_THRESHOLD:
                self.processed_msgs.clear()
                self.clear_counter = 0
                self.logger.info("已清理历史消息记录")
            
            if new_messages:
                self.logger.info(f"获取到 {len(new_messages)} 条新弹幕:")
                for msg in new_messages:
                    self.logger.info(msg)
            
        except Exception as e:
            self.logger.error(f"获取弹幕失败: {e}")
                
    def clear_events(self):
        """清空事件列表"""
        self.chatlist.clear()
        self.chatname.clear()
        self.timelist.clear()

    def start(self):
        """启动弹幕获取器"""
        self.processed_msgs.clear()  # 清空消息记录
        self.clear_counter = 0  # 重置计数器
        self.logger.info("B站弹幕获取器已启动")
        return True

    def stop(self):
        """停止弹幕获取器"""
        self.processed_msgs.clear()  # 清空消息记录
        self.clear_counter = 0  # 重置计数器
        self.logger.info("B站弹幕获取器已停止")
        return True