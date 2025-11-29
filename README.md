# Workout Pacer 运动配速器

Generate audio with voice announcements to help you maintain a steady pace during swimming, running, or any sport.

生成带语音播报的音频，帮助你在游泳、跑步或其他运动中保持稳定配速。

## Quick Start 快速开始

### 1. Install 安装

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install ffmpeg (required by pydub)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg
```

### 2. Configure 配置

Edit `config.yaml` - only 4 settings needed:

编辑 `config.yaml` - 只需要填写 4 个设置：

```yaml
# 配速设置：你的目标配速是多少？
target_time: "2:00"      # 2分钟
per_meters: 100          # 跑100米

# 音频设置：这段音频能陪你跑多远？
total_distance: 1000     # 米

# 每跑多少米报一次时？（填25 → 会在25m, 50m, 75m...处报时）
announce_every: 25
```

### 3. Generate 生成

```bash
python generate.py
```

Output file: `output/workout_pacer.mp3`

### 4. Use 使用

1. Transfer the audio file to your device/waterproof earbuds
2. Press play, wait for countdown
3. Start when you hear "Go!"
4. Listen for distance announcements to check your pace

---

1. 把音频文件传到手机或防水耳机
2. 按播放，等待倒计时
3. 听到"开始"后开始运动
4. 听语音播报来检查配速

## Examples 示例

### Swimming 游泳

25米泳池，2分钟游100米，游1000米：

```yaml
target_time: "2:00"
per_meters: 100
total_distance: 1000
announce_every: 25
```

### Running 跑步

6分钟跑1公里，跑5公里：

```yaml
target_time: "6:00"
per_meters: 1000
total_distance: 5000
announce_every: 500
```

## Optional Settings 可选设置

### Warmup Countdown 准备倒计时

```yaml
warmup_seconds: 15       # 默认 15 秒（包含语音提示 + 10秒倒数）
```

### Metronome 节拍器

Help maintain stroke/step rhythm:

帮助保持划水/步频节奏：

```yaml
metronome:
  enabled: true          # 启用节拍器
  bpm: 55                # 每分钟节拍数
```

### Voice Language 语音语言

```yaml
voice:
  language: "zh"         # "zh" 中文 / "en" 英文
```

### TTS Engine 语音引擎

```yaml
tts:
  provider: "edge"       # "edge"（免费）或 "openai"（付费）
```

## How It Works 工作原理

The pacer calculates when you should reach each distance checkpoint based on your target pace, then announces it at exactly that time.

配速器根据你的目标配速计算你应该在什么时间到达每个距离点，然后在那个时间播报。

**Example 示例:**

- Target: 2:00 per 100m (2分钟100米)
- At 30 sec → "25 meters" (30秒时播报"25米")
- At 60 sec → "50 meters"
- At 90 sec → "75 meters"
- At 120 sec → "100 meters"

If you hear "50 meters" and you're:
- At 50m → Perfect pace! 配速正确
- Past 50m → Too fast, slow down 太快了
- Before 50m → Too slow, speed up 太慢了

## Features 功能

- Free TTS (Edge TTS) - works in China, no API key needed
- Optional premium TTS (OpenAI)
- Optional metronome for rhythm
- Chinese and English voice support
- Simple 4-parameter configuration

## Project Structure 项目结构

```
workout-pacer/
├── config.yaml          # Configuration 配置文件
├── generate.py          # Main program 主程序
├── tts_service.py       # TTS service 语音服务
├── audio_generator.py   # Audio generation 音频生成
├── requirements.txt     # Dependencies 依赖
└── output/              # Output directory 输出目录
```

## Requirements 依赖

- Python 3.7+
- ffmpeg
- pydub, edge-tts, PyYAML, numpy

## License

MIT

## Contributing 贡献

Issues and Pull Requests welcome!

欢迎提交 Issue 和 PR！
