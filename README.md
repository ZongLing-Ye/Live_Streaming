# AI 虚拟主播直播助手

本项目是一个 AI 虚拟主播直播助手，旨在帮助用户在B站等平台进行互动式直播。它可以自动接收直播间的弹幕消息，利用大语言模型 (LLM) 生成智能回复，并通过文本转语音 (TTS) 技术将回复转换成主播的声音播放出来。此外，项目还集成了 OBS 音频控制、动态广告生成和Gradio Web用户界面。

## 主要功能

*   **实时弹幕互动**: 自动获取B站直播间弹幕，并能与观众进行实时互动。
*   **智能回复生成**: 集成大语言模型 (如 DeepSeek)，根据主播人设和上下文生成自然、有趣的回复。
*   **语音合成播放**: 支持多种 TTS 服务，将生成的文本回复转换为语音，并通过指定音频设备播放。
*   **OBS 音频控制**: 能够控制 OBS 中的音频源，方便管理直播音频。
*   **动态广告生成**: 可根据直播内容和历史对话动态生成广告词，并在合适的时机插播。
*   **可配置主播人设**: 通过配置文件定义主播的姓名、性格、背景故事等，使AI回复更具个性。
*   **多平台支持 (规划中)**: 目前主要支持B站，未来可能扩展到抖音等其他直播平台。
*   **Web 用户界面**: 提供 Gradio 构建的 Web 界面，方便用户启停直播、监控状态和调整配置。

## 项目结构

```
.
├── CosyVoice/        # CosyVoice TTS 解决方案 (可能作为子模块或依赖)
│   ├── ...
│   └── README.md
├── Live_Streaming/   # AI虚拟主播核心代码
│   ├── config.py               # 项目主要配置文件
│   ├── person_live.py          # 直播核心逻辑
│   ├── llm.py                  # 大语言模型接口
│   ├── tts.py / tts_c.py       # TTS 接口
│   ├── get_bili_danmu.py       # B站弹幕获取
│   ├── obs_audio_control.py    # OBS 音频控制
│   ├── gradio_interface.py     # Gradio Web 界面
│   ├── dialogue_manager.py     # 对话管理
│   ├── ad_generator.py         # 广告生成器
│   ├── requirements.txt        # Python 依赖
│   ├── 主播设定.txt            # (旧版)主播人设示例，现已整合至 config.py
│   └── ...
└── README.md         # 本文件
```

## 安装依赖

1.  确保您已安装 Python (建议版本 >= 3.8)。
2.  克隆本项目。
3.  进入 `Live_Streaming` 目录，并通过 pip 安装所需依赖：

    ```bash
    cd Live_Streaming
    pip install -r requirements.txt
    ```
4.  如果 `CosyVoice` 是必需的，请参照其目录下的 `README.md` 进行安装和配置。

## 配置说明

主要的配置文件位于 `Live_Streaming/config.py`。在启动项目前，请务必根据您的实际情况修改以下关键配置：

*   **`LLM_CONFIG`**:
    *   `api_key`: 您的大语言模型 API 密钥 (例如 DeepSeek API Key)。
    *   `base_url`: 大语言模型服务的 API 地址。
    *   `model`: 使用的模型名称。
*   **`TTS_CONFIG` / `TTS_C_CONFIG`**:
    *   `base_url`: TTS 服务的 API 地址。
    *   `voice_file`, `prompt_text`, `prompt_language` 等: 根据您选择的 TTS 服务进行配置。
    *   `tts_enabled`, `tts_c_enabled`: 选择启用哪个 TTS 服务。
*   **`AUDIO_CONFIG`**:
    *   `output_device_index`: 指定音频输出设备的索引。您可能需要通过脚本或工具查询系统中可用的音频设备及其索引。
*   **`BILIBILI_CONFIG`**:
    *   `room_id`: 您B站直播间的真实房间号 (不是短链ID)。
    *   `enabled`: 是否启用B站弹幕获取。
*   **`PLATFORM_CONFIG`**:
    *   `bilibili_enabled`: 是否启用B站平台。
    *   `douyin_enabled`: 是否启用抖音平台 (当前版本可能尚不支持)。
*   **`VOICE_PROMPT`**:
    *   `system_prompt`: 核心的主播人设定义。请详细描述主播的性格、说话风格、背景、禁忌等。也包含带货产品信息（如果需要）。

**注意**: `主播设定.txt` 文件中的内容已作为 `VOICE_PROMPT` 的一部分整合到了 `config.py` 中，主要配置请以 `config.py` 为准。

## 运行项目

1.  完成依赖安装和配置。
2.  确保您的 LLM 服务、TTS 服务均可正常访问。
3.  运行 `Live_Streaming/person_live.py` 可能会启动后端服务和 Gradio 界面。

    ```bash
    cd Live_Streaming
    python person_live.py
    ```
    或者，如果 Gradio 界面是独立启动的，可能是运行 `Live_Streaming/gradio_interface.py` (需要确认)。

    通常，启动后，您可以通过浏览器访问 Gradio 提供的 URL (例如 `http://127.0.0.1:7860`) 来操作和监控虚拟主播。

    具体启动方式请参照代码或进一步的项目说明。

## 注意事项

*   **音频设备索引**: 正确配置 `AUDIO_CONFIG['output_device_index']` 非常重要，否则可能无法听到主播的声音。您可能需要编写一个简单的 `pygame` 或 `sounddevice` 脚本来列出所有音频设备及其索引，然后选择正确的输出设备。
*   **API Keys**: 请妥善保管您的 API 密钥，不要将其直接上传到公开的代码仓库。建议使用环境变量或专门的密钥管理工具。
*   **CosyVoice**: 如果项目依赖 `CosyVoice`，确保其服务已正确运行并可被主程序访问。

## 贡献

欢迎对本项目进行贡献！如果您有任何建议或发现任何问题，请随时提交 Issue 或 Pull Request。

## 许可证

本项目（`Live_Streaming` 目录下的代码）的许可证信息待补充。
`CosyVoice` 目录包含其自身的 `LICENSE` 文件。 