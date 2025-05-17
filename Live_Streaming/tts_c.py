import requests
import torch
import torchaudio
import io
import soundfile as sf  # pip install soundfile
import torch
from datetime import datetime
import os
from config import TTS_C_CONFIG

def tts_c(text):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    # url = "http://192.168.1.55:7800/generate_audio"
    url = "http://ry2.9gpu.com:37026/generate_audio"
    # url = TTS_C_CONFIG["base_url"]
    current_path=os.path.abspath(os.getcwd())
    save_path=os.path.join(current_path,"output",f"{timestamp}.wav")

    # 表单参数
    data = {
        "tts_text": text,
    }
    # sample_rate, complete_audio = requests.post(url, data=data)

    response = requests.post(url, data=data)
    # 获取二进制音频数据
    audio_bytes = io.BytesIO(response.content)
    audio_data, sample_rate = sf.read(audio_bytes, dtype="float32")  # 从音频数据中获取实际采样率
    audio_tensor = torch.from_numpy(audio_data).unsqueeze(0)  # 转成 Tensor [1, samples]

    # 创建重采样器
    resampler = torchaudio.transforms.Resample(
        orig_freq=sample_rate,
        new_freq=44100
    )
    
    # 执行重采样
    resampled_audio = resampler(audio_tensor)
    
    complete_audio = response.content
    
    torchaudio.save(
        save_path,
        resampled_audio,
        44100  # 使用新的采样率
    )

    return save_path