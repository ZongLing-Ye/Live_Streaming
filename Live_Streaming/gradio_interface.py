import gradio as gr
import json
import os
import sys
import logging
from datetime import datetime
import config
from config import BILIBILI_CONFIG, PLATFORM_CONFIG
from logging_config import setup_logging

# 初始化日志系统
logger = setup_logging('gradio_interface')

# 设置日志
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_file = os.path.join(log_dir, f"interface_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class LogHandler(logging.Handler):
    def __init__(self, text_box):
        super().__init__()
        self.text_box = text_box
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        try:
            msg = self.format(record)
            # 使用value属性直接更新文本框
            if hasattr(self.text_box, 'value'):
                current_value = self.text_box.value if self.text_box.value else ""
                self.text_box.value = current_value + msg + "\n"
            else:
                print(msg)  # 如果无法更新文本框，至少打印到控制台
        except Exception:
            self.handleError(record)

class ConfigManager:
    def __init__(self):
        self.config_file = os.path.join(os.path.dirname(__file__), "config.py")
        try:
            self.load_config()
        except Exception as e:
            logger.error(f"初始化配置管理器时出错: {e}", exc_info=True)
            raise
        
    def load_config(self):
        """从config.py加载配置"""
        try:
            # 获取所有配置
            self.llm_config = config.LLM_CONFIG.copy()
            self.tts_config = config.TTS_CONFIG.copy()
            self.tts_c_config = config.TTS_C_CONFIG.copy()
            self.audio_config = config.AUDIO_CONFIG.copy()
            self.bilibili_config = config.BILIBILI_CONFIG.copy()
            self.platform_config = config.PLATFORM_CONFIG.copy()
            self.voice_prompt = config.VOICE_PROMPT.copy()
            logger.info("配置加载成功")
        except Exception as e:
            logger.error(f"加载配置时出错: {e}", exc_info=True)
            raise
            
    def save_config(self, config_dict):
        """保存配置到config.py"""
        try:
            # 读取现有文件内容
            with open(self.config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 更新每个配置部分
            for section, section_dict in config_dict.items():
                # 将字典转换为格式化的字符串
                section_str = f"{section} = {repr(section_dict)}\n"
                
                # 查找配置部分的位置
                start = content.find(f"{section} =")
                if start != -1:
                    # 找到配置部分的结束位置
                    end = content.find("\n\n", start)
                    if end == -1:
                        end = len(content)
                    
                    # 替换配置部分
                    content = content[:start] + section_str + content[end:]
                else:
                    # 如果找不到配置部分，添加到文件末尾
                    content += f"\n{section_str}"
            
            # 写入更新后的内容
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重新加载配置
            self.load_config()
            
            logger.info("配置保存成功")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

def create_interface():
    """创建配置界面"""
    config_manager = ConfigManager()
    
    with gr.Blocks(title="直播助手配置") as interface:
        gr.Markdown("# 直播助手配置")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("## 平台选择")
                bilibili_enabled = gr.Checkbox(label="启用B站直播", value=PLATFORM_CONFIG["bilibili_enabled"])
                tts_selection = gr.Radio(
                    label="TTS选择",
                    choices=["TTS", "TTS_C"],
                    value="TTS_C" if PLATFORM_CONFIG.get("tts_c_enabled", False) else "TTS"
                )

        with gr.Row():
            with gr.Column():
                gr.Markdown("## B站配置")
                room_id = gr.Textbox(label="B站直播间ID", value=BILIBILI_CONFIG["room_id"])
                save_btn = gr.Button("保存直播配置", variant="primary")
                status = gr.Textbox(label="配置状态", interactive=False)
        
        
        with gr.Tab("LLM配置"):
            with gr.Row():
                llm_api_key = gr.Textbox(label="API Key", value=config_manager.llm_config.get("api_key", ""), type="password")
                llm_base_url = gr.Textbox(label="Base URL", value=config_manager.llm_config.get("base_url", ""))
            with gr.Row():
                llm_model = gr.Textbox(label="Model", value=config_manager.llm_config.get("model", ""))
                llm_temperature = gr.Number(label="Temperature", value=config_manager.llm_config.get("temperature", 0.7))
            with gr.Row():
                llm_top_p = gr.Number(label="Top P", value=config_manager.llm_config.get("top_p", 0.9))
                llm_presence_penalty = gr.Number(label="Presence Penalty", value=config_manager.llm_config.get("presence_penalty", 0.0))
            with gr.Row():
                llm_top_k = gr.Number(label="Top K", value=config_manager.llm_config.get("top_k", 20))
                llm_enable_thinking = gr.Checkbox(label="Enable Thinking", value=config_manager.llm_config.get("enable_thinking", False))
            llm_save_btn = gr.Button("保存LLM配置", variant="primary")
            llm_status = gr.Textbox(label="LLM配置状态", interactive=False)
        
        with gr.Tab("TTS配置"):
            with gr.Row():
                tts_base_url = gr.Textbox(label="Base URL", value=config_manager.tts_config.get("base_url", ""))
                tts_voice_file = gr.Textbox(label="Voice File", value=config_manager.tts_config.get("voice_file", ""))
            with gr.Row():
                tts_prompt_text = gr.Textbox(label="Prompt Text", value=config_manager.tts_config.get("prompt_text", ""))
                tts_prompt_language = gr.Textbox(label="Prompt Language", value=config_manager.tts_config.get("prompt_language", ""))
            with gr.Row():
                tts_text_language = gr.Textbox(label="Text Language", value=config_manager.tts_config.get("text_language", ""))
                tts_how_to_cut = gr.Textbox(label="How to Cut", value=config_manager.tts_config.get("how_to_cut", ""))
            with gr.Row():
                tts_top_k = gr.Number(label="Top K", value=config_manager.tts_config.get("top_k", 3))
                tts_top_p = gr.Number(label="Top P", value=config_manager.tts_config.get("top_p", 0.7))
            with gr.Row():
                tts_temperature = gr.Number(label="Temperature", value=config_manager.tts_config.get("temperature", 0.7))
                tts_ref_free = gr.Checkbox(label="Ref Free", value=config_manager.tts_config.get("ref_free", False))
            with gr.Row():
                tts_speed = gr.Number(label="Speed", value=config_manager.tts_config.get("speed", 1.0))
                tts_if_freeze = gr.Checkbox(label="If Freeze", value=config_manager.tts_config.get("if_freeze", False))
            with gr.Row():
                tts_sample_steps = gr.Number(label="Sample Steps", value=config_manager.tts_config.get("sample_steps", 10))
                tts_if_sr = gr.Checkbox(label="If SR", value=config_manager.tts_config.get("if_sr", False))
            with gr.Row():
                tts_pause_second = gr.Number(label="Pause Second", value=config_manager.tts_config.get("pause_second", 0.0))
            tts_save_btn = gr.Button("保存TTS配置", variant="primary")
            tts_status = gr.Textbox(label="TTS配置状态", interactive=False)

        with gr.Tab("TTS_C配置"):
            with gr.Row():
                tts_c_base_url = gr.Textbox(label="Base URL", value=config_manager.tts_c_config.get("base_url", ""))
            tts_c_save_btn = gr.Button("保存TTS_C配置", variant="primary")
            tts_c_status = gr.Textbox(label="TTS_C配置状态", interactive=False) 
        
        with gr.Tab("音频配置"):
            with gr.Row():
                audio_output_device_index = gr.Number(label="Output Device Index", value=config_manager.audio_config.get("output_device_index", 0))
            audio_save_btn = gr.Button("保存音频配置", variant="primary")
            audio_status = gr.Textbox(label="音频配置状态", interactive=False)
        
        with gr.Tab("主播人格配置"):
            with gr.Row():
                voice_prompt_text = gr.Textbox(label="System Prompt", value=config_manager.voice_prompt.get("system_prompt", ""), lines=10)
            voice_save_btn = gr.Button("保存主播配置", variant="primary")
            voice_status = gr.Textbox(label="主播配置状态", interactive=False)
        
        with gr.Tab("日志"):
            log_text = gr.Textbox(label="日志", lines=20, interactive=False)
            log_handler = LogHandler(log_text)
            logging.getLogger().addHandler(log_handler)
            
            def cleanup():
                logging.getLogger().removeHandler(log_handler)
            interface.load(cleanup)
        
        def save_live_config(bili_enabled, bili_room_id, tts_choice):
            try:
                # 更新平台配置
                PLATFORM_CONFIG["bilibili_enabled"] = bili_enabled
                # 根据选择设置TTS配置
                if tts_choice == "TTS":
                    PLATFORM_CONFIG["tts_enabled"] = True
                    PLATFORM_CONFIG["tts_c_enabled"] = False
                else:  # TTS_C
                    PLATFORM_CONFIG["tts_enabled"] = False
                    PLATFORM_CONFIG["tts_c_enabled"] = True
                
                # 更新房间配置
                BILIBILI_CONFIG["room_id"] = bili_room_id
                
                # 保存配置到文件
                config_manager.save_config({
                    "LLM_CONFIG": config_manager.llm_config,
                    "TTS_CONFIG": config_manager.tts_config,
                    "TTS_C_CONFIG": config_manager.tts_c_config,
                    "AUDIO_CONFIG": config_manager.audio_config,
                    "BILIBILI_CONFIG": BILIBILI_CONFIG,
                    "PLATFORM_CONFIG": PLATFORM_CONFIG,
                    "VOICE_PROMPT": config_manager.voice_prompt
                })
                
                return "直播配置已保存"
            except Exception as e:
                logger.error(f"保存直播配置时出错: {e}")
                return f"保存直播配置失败: {e}"

        def save_llm_config(api_key, base_url, model, temperature, top_p, presence_penalty, top_k, enable_thinking):
            try:
                config_manager.llm_config.update({
                    "api_key": api_key,
                    "base_url": base_url,
                    "model": model,
                    "temperature": float(temperature),
                    "top_p": float(top_p),
                    "presence_penalty": float(presence_penalty),
                    "top_k": int(top_k),
                    "enable_thinking": bool(enable_thinking)
                })
                config_manager.save_config({
                    "LLM_CONFIG": config_manager.llm_config,
                    "TTS_CONFIG": config_manager.tts_config,
                    "TTS_C_CONFIG": config_manager.tts_c_config,
                    "AUDIO_CONFIG": config_manager.audio_config,
                    "BILIBILI_CONFIG": config_manager.bilibili_config,
                    "PLATFORM_CONFIG": config_manager.platform_config,
                    "VOICE_PROMPT": config_manager.voice_prompt
                })
                return "LLM配置已保存"
            except Exception as e:
                logger.error(f"保存LLM配置时出错: {e}")
                return f"保存LLM配置失败: {e}"

        def save_tts_config(base_url, voice_file, prompt_text, prompt_language, text_language, how_to_cut,
                          top_k, top_p, temperature, ref_free, speed, if_freeze, sample_steps, if_sr, pause_second):
            try:
                config_manager.tts_config.update({
                    "base_url": base_url,
                    "voice_file": voice_file,
                    "prompt_text": prompt_text,
                    "prompt_language": prompt_language,
                    "text_language": text_language,
                    "how_to_cut": how_to_cut,
                    "top_k": int(top_k),
                    "top_p": float(top_p),
                    "temperature": float(temperature),
                    "ref_free": bool(ref_free),
                    "speed": float(speed),
                    "if_freeze": bool(if_freeze),
                    "sample_steps": int(sample_steps),
                    "if_sr": bool(if_sr),
                    "pause_second": float(pause_second)
                })
                config_manager.save_config({
                    "LLM_CONFIG": config_manager.llm_config,
                    "TTS_CONFIG": config_manager.tts_config,
                    "TTS_C_CONFIG": config_manager.tts_c_config,
                    "AUDIO_CONFIG": config_manager.audio_config,
                    "BILIBILI_CONFIG": config_manager.bilibili_config,
                    "PLATFORM_CONFIG": config_manager.platform_config,
                    "VOICE_PROMPT": config_manager.voice_prompt
                })
                return "TTS配置已保存"
            except Exception as e:
                logger.error(f"保存TTS配置时出错: {e}")
                return f"保存TTS配置失败: {e}"
            
        def save_tts_c_config(base_url):
            try:
                config_manager.tts_c_config.update({
                    "base_url": base_url
                })
                config_manager.save_config({
                    "LLM_CONFIG": config_manager.llm_config,
                    "TTS_CONFIG": config_manager.tts_config, 
                    "TTS_C_CONFIG": config_manager.tts_c_config,
                    "AUDIO_CONFIG": config_manager.audio_config,
                    "BILIBILI_CONFIG": config_manager.bilibili_config,
                    "PLATFORM_CONFIG": config_manager.platform_config,
                    "VOICE_PROMPT": config_manager.voice_prompt
                })
                return "TTS_C配置已保存"
            except Exception as e:
                logger.error(f"保存TTS_C配置时出错: {e}")
                return f"保存TTS_C配置失败: {e}"
            
        def save_audio_config(output_device_index):
            try:
                config_manager.audio_config.update({
                    "output_device_index": int(output_device_index)
                })
                config_manager.save_config({
                    "LLM_CONFIG": config_manager.llm_config,
                    "TTS_CONFIG": config_manager.tts_config,
                    "TTS_C_CONFIG": config_manager.tts_c_config,
                    "AUDIO_CONFIG": config_manager.audio_config,
                    "BILIBILI_CONFIG": config_manager.bilibili_config,
                    "PLATFORM_CONFIG": config_manager.platform_config,
                    "VOICE_PROMPT": config_manager.voice_prompt
                })
                return "音频配置已保存"
            except Exception as e:
                logger.error(f"保存音频配置时出错: {e}")
                return f"保存音频配置失败: {e}"

        def save_voice_prompt(prompt_text):
            try:
                config_manager.voice_prompt.update({
                    "system_prompt": prompt_text
                })
                config_manager.save_config({
                    "LLM_CONFIG": config_manager.llm_config,
                    "TTS_CONFIG": config_manager.tts_config,
                    "TTS_C_CONFIG": config_manager.tts_c_config,
                    "AUDIO_CONFIG": config_manager.audio_config,
                    "BILIBILI_CONFIG": config_manager.bilibili_config,
                    "PLATFORM_CONFIG": config_manager.platform_config,
                    "VOICE_PROMPT": config_manager.voice_prompt
                })
                return "语音提示配置已保存"
            except Exception as e:
                logger.error(f"保存语音提示配置时出错: {e}")
                return f"保存语音提示配置失败: {e}"

        # 直播配置保存按钮点击事件
        save_btn.click(
            fn=save_live_config,
            inputs=[bilibili_enabled, room_id, tts_selection],
            outputs=[status]
        )

        # 配置保存按钮点击事件
        llm_save_btn.click(
            fn=save_llm_config,
            inputs=[llm_api_key, llm_base_url, llm_model, llm_temperature, llm_top_p, 
                   llm_presence_penalty, llm_top_k, llm_enable_thinking],
            outputs=[llm_status]
        )

        tts_save_btn.click(
            fn=save_tts_config,
            inputs=[tts_base_url, tts_voice_file, tts_prompt_text, tts_prompt_language, 
                   tts_text_language, tts_how_to_cut, tts_top_k, tts_top_p, tts_temperature, 
                   tts_ref_free, tts_speed, tts_if_freeze, tts_sample_steps, tts_if_sr, 
                   tts_pause_second],
            outputs=[tts_status]
        )

        tts_c_save_btn.click(
            fn=save_tts_c_config,
            inputs=[tts_c_base_url],
            outputs=[tts_c_status]
        )

        audio_save_btn.click(
            fn=save_audio_config,
            inputs=[audio_output_device_index],
            outputs=[audio_status]
        )

        voice_save_btn.click(
            fn=save_voice_prompt,
            inputs=[voice_prompt_text],
            outputs=[voice_status]
        )
    
    return interface

if __name__ == "__main__":
    interface = create_interface()
    interface.launch() 