# Amadeus Presence

红莉栖风格个人桌面助手原型。当前版本在原有 Presence 交互底座上加入了 **轻量级本地语音链路雏形**：录音、离线 STT、本地小模型、离线 TTS 和角色表情状态可以串起来运行。

目标不是把大模型常驻塞满显存，而是优先验证：**低资源、低延迟、本地运行、短语音互动和稳定角色感**。

## 当前能力

### Presence

- 透明无边框桌面窗口、置顶、拖动和位置保存。
- 鼠标靠近面部：眼睛跟随，头部滞后；离远后小幅随机扫视。
- 左键点击：10 秒内连续点击会逐步皱眉、偏头和增加不耐烦；情绪随时间衰减。
- 自然眨眼、微小呼吸、基础表情状态和本地交互日志。
- 右键调试面板、置顶开关和退出。

### Local Voice V0.1

按住角色 **鼠标中键** 说话，松开后依次执行：

```text
Microphone
  -> faster-whisper small
  -> local Ollama model (default: qwen2.5:1.5b)
  -> structured reply {text, emotion}
  -> character expression
  -> local pyttsx3 / Windows SAPI voice
```

STT、LLM 和 TTS 的耗时部分均在后台 worker 中执行，不放进 Qt 主线程，因此语音处理时桌宠动画不应冻结。

当前角色只保留最近 8 轮短期对话；**尚未加入长期记忆、Utility AI、系统活动感知、Live2D 或主动说话**。

---

## 1. 基础安装

需要 Python 3.10+。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

只运行 Presence、不启用语音：

```powershell
.\.venv\Scripts\python.exe app.py --no-voice
```

或者双击：

```text
Start Amadeus.cmd
```

---

## 2. 安装可选语音依赖

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
```

语音扩展当前包含：

- `sounddevice`：麦克风录音。
- `faster-whisper`：本地语音识别。
- `pyttsx3`：轻量离线 Windows TTS。

首次加载 Whisper 模型需要本地存在对应模型文件；如果由 faster-whisper 自动获取模型，则首次准备阶段可能需要网络，之后推理可本地进行。

---

## 3. 本地小模型

当前默认使用本机 Ollama HTTP 接口：

```text
http://127.0.0.1:11434/api/chat
```

默认模型：

```text
qwen2.5:1.5b
```

安装 Ollama 后，在命令行准备模型：

```powershell
ollama pull qwen2.5:1.5b
```

然后确认：

```powershell
ollama run qwen2.5:1.5b
```

模型名、端点和上下文轮数都在 `config/voice.json` 修改。

这个版本刻意选择 1.5B 级模型，而不是 7B/14B，目标是在 RTX 4060 Laptop 8 GB 显存机器上尽量降低常驻资源和首响应延迟。后续可以直接把 `model` 改成其他本地模型做 A/B 测试。

---

## 4. 启动与操作

普通启动：

```powershell
.\.venv\Scripts\python.exe app.py
```

调试启动：

```powershell
.\.venv\Scripts\python.exe app.py --debug
```

操作：

- **左键点击**：角色确认/逐步不耐烦。
- **左键拖动**：移动角色，松开保存位置。
- **按住鼠标中键**：开始录音。
- **松开鼠标中键**：停止录音并执行 STT -> LLM -> TTS。
- **右键**：调试面板、置顶开关、退出。

调试面板会显示：

- 当前事件、行为和表情；
- voice status：listening / transcribing / thinking / speaking / idle；
- Whisper 识别文本；
- 本地模型最终角色回复；
- irritation、gaze 等 Presence 状态。

---

## 5. 配置

### `config/behavior.json`

Presence 参数：

- 点击窗口与不耐烦增量；
- 情绪衰减；
- gaze 平滑；
- blink 和 idle gaze 周期。

### `config/voice.json`

示例：

```json
{
  "enabled": true,
  "stt": {
    "model": "small",
    "device": "cuda",
    "compute_type": "int8_float16",
    "language": "zh"
  },
  "llm": {
    "endpoint": "http://127.0.0.1:11434/api/chat",
    "model": "qwen2.5:1.5b",
    "history_turns": 8
  },
  "tts": {
    "rate": 185,
    "volume": 1.0,
    "voice_contains": ""
  }
}
```

如果暂时没有安装语音模型，使用 `--no-voice` 即可继续试玩原 Presence，不会要求安装语音依赖。

---

## 6. 目录

```text
Amadeus/
├── app.py
├── brain/
│   ├── history.py
│   ├── local_llm.py
│   ├── prompt.py
│   └── types.py
├── character/
│   └── controller.py
├── core/
│   ├── events.py
│   └── state.py
├── voice/
│   ├── pipeline.py
│   ├── recorder.py
│   ├── stt.py
│   └── tts.py
├── ui/
│   ├── pet_window.py
│   └── placeholder.py
├── config/
│   ├── behavior.json
│   └── voice.json
└── storage/
```

设计边界保持明确：

- `ui/` 不负责模型推理。
- `brain/` 不依赖 Qt。
- `voice/` 封装音频链路。
- `character/` 只维护角色状态和反应。
- EventBus 用于把语音状态映射回角色表现。

---

## 7. 测试

不需要安装 Whisper/Ollama/TTS 即可运行核心单元测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

新增测试覆盖：

- Event payload；
- voice reply -> character state；
- bounded short-term history；
- 本地模型 JSON / plain-text 回复解析。

语音、Windows 音频设备和 CUDA 仍需要本机手动验收。

---

## 当前边界与下一步

当前版本是 **V0.1 voice architecture prototype**，不是完整 Amadeus：

尚未实现：

- Live2D；
- 高质量角色 TTS；
- 全局语音快捷键或 wake word；
- VAD 常驻监听；
- 长期记忆；
- 桌面窗口/进程感知；
- 主动互动；
- Utility / BDI；
- 屏幕视觉理解。

下一步优先试玩当前链路，实测三件事：

1. `faster-whisper small` 在目标电脑上的识别延迟；
2. 1.5B 本地模型的角色回复是否足够自然；
3. STT + LLM + TTS 总体首次发声延迟和 GPU/RAM 占用。

先根据实际体验调整模型大小和 TTS，再决定是否进入长期记忆与桌面感知。
