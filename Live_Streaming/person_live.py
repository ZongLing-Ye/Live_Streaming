import get_bili_danmu as gd
import os
import sys
import time
import llm
import tts
from pathlib import Path
import pygame
import tts_c
from pydub import AudioSegment
from pydub.playback import play
import wave
import contextlib
import shutil
import tempfile
import msvcrt
import uuid
from obs_audio_control import AudioController
import threading
from queue import Queue, Empty
from gradio_interface import create_interface, LogHandler
import gradio as gr
import traceback
from config import PLATFORM_CONFIG
from logging_config import setup_logging
from dialogue_manager import DialogueSystem, DialogueType
from ad_generator import AdGenerator

# 初始化日志系统
logger = setup_logging('person_live')

class LiveStreamManager:
    def __init__(self):
        self.logger = setup_logging('live_manager')
        self.audio_controller = AudioController()
        
        # 语音生成任务队列
        self.tts_priority_queue = Queue(maxsize=2)  # 优先级语音生成队列
        self.tts_normal_queue = Queue(maxsize=3)    # 普通语音生成队列
        
        # 语音播放队列
        self.normal_voice_queue = Queue(maxsize=3)  # 普通弹幕回复队列
        self.priority_voice_queue = Queue(maxsize=2) # 优先级队列（广告等）
        
        self.queue_lock = threading.Lock()
        
        # 对话管理系统
        self.dialogue_system = DialogueSystem()
        
        # 直播状态控制
        self.is_running = False
        self.voice_thread = None
        self.player_thread = None
        self.queue_maintainer = None
        self.tts_generator_thread = None
        
        # 线程控制
        self.should_stop = threading.Event()
        
        # TTS 重试控制
        self.tts_retry_count = 0
        self.max_tts_retries = 3
        self.tts_retry_delay = 2
        self.user_prompt = ""
        
        # 平台弹幕获取器
        self.bili_danmu = None
        
        # 广告播放控制
        self.ad_play_probability = 0  # 广告播放概率
        self.danmu_reply_count = 0    # 弹幕回复计数
        self.probability_increment = 0.2  # 每次增加的概率（20%）
        self.original_product_info = None  # 保存原始商品信息
        
        # 初始化弹幕获取器
        if PLATFORM_CONFIG["bilibili_enabled"]:
            self.bili_danmu = gd.Danmu()

    def reset_ad_probability(self):
        """重置广告播放概率和弹幕计数"""
        self.ad_play_probability = 0
        self.danmu_reply_count = 0
        
    def increase_ad_probability(self):
        """增加广告播放概率"""
        self.danmu_reply_count += 1
        old_probability = self.ad_play_probability
        self.ad_play_probability = min(1.0, self.danmu_reply_count * self.probability_increment)
        # self.logger.info(f"广告播放概率从 {old_probability:.2f} 增加到 {self.ad_play_probability:.2f}")
        
    def should_play_ad(self):
        """判断是否应该播放广告"""
        import random
        return random.random() < self.ad_play_probability
        
    def generate_new_ad(self):
        """根据历史对话生成新的广告词"""
        if not self.original_product_info:
            return None
            
        # 获取历史对话记录
        dialogue_history = self.dialogue_system.get_dialogue_history()
        
        # 生成新的广告词
        ad_generator = AdGenerator()
        new_ad = ad_generator.generate_ad_copy_with_history(
            self.original_product_info,
            dialogue_history,
            self.dialogue_system
        )
        
        return new_ad

    def tts_generator(self):
        """语音生成线程"""
        while not self.should_stop.is_set():
            try:
                text = None
                is_priority = False
                
                # 优先检查优先级生成队列
                try:
                    text, is_priority = self.tts_priority_queue.get_nowait()
                    self.logger.info("从优先级生成队列获取文本")
                except Empty:
                    # 如果优先级队列为空，则从普通队列获取
                    try:
                        text, is_priority = self.tts_normal_queue.get(timeout=1)
                        self.logger.info("从普通生成队列获取文本")
                    except Empty:
                        continue
                
                if text is None:
                    continue
                    
                try:
                    # 生成语音
                    if PLATFORM_CONFIG["tts_c_enabled"]:
                        voice_file = tts_c.tts_c(text)
                    elif PLATFORM_CONFIG["tts_enabled"]:
                        voice_file = tts.tts(text)

                    
                    # 将生成的语音放入对应的播放队列
                    if is_priority:
                        self.priority_voice_queue.put(voice_file)
                        self.logger.info("语音文件已加入优先级播放队列")
                    else:
                        self.normal_voice_queue.put(voice_file)
                        self.logger.info("语音文件已加入普通播放队列")
                        
                    # 标记任务完成
                    if is_priority:
                        self.tts_priority_queue.task_done()
                    else:
                        self.tts_normal_queue.task_done()
                        
                except Exception as e:
                    self.logger.error(f"生成语音失败: {e}")
                    # 标记任务完成，即使失败也要移出队列
                    if is_priority:
                        self.tts_priority_queue.task_done()
                    else:
                        self.tts_normal_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"语音生成线程出错: {e}")
                time.sleep(1)

    def generate_and_queue_voice(self, text, is_priority=False):
        """
        将文本加入语音生成队列
        :param text: 要转换为语音的文本
        :param is_priority: 是否为优先级内容（如广告）
        :return: 是否成功加入队列
        """
        if not self.is_running:
            return False
            
        try:
            # 根据优先级选择生成队列
            if is_priority:
                target_queue = self.tts_priority_queue
                queue_type = "优先级生成队列"
            else:
                target_queue = self.tts_normal_queue
                queue_type = "普通生成队列"
            
            # 将文本和优先级信息加入队列
            target_queue.put((text, is_priority))
            self.logger.info(f"文本已加入{queue_type}")
            
            return True
        except Exception as e:
            self.logger.error(f"加入语音生成队列失败: {e}")
            return False

    def start_live(self):
        """启动直播功能"""
        if self.is_running:
            self.logger.warning("直播已经在运行中")
            return "直播已经在运行中"
            
        try:
            # 检查必要文件
            base_dir = os.path.dirname(os.path.abspath(__file__))
            required_files = {
                '/danmu_history/bili_history.txt': '弹幕历史记录文件'
            }
                
            # 重置停止标志
            self.should_stop.clear()
            self.is_running = True
            
            # 启动弹幕获取器
            if PLATFORM_CONFIG.get("bilibili_enabled", False) and self.bili_danmu:
                try:
                    if not self.bili_danmu.start():
                        self.logger.error("B站弹幕获取器启动失败")
                        return "B站弹幕获取器启动失败"
                    # 获取初始弹幕记录
                    self.logger.info("正在获取B站历史弹幕记录...")
                    self.bili_danmu.get_danmu()
                    self.bili_danmu.clear_events()  # 清空初始弹幕列表
                except Exception as e:
                    self.logger.error(f"启动B站弹幕获取器时出错: {e}")
                    return f"启动B站弹幕获取器时出错: {e}"
            
            # 启动语音生成线程
            self.tts_generator_thread = threading.Thread(target=self.tts_generator, name="tts_generator")
            self.tts_generator_thread.daemon = True
            self.tts_generator_thread.start()
            self.logger.info("语音生成线程已启动")
            
            # 启动语音播放线程
            self.player_thread = threading.Thread(target=self.voice_player, name="voice_player")
            self.player_thread.daemon = True
            self.player_thread.start()
            self.logger.info("语音播放线程已启动")
            
            # 启动队列维护线程
            self.queue_maintainer = threading.Thread(target=self.maintain_voice_queue, name="queue_maintainer")
            self.queue_maintainer.daemon = True
            self.queue_maintainer.start()
            self.logger.info("队列维护线程已启动")
            
            # 启动直播主循环
            self.voice_thread = threading.Thread(target=self.run_live, name="run_live")
            self.voice_thread.daemon = True
            self.voice_thread.start()
            self.logger.info("直播主循环已启动")
            
            time.sleep(0.5)  # 等待所有线程启动
            self.logger.info("所有线程已成功启动")
            return "直播已启动"
            
        except Exception as e:
            self.logger.error(f"启动直播失败: {e}")
            self.stop_live()
            return f"启动直播失败: {e}"

    def stop_live(self):
        """停止直播功能"""
        if not self.is_running:
            self.logger.warning("直播未在运行")
            return "直播未在运行"
        
        try:
            # 设置停止标志
            self.should_stop.set()
            self.is_running = False
            self.logger.info(f"直播状态已设置为停止")
            
            # 停止弹幕获取器
            if self.bili_danmu:
                self.bili_danmu.stop()
            # 等待线程结束
            threads_to_join = [
                (self.voice_thread, "语音生成线程"),
                (self.player_thread, "播放器线程"),
                (self.queue_maintainer, "队列维护线程")
            ]
            
            for thread, thread_name in threads_to_join:
                if thread and thread.is_alive():
                    self.logger.info(f"等待{thread_name}结束...")
                    thread.join(timeout=5)
                    if thread.is_alive():
                        self.logger.warning(f"{thread_name}未能在5秒内结束")
            
            # 清空队列
            while not self.normal_voice_queue.empty():
                try:
                    self.normal_voice_queue.get_nowait()
                    self.normal_voice_queue.task_done()
                except Empty:
                    pass
            
            while not self.priority_voice_queue.empty():
                try:
                    self.priority_voice_queue.get_nowait()
                    self.priority_voice_queue.task_done()
                except Empty:
                    pass
            
            # 重置所有状态
            self.voice_thread = None
            self.player_thread = None
            self.queue_maintainer = None
            self.should_stop.clear()
            
            self.logger.info("直播已停止")
            return "直播已停止"
        except Exception as e:
            error_msg = f"停止直播失败: {str(e)}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            return error_msg

    def is_file_locked(self, filepath):
        """检查文件是否被锁定"""
        try:
            with open(filepath, 'rb') as f:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                return False
        except IOError:
            return True

    def wait_for_file_unlock(self, filepath, timeout=5):
        """等待文件解锁，最多等待timeout秒"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_file_locked(filepath):
                return True
            time.sleep(0.1)
        return False

    def get_audio_duration(self, file_path):
        """获取音频文件的实际长度"""
        try:
            with contextlib.closing(wave.open(file_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
                return duration
        except Exception as e:
            self.logger.error(f"无法获取音频长度: {e}")
            return 3.0  # 默认返回3秒

    def safe_play(self, audio_path):
        """更安全的音频播放函数"""
        if not Path(audio_path).exists():
            print(f"错误：文件不存在 - {audio_path}")
            return False
        pygame.mixer.init()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        # 检测是否播放完成
        while pygame.mixer.music.get_busy():
            time.sleep(0.3)  # 避免 CPU 占用过高
        print("音频播放完成！")
        time.sleep(0.3)
        pygame.mixer.quit()
        # os.startfile(audio_path)
        os.remove(audio_path)


    def voice_player(self):
        """语音播放线程"""
        while not self.should_stop.is_set():
            try:
                voice_file = None
                is_priority = False
                
                # 优先检查优先级队列
                try:
                    voice_file = self.priority_voice_queue.get_nowait()
                    is_priority = True
                    self.logger.info("从优先级队列获取语音文件")
                except Empty:
                    # 如果优先级队列为空，则从普通队列获取
                    try:
                        voice_file = self.normal_voice_queue.get(timeout=1)
                        self.logger.info("从普通队列获取语音文件")
                    except Empty:
                        continue  # 两个队列都为空，继续等待
                
                if voice_file is None:  # 退出信号
                    break
                    
                # 播放语音
                if self.safe_play(voice_file):
                    self.logger.info("语音播放成功")
                else:
                    self.logger.warning("语音播放失败")
                
                # 标记任务完成
                if is_priority:
                    self.priority_voice_queue.task_done()
                    self.logger.info(f"优先级语音播放完成，当前优先级队列大小: {self.priority_voice_queue.qsize()}")
                else:
                    self.normal_voice_queue.task_done()
                    self.logger.info(f"普通语音播放完成，当前普通队列大小: {self.normal_voice_queue.qsize()}")
                    
            except Exception as e:
                self.logger.error(f"语音播放出错: {e}")
                if is_priority:
                    self.priority_voice_queue.task_done()
                else:
                    self.normal_voice_queue.task_done()

    def run_live(self):
        """运行直播主循环"""
        self.logger.info("直播主循环开始运行")
        last_check_time = time.time()
        
        try:
            while not self.should_stop.is_set():
                try:
                    current_time = time.time()
                    if current_time - last_check_time >= 5:
                        last_check_time = current_time
                    
                    if not self.is_running:
                        self.logger.info("直播未运行，主循环等待中...")
                        time.sleep(1)
                        continue
                                    
                    # 检查是否应该播放广告
                    if self.should_play_ad():
                        # 生成新的广告词
                        new_ad = self.generate_new_ad()
                        if new_ad:
                            # 生成并播放广告
                            if self.generate_and_queue_voice(new_ad, is_priority=True):
                                # 将广告词添加到对话历史
                                self.dialogue_system.process_message(
                                    new_ad,
                                    "主播",
                                    DialogueType.AD_RESPONSE
                                )
                                # 重置概率
                                self.reset_ad_probability()
                            else:
                                self.logger.warning("广告语音生成失败")

                    # 处理B站弹幕
                    if self.bili_danmu:
                        self.bili_danmu.get_danmu()
                        
                        if self.bili_danmu.chatlist:
                            # 检查是否有新弹幕需要处理
                            current_msg = self.bili_danmu.chatlist[0]
                            current_user = self.bili_danmu.chatname[0]
                            
                            self.logger.info(f"收到B站弹幕 - 用户: {current_user}, 内容: {current_msg}")
                            
                            # 使用对话系统处理消息
                            context = self.dialogue_system.process_message(
                                current_msg,
                                current_user,
                                DialogueType.USER_CHAT
                            )
                            
                            # 生成回复
                            response = llm.gpt(current_msg, context, current_user)
                            
                            # 将回复添加到历史记录
                            self.dialogue_system.add_response(response, DialogueType.USER_CHAT)
                            
                            self.logger.info(f"AI回复: {response}")
                            self.logger.info(f"现在主播正在回应{current_user}的话语")
                            
                            # 生成语音并加入队列
                            if self.generate_and_queue_voice(response, is_priority=False):
                                self.logger.info("B站弹幕回复语音已加入普通队列")
                                # 增加广告播放概率
                                self.increase_ad_probability()
                            else:
                                self.logger.warning("B站弹幕回复语音生成失败")
                            
                            # 处理完成后移除该弹幕
                            self.bili_danmu.chatlist.pop(0)
                            self.bili_danmu.chatname.pop(0)
                            
                            # 添加短暂延时，避免过于频繁的处理
                            time.sleep(0.1)
                        
                        self.bili_danmu.clear_events()
                 
                    time.sleep(0.1)  # 避免CPU占用过高
                
                except Exception as e:
                    self.logger.error(f"直播主循环处理弹幕出错: {str(e)}", exc_info=True)
                    time.sleep(1)  # 出错后等待一段时间再继续
        
        except Exception as e:
            self.logger.error(f"直播主循环异常退出: {str(e)}", exc_info=True)
        finally:
            # 在停止前处理剩余的消息       
            self.logger.info(f"直播主循环已停止")
            self.is_running = False

    def _process_message(self, content, username):
        """处理单条弹幕消息"""
        try:
            self.logger.info(f"开始处理弹幕消息 - 用户: {username}, 内容: {content}")
            
            # 使用对话系统处理消息
            context = self.dialogue_system.process_message(content, username, DialogueType.USER_CHAT)
            
            # 生成AI回复
            response = llm.gpt(content, context)
            
            # 将回复添加到历史记录
            self.dialogue_system.add_response(response, DialogueType.USER_CHAT)
            
            # 生成语音并加入普通队列
            if self.generate_and_queue_voice(response, is_priority=False):
                self.logger.info("弹幕回复语音已加入普通队列")
            else:
                self.logger.warning("弹幕回复语音生成或加入队列失败")
            
            self.logger.info(f"完成处理弹幕消息 - 用户: {username}")
        
        except Exception as e:
            self.logger.error(f"处理弹幕消息失败 - 用户: {username}, 内容: {content}", exc_info=True)

    def maintain_voice_queue(self):
        """维护语音队列的线程"""
        while not self.should_stop.is_set():
            try:
                # 检查队列状态
                with self.queue_lock:
                    normal_size = self.normal_voice_queue.qsize()
                    priority_size = self.priority_voice_queue.qsize()
                    
                    # 记录队列状态
                    if normal_size > 0 or priority_size > 0:
                        self.logger.info(f"当前队列状态 - 普通队列: {normal_size}, 优先级队列: {priority_size}")
                                    
                time.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                self.logger.error(f"维护语音队列时出错: {e}")
                time.sleep(1)  # 出错后等待一秒再继续

def create_live_interface(live_manager):
    """创建直播界面"""
    ad_generator = AdGenerator()
    
    with gr.Blocks(title="直播助手") as interface:
        gr.Markdown("# 直播助手")
        
        with gr.Row():
            start_btn = gr.Button("开始直播", variant="primary")
            stop_btn = gr.Button("停止直播", variant="stop")
            
        # 添加广告生成部分
        gr.Markdown("## 广告词生成")
        with gr.Row():
            product_info_box = gr.Textbox(
                label="商品信息",
                placeholder="请输入商品的基本信息，如：品牌、价格、特点、适用人群等",
                lines=3
            )
        
        with gr.Row():
            generate_ad_btn = gr.Button("生成并播放广告", variant="primary")
            
        with gr.Row():
            ad_result = gr.Textbox(label="生成的广告词", lines=2, interactive=False)
        
        with gr.Row():
            log_text = gr.Textbox(label="直播日志", lines=20, interactive=False)
            log_handler = LogHandler(log_text)
            logger.addHandler(log_handler)
        
        def on_start():
            return live_manager.start_live()
        
        def on_stop():
            return live_manager.stop_live()
            
        def on_generate_ad(product_info):
            try:
                # 生成广告词
                ad_copy = ad_generator.generate_ad_copy(product_info)
                
                # 如果返回的是提示信息（空输入的情况），直接返回
                if ad_copy == "请输入商品信息后再生成广告词":
                    return ad_copy
                
                # 保存原始商品信息
                live_manager.original_product_info = product_info
                
                # 重置广告播放概率
                live_manager.reset_ad_probability()
                
                # 将广告词加入语音生成队列
                if live_manager.generate_and_queue_voice(ad_copy, is_priority=True):
                    logger.info("广告语音已加入优先级播放队列")
                    # 将广告词添加到对话历史
                    live_manager.dialogue_system.process_message(
                        ad_copy,
                        "主播",
                        DialogueType.AD_RESPONSE
                    )
                else:
                    logger.warning("广告语音生成失败")
                
                return f"广告生成成功！\n\n{ad_copy}"
            except Exception as e:
                logger.error(f"广告生成失败：{str(e)}")
                return f"广告生成失败：{str(e)}"
        
        start_btn.click(fn=on_start, inputs=[], outputs=[log_text])
        stop_btn.click(fn=on_stop, inputs=[], outputs=[log_text])
        generate_ad_btn.click(fn=on_generate_ad, inputs=[product_info_box], outputs=[ad_result])
    
    return interface

if __name__ == "__main__":
    try:
        # 设置标准输出编码
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            
        # 创建直播管理器
        live_manager = LiveStreamManager()
        
        # 创建配置界面
        config_interface = create_interface()
        # 创建直播界面
        live_interface = create_live_interface(live_manager)
        
        # 启动界面
        with gr.TabbedInterface(
            [config_interface, live_interface],
            ["配置", "直播"]
        ) as interface:
            interface.launch(
                server_name="0.0.0.0",  # 允许外部访问
                server_port=7892,       # 让系统自动选择可用端口
                share=False,           # 不需要分享链接
                inbrowser=True,         # 自动打开浏览器
                show_error=True,        # 显示详细错误信息
                quiet=True             # 减少控制台输出
            )
    except Exception as e:
        logger.error(f"启动界面时出错: {e}")
        sys.exit(1)