import llm
import tts
from logging_config import setup_logging
import logging
from dialogue_manager import DialogueType, DialogueSystem

class AdGenerator:
    def __init__(self):
        self.logger = setup_logging('ad_generator')
        self.ad_prompt_template = """
你是一个专业的广告文案撰写专家。现在需要你为一个商品生成富有感染力的广告词。
要求：
1. 语言要生动活泼，富有感染力
2. 长度控制在50字以内
3. 要突出商品的核心优势和特点
4. 语言要自然，适合直播场景下的语音播报
5. 要有吸引力和说服力
6. 将广告词中所有的数字替换为中文数字，例如：22000替换为两万两千，将英文单位替换为中文，例如：Pa替换为帕
7. 除商品信息外，不要输出其他内容
8. 所有产品都经过严格测试，质量可靠，请放心使用

商品信息：{product_info}

请基于以上信息，生成一段广告词。
"""

    def generate_ad_copy(self, product_info):
        """
        生成广告词
        :param product_info: 商品基本信息
        :return: 生成的广告词
        """
        try:
            # 检查输入是否为空
            if not product_info or not product_info.strip():
                self.logger.warning("商品信息为空，无法生成广告词")
                return "请输入商品信息后再生成广告词"
            
            self.logger.info(f"开始为商品生成广告词: {product_info}")
            
            # 构建完整的prompt
            full_prompt = self.ad_prompt_template.format(product_info=product_info)
            
            # 调用大模型生成广告词
            ad_copy = llm.gpt(full_prompt, "")
            
            self.logger.info(f"广告词生成成功: {ad_copy}")
            return ad_copy
            
        except Exception as e:
            self.logger.error(f"生成广告词时出错: {e}")
            return None

    def generate_ad_copy_with_history(self, product_info, dialogue_history, dialogue_system):
        """
        根据历史对话生成广告词
        :param product_info: 商品基本信息
        :param dialogue_history: 历史对话记录
        :return: 生成的广告词
        """
        try:
            # 检查输入是否为空
            if not product_info or not product_info.strip():
                self.logger.warning("商品信息为空，无法生成广告词")
                return "请输入商品信息后再生成广告词"
            
            self.logger.info(f"开始根据历史对话生成广告词: {product_info}")

            history = dialogue_system.history_manager.get_formatted_history()
                        
            full_prompt = f"""
你是一个专业的广告文案撰写专家。现在需要你为一个商品生成富有感染力的广告词。
要求：
1. 语言要生动活泼，富有感染力
2. 长度控制在50字以内
3. 要突出商品的核心优势和特点
4. 语言要自然，适合直播场景下的语音播报
5. 要有吸引力和说服力
6. 将广告词中所有的数字替换为中文数字，例如：22000替换为两万两千，将英文单位替换为中文，例如：Pa替换为帕
7. 除商品信息外，不要输出其他内容
8. 如果历史对话中出现了商品信息，请参考历史对话内容，使广告词更自然，更符合当前对话场景


以下是弹幕历史对话：
{history}

商品信息：{product_info}

请基于以上信息，生成一段广告词。
"""
            
            # 调用大模型生成广告词
            ad_copy = llm.gpt(full_prompt, "")
            
            self.logger.info(f"广告词生成成功: {ad_copy}")
            return ad_copy
            
        except Exception as e:
            self.logger.error(f"生成广告词时出错: {e}")
            return None

    def generate_ad_voice(self, ad_copy):
        """
        将广告词转换为语音
        :param ad_copy: 广告词文本
        :return: 语音文件路径
        """
        try:
            self.logger.info("开始生成广告词语音")
            voice_file = tts.tts(ad_copy)
            self.logger.info(f"广告词语音生成成功: {voice_file}")
            return voice_file
        except Exception as e:
            self.logger.error(f"生成广告词语音时出错: {e}")
            return None

    def generate_and_get_voice(self, product_info):
        """
        整合广告词生成和语音转换的完整流程
        :param product_info: 商品基本信息
        :return: 语音文件路径或None
        """
        try:
            # 生成广告词
            ad_copy = self.generate_ad_copy(product_info)
            if not ad_copy:
                return None
                
            # 生成语音
            voice_file = self.generate_ad_voice(ad_copy)
            return voice_file
            
        except Exception as e:
            self.logger.error(f"广告生成完整流程出错: {e}")
            return None 