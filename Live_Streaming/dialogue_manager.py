import time
import os
import json
from logging_config import setup_logging
import logging

class DialogueType:
    USER_CHAT = "user_chat"        # 用户实际对话
    IDLE_CHAT = "idle_chat"        # 空闲时的系统对话
    SYSTEM_PROMPT = "system"       # 系统提示词
    AD_RESPONSE = "Advertisement"            # 广告回复

class HistoryManager:
    def __init__(self):
        self.logger = setup_logging('history_manager')
        self.max_tokens = 1500  # 预留空间给新对话
        self.history_cache = []  # 内存中缓存最近的对话
        self.history_file = "danmu_history/bili_history.txt"
        
        # 确保目录存在
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        
        # 如果文件不存在，创建空文件
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                pass
                
        self.load_history()
    
    def load_history(self):
        """从文件加载历史记录到缓存"""
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-10:]:  # 只加载最近5组对话（10行）
                    try:
                        data = json.loads(line.strip())
                        self.history_cache.append(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            self.logger.error(f"加载历史记录失败: {e}")
            self.history_cache = []

    def save_history(self):
        """将缓存中的历史记录保存到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            # 使用追加模式写入文件
            with open(self.history_file, "a", encoding="utf-8") as f:
                # 只写入最新的记录
                if self.history_cache:
                    latest_record = self.history_cache[-1]
                    f.write(json.dumps(latest_record, ensure_ascii=False) + "\n")
            self.logger.info(f"历史记录已保存到文件: {self.history_file}")
        except Exception as e:
            self.logger.error(f"保存历史记录失败: {e}")

    def add_history(self, role, content, username="", dialogue_type=None):
        """添加新对话到历史记录"""
        try:
            entry = {
                "role": role,
                "content": content,
                "username": username,
                "timestamp": time.time(),
                "dialogue_type": dialogue_type
            }
            
            self.history_cache.append(entry)
            self.logger.info(f"添加新对话到历史记录: {entry}")
            
            # 保持缓存大小在10条对话以内
            if len(self.history_cache) > 10:
                self.history_cache.pop(0)
                
            # 保存到文件
            self.save_history()
        except Exception as e:
            self.logger.error(f"添加历史记录失败: {e}")

    def get_formatted_history(self):
        """返回格式化的历史记录用于对话"""
        formatted = []
        for item in self.history_cache:
            if item["username"]:
                formatted.append(f"{item['username']}: {item['content']}")
            else:
                formatted.append(f"{item['role']}: {item['content']}")
        return "\n".join(formatted)


class DialogueSystem:
    def __init__(self):
        self.logger = setup_logging('dialogue_system')
        self.history_manager = HistoryManager()
        
    def get_dialogue_history(self):
        """获取对话历史记录"""
        return self.history_manager.history_cache
        
    def process_message(self, content, username, dialogue_type):
        """
        处理对话消息
        :param content: 消息内容
        :param username: 用户名
        :param dialogue_type: 对话类型（DialogueType中的类型）
        :return: AI的回复
        """
        try:        
            # 获取历史记录
            history = self.history_manager.get_formatted_history()
            
            # 构建完整的上下文
            context = f"""历史对话：
{history}

请根据以上对话历史，特别是最近的用户提问，给出合适的回答。
注意：如果用户重复提问，请确保回答的一致性。"""
            
            # 根据对话类型设置角色
            role = "主播" if dialogue_type == DialogueType.AD_RESPONSE else "user"
            
            # 保存到历史记录
            self.history_manager.add_history(role, content, username, dialogue_type)
            
            return context
            
        except Exception as e:
            self.logger.error(f"处理对话消息失败: {e}")
            return f"\n{content}"  # 返回简单的上下文
            
    def add_response(self, response, dialogue_type):
        """
        添加AI的回复到历史记录
        :param response: AI的回复
        :param dialogue_type: 对话类型
        """
        self.history_manager.add_history("assistant", response, "", dialogue_type) 