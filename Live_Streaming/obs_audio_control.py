import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from config import AUDIO_CONFIG
import logging
from logging_config import setup_logging

class AudioController:
    def __init__(self):
        self.output_device_index = AUDIO_CONFIG["output_device_index"]  # WASAPI版本的CABLE Input设备索引
        self.logger = setup_logging('audio_controller')
        
    def list_audio_devices(self):
        """列出所有可用的音频设备"""
        devices = sd.query_devices()
        self.logger.info("\n可用的音频设备：")
        for i, device in enumerate(devices):
            if device['max_output_channels'] > 0:  # 只显示输出设备
                self.logger.info(f"{i}: {device['name']}")
                self.logger.info(f"  - 通道数: {device['max_output_channels']}")
                self.logger.info(f"  - 默认采样率: {device['default_samplerate']}")
                if i == self.output_device_index:
                    self.logger.info(f"  - 当前使用的设备")
            
    def play_audio(self, audio_file_path):
        """播放音频文件到CABLE Input"""
        if not os.path.exists(audio_file_path):
            self.logger.error(f"音频文件未找到: {audio_file_path}")
            return False
            
        try:
            # 读取音频文件
            data, samplerate = sf.read(audio_file_path)
            self.logger.info(f"音频文件信息:")
            self.logger.info(f"- 采样率: {samplerate}")
            self.logger.info(f"- 通道数: {data.shape[1] if len(data.shape) > 1 else 1}")
            self.logger.info(f"- 时长: {len(data)/samplerate:.2f}秒")
            
            # 确保数据是二维数组（立体声）
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            
            # 转换为int16格式
            data = (data * 32767).astype(np.int16)
            
            # 使用sounddevice直接播放
            self.logger.info(f"使用设备播放: {sd.query_devices(self.output_device_index)['name']}")
            sd.play(data, samplerate, device=self.output_device_index)
            sd.wait()  # 等待播放完成
            self.logger.info("音频播放完成")
            return True
            
        except Exception as e:
            self.logger.error(f"播放音频时出错: {str(e)}")
            return False
            
    def stop_audio(self):
        """停止音频播放"""
        try:
            sd.stop()
            return True
        except Exception as e:
            self.logger.error(f"停止音频时出错: {str(e)}")
            return False

# 使用示例
if __name__ == "__main__":
    controller = AudioController()
    # 列出所有可用的音频设备
    controller.list_audio_devices()
    # 播放音频文件
    audio_file = os.path.join(os.path.dirname(__file__), "香奈美语音-006CN.mp3")  # 替换为实际的音频文件路径
    controller.play_audio(audio_file)