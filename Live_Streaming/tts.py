from config import TTS_CONFIG
import os

def tts(word):
	from gradio_client import Client, handle_file
	
	# 使用 os.path.join 来构建路径，避免转义问题
	voice_file = os.path.join(os.path.dirname(__file__), TTS_CONFIG["voice_file"])
	
	client = Client(TTS_CONFIG["base_url"])
	result = client.predict(
			ref_wav_path=handle_file(voice_file),
			prompt_text=TTS_CONFIG["prompt_text"],
			prompt_language=TTS_CONFIG["prompt_language"],
			text_language=TTS_CONFIG["text_language"],
			how_to_cut=TTS_CONFIG["how_to_cut"],
			top_k=TTS_CONFIG["top_k"],
			top_p=TTS_CONFIG["top_p"],
			text=word,
			temperature=TTS_CONFIG["temperature"],
			ref_free=TTS_CONFIG["ref_free"],
			speed=TTS_CONFIG["speed"],
			if_freeze=TTS_CONFIG["if_freeze"],
			inp_refs=None,
			sample_steps=TTS_CONFIG["sample_steps"],
			if_sr=TTS_CONFIG["if_sr"],
			pause_second=TTS_CONFIG["pause_second"],
			fn_index=1
	)
	return result
    #这里result返回的是gptsovits输出的音频文件路径地址，之后可以通过读取这个地址的文件来播放音频