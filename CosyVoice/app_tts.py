from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile

import os
import sys

import uuid
import numpy as np

import torch
import torchaudio
import random
import librosa
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append('{}/third_party/Matcha-TTS'.format(ROOT_DIR))
from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
from cosyvoice.utils.file_utils import load_wav, logging
from cosyvoice.utils.common import set_all_random_seed


app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化模型（在服务启动时加载）
cosyvoice = None
max_val = 0.8
prompt_sr = 16000

model_dir = "/home/ye/data/my_models/models/pretrained_models/CosyVoice2-0.5B"
cosyvoice = CosyVoice2(model_dir)


def postprocess(speech, top_db=60, hop_length=220, win_length=440):
    speech, _ = librosa.effects.trim(
        speech, top_db=top_db,
        frame_length=win_length,
        hop_length=hop_length
    )
    if speech.abs().max() > max_val:
        speech = speech / speech.abs().max() * max_val
    speech = torch.concat([speech, torch.zeros(1, int(cosyvoice.sample_rate * 0.2))], dim=1)
    return speech



@app.post("/generate_audio")
async def api_generate_audio(
    tts_text: str = Form(...),

):
    mode_checkbox_group="3s极速复刻"
    sft_dropdown="default"
    prompt_text="什么意思啊？什么意思啊她，她不播了是吧？"
    prompt_wav = "/home/ye/data/code/CosyVoice/dataset/badXT_1.wav"
    seed=0
    stream=False
    speed=1.0

    result = generate_audio(
        tts_text=tts_text,
        mode_checkbox_group=mode_checkbox_group,
        sft_dropdown=sft_dropdown,
        prompt_text=prompt_text,
        prompt_wav_upload=prompt_wav,
        prompt_wav_record=None,
        instruct_text="",
        seed=seed,
        stream=stream,
        speed=speed
    )

    # 生成唯一文件名
    output_filename = f"/tmp/{uuid.uuid4()}.wav"
    torchaudio.save(
        output_filename,
        torch.FloatTensor(result[1]).unsqueeze(0),
        result[0]
    )

    # 返回音频文件
    return FileResponse(
        output_filename,
        media_type="audio/wav",
        filename="generated_audio.wav"
    )




# 原始生成函数保持不变（需要稍作修改返回格式）
def generate_audio(tts_text, mode_checkbox_group, sft_dropdown, prompt_text,
                  prompt_wav_upload, prompt_wav_record, instruct_text, seed, stream, speed):
    save_path=r"/home/ye/data/code/CosyVoice/output/demo.wav"
    if prompt_wav_upload is not None:
        prompt_wav = prompt_wav_upload
    elif prompt_wav_record is not None:
        prompt_wav = prompt_wav_record
    else:
        prompt_wav = None
    # if instruct mode, please make sure that model is iic/CosyVoice-300M-Instruct and not cross_lingual mode
    if mode_checkbox_group == '3s极速复刻':
        logging.info('get zero_shot inference request')
        prompt_speech_16k = postprocess(load_wav(prompt_wav, prompt_sr))
        set_all_random_seed(seed)

        # 初始化存储完整音频的列表
        full_audio = []

        # 生成完整音频（stream=False 表示非流式）
        for i in cosyvoice.inference_zero_shot(
                tts_text,
                prompt_text,
                prompt_speech_16k,
                stream=False,  # 关键：关闭流式
                speed=speed
        ):
            audio_chunk = i['tts_speech'].numpy().flatten()
            full_audio.append(audio_chunk)

        # 合并所有音频块
        if len(full_audio) == 0:
            raise ValueError("No audio generated")
        complete_audio = np.concatenate(full_audio, axis=0)

        # 保存音频文件（可选，根据需求保留）
        torchaudio.save(
            save_path,
            torch.FloatTensor(complete_audio).unsqueeze(0),
            cosyvoice.sample_rate
        )
    result1=cosyvoice.sample_rate
    result2=complete_audio

    return result1, result2

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7800)