# 游泳节拍器生成器 🏊‍♂️

为游泳训练生成定制化的节拍器音频，带有精确的时间和距离语音提示。

## 功能特性

- ✅ **可配置的节拍器**：自定义 BPM、拍数和重音模式
- ✅ **智能语音提示**：在精确的时间点提示游泳距离
- ✅ **自动计算**：根据目标配速自动计算所有提示时间点
- ✅ **高质量 TTS**：使用 OpenAI TTS 生成自然的语音
- ✅ **灵活配置**：通过 YAML 配置文件轻松调整所有参数
- ✅ **支持自定义 API**：可配置自定义的 OpenAI API Base URL

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 ffmpeg（pydub 需要）
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt-get install ffmpeg

# Windows:
# 下载 ffmpeg 并添加到 PATH
```

### 2. 配置 API

复制 `.env.example` 到 `.env` 并填入你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
OPENAI_API_KEY=your-api-key-here
# 如果使用自定义 API Base URL：
OPENAI_BASE_URL=https://your-custom-api.com/v1
```

或者直接在环境变量中设置：

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://your-custom-api.com/v1"  # 可选
```

### 3. 配置参数

编辑 `config.yaml` 文件，根据你的需求调整参数：

```yaml
pool:
  length: 25  # 泳池长度

target:
  time_per_100m: 105  # 目标配速（秒）

audio:
  duration: 3600  # 音频总时长（秒）

metronome:
  enabled: true
  bpm: 41
  beats_per_measure: 6

voice:
  enabled: true
  voice_model: "nova"  # 声音选择
```

### 4. 生成音频

```bash
python generate.py
```

生成的音频文件将保存在 `output/` 目录下。

## 配置说明

### 泳池设置 (pool)

- `length`: 泳池长度（米）
- `actual_length`: 实际长度（如果与标准不同）

### 目标配置 (target)

- `time_per_100m`: 每 100 米的目标时间（秒）
  - 例如：105 = 1分45秒/100米

### 音频设置 (audio)

- `duration`: 总时长（秒）
- `format`: 输出格式（mp3 或 wav）
- `sample_rate`: 采样率（默认 44100）
- `output_filename`: 输出文件名

### 节拍器设置 (metronome)

- `enabled`: 是否启用节拍器
- `bpm`: 每分钟节拍数
- `beats_per_measure`: 每小节拍数
- `accent_first`: 第一拍是否为重音
- `volume`: 音量（0-1）
- `click_frequency`: 普通拍频率（Hz）
- `accent_frequency`: 重音拍频率（Hz）

### 语音设置 (voice)

- `enabled`: 是否启用语音提示
- `language`: 语言（zh-CN 或 en-US）
- `volume`: 语音音量（0-1）
- `voice_model`: OpenAI TTS 声音模型
  - 可选：alloy, echo, fable, onyx, nova, shimmer

#### 提示配置 (announcements)

可以配置多个提示规则：

```yaml
announcements:
  - interval: 25  # 每 25 米
    format: "{distance}米"

  - interval: 100  # 每 100 米额外提示
    format: "完成 {hundreds} 个100米"
```

支持的占位符：
- `{distance}`: 当前距离
- `{laps}`: 圈数
- `{hundreds}`: 100米的倍数

## 测试

### 测试 TTS 服务

```bash
python tts_service.py
```

这将生成一个测试语音文件在 `output/test_voice.mp3`。

### 测试音频生成器

```bash
python audio_generator.py
```

这将生成一个 10 秒的测试节拍器在 `output/test_metronome.mp3`。

## 使用场景

### 场景 1：保持匀速游泳

配置：
- BPM 41，每 6 拍 1 重音
- 每 25 米语音提示
- 目标配速 1分45秒/100米

```yaml
metronome:
  enabled: true
  bpm: 41
  beats_per_measure: 6

voice:
  announcements:
    - interval: 25
      format: "{distance}米"
```

### 场景 2：只用语音提示（无节拍器）

配置：
```yaml
metronome:
  enabled: false

voice:
  enabled: true
  announcements:
    - interval: 50
      format: "{distance}米"
```

### 场景 3：长距离训练

配置 1 小时音频，每 100 米提示：

```yaml
audio:
  duration: 3600  # 1小时

voice:
  announcements:
    - interval: 100
      format: "{hundreds}个100"
```

## 项目结构

```
swim-metronome/
├── config.yaml           # 主配置文件
├── generate.py          # 主程序
├── tts_service.py       # TTS 服务模块
├── audio_generator.py   # 音频生成模块
├── requirements.txt     # Python 依赖
├── .env.example        # 环境变量示例
├── README.md           # 说明文档
└── output/            # 输出目录
    ├── voices/        # 生成的语音文件
    └── *.mp3         # 最终音频文件
```

## 常见问题

### 1. TTS 生成失败

**问题**：提示 "生成语音失败" 或 API 错误

**解决方案**：
- 检查 `OPENAI_API_KEY` 是否正确设置
- 如果使用自定义 Base URL，确认 `OPENAI_BASE_URL` 配置正确
- 运行 `python tts_service.py` 测试 TTS 服务

### 2. ffmpeg 未找到

**问题**：提示 "ffmpeg not found"

**解决方案**：
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: 下载 ffmpeg 并添加到系统 PATH

### 3. 音频文件太大

**问题**：生成的 MP3 文件很大

**解决方案**：
- 减少 `audio.duration`（总时长）
- 降低 `metronome.volume`（节拍器音量会影响文件大小）
- 使用 `format: "mp3"` 而不是 `wav`（MP3 更小）

### 4. 语音提示不准确

**问题**：语音提示时间与实际游泳不匹配

**解决方案**：
- 调整 `target.time_per_100m` 以匹配你的实际配速
- 如果泳池实际长度不是标准 25 米，在 `pool.actual_length` 中设置实际长度

## 技术栈

- **Python 3.7+**
- **pydub**: 音频处理和混合
- **OpenAI API**: 高质量 TTS
- **PyYAML**: 配置文件解析
- **NumPy**: 数值计算

## License

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！
