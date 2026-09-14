# 音频资产库

> `assets/speech/` 下打包的 7 个 .aiff 文件，每个的特征、时长、用途，以及怎么换/生成新音频。

---

## 当前打包的音频清单

```
assets/speech/
├── cute_robot_comfort.aiff      ⭐ 1.85 MB  主语音，v14 默认
├── touch_affection_host.aiff    258 KB  fallback (代码里默认值)
├── cute_probe_host.aiff         215 KB  好奇试探声
├── sigh_demo_host.aiff          250 KB  舒服叹气（主）
├── sigh_demo_line.aiff          106 KB  舒服叹气（短）
├── thank_you_happy_line.aiff     98 KB  开心感谢
└── celebrate_line.aiff          108 KB  欢庆短句
```

总占用：~3 MB（很轻）

---

## 每个音频的"画风"

| 文件 | 推荐场景 | 听起来像 |
|---|---|---|
| `cute_robot_comfort.aiff` | 长按 1.2s+ 安抚 | 可爱机器人语调："唔……唔……被摸真舒服～" 6 秒长版 |
| `touch_affection_host.aiff` | 通用触摸反馈 | 短温柔的"嗯～"或类似抚摸回应（2 秒）|
| `cute_probe_host.aiff` | 想做"试探"性反应（触摸 < 1s 时）| 短促好奇音"咦？"（2 秒）|
| `sigh_demo_host.aiff` | 想做"享受"声 | 满足的叹息"哈～"（2.5 秒）|
| `sigh_demo_line.aiff` | 同上但更短 | 短叹气（1 秒）|
| `thank_you_happy_line.aiff` | 完成某事的感谢 | 短"谢谢～"（1 秒）|
| `celebrate_line.aiff` | 完成某事的欢庆 | 短"耶～"（1 秒）|

**当前 v14 配置只用 `cute_robot_comfort.aiff`**，其他是备选库。

---

## 怎么换主语音

### 方法 1: 改板上 mapping（用现成 asset）

```bash
# 编辑 board-files/touch_mapping.json
# 找到 comfort_sound.asset_name，改成你想要的
# 例如：
"asset_name": "speech/sigh_demo_host.aiff"

# 上传
scp board-files/touch_mapping.json root@192.168.0.183:/home/sunrise/Desktop/
ssh root@192.168.0.183 'systemctl restart mira-touch'
```

dispatcher 监听 mtime，下次触摸自动用新 asset。

### 方法 2: 替换文件（保持文件名不变）

如果你只想改"那段话"但不动 mapping 配置：

```bash
# 用同名替换
cp 你的新录音.aiff "assets/speech/cute_robot_comfort.aiff"
# bridge 下次播就是新内容（不需要重启 bridge，afplay 每次重新读文件）
```

---

## 怎么生成新音频

### 方案 A: 用 macOS `say` 命令（最快）

```bash
# 中文女声"婷婷"
say -v Tingting "唔……被你摸到了……" -o assets/speech/cute_new.aiff --data-format=LEI16@22050

# 英文女声 Samantha
say -v Samantha "Mmm... that feels nice..." -o assets/speech/cute_new.aiff
```

可用语音列表：`say -v ?` （会列出所有装的 TTS 语音）

调速：`-r 150` （单位 wpm，默认 200）

### 方案 B: 用云 TTS（更自然）

#### Anthropic 没 TTS，用第三方：

- **Microsoft Azure TTS** —— 中文 zh-CN-XiaoxiaoNeural 等"少女音"很自然
- **ElevenLabs** —— 最逼真，但收费
- **OpenAI TTS** —— `tts-1-hd` 模型，nova/shimmer 等女声

下载结果通常是 .mp3 / .wav，转 .aiff：

```bash
brew install ffmpeg
ffmpeg -i input.mp3 -ar 22050 -ac 1 -c:a pcm_s16be assets/speech/output.aiff
```

### 方案 C: 真人录音

用 iPhone "语音备忘录" 录，发到 Mac (.m4a)。然后转：

```bash
ffmpeg -i recording.m4a -ar 22050 -ac 1 -c:a pcm_s16be \
  assets/speech/cute_robot_comfort.aiff
```

---

## 推荐的"画风设计"

触觉系统是"被抚摸时的反应"——参考宠物/婴儿的反应原型：

| 触摸时长 | 推荐情绪 | 例 |
|---|---|---|
| 0-0.5s | 微反应（轻"咦？"）| cute_probe_host |
| 0.5-1.2s | 享受（开始放松）| sigh_demo_line |
| 1.2-3s | 沉浸（满足的"哈～"）| cute_robot_comfort（当前用）|
| 3s+ | 撒娇 / 嗯哼 | 自定义录制 |

**只用一个 asset 的好处**：状态机简单。

**多 asset 的好处**：根据触摸时长选不同语音，体验更丰富。但需要改 dispatcher 加多阈值逻辑（v15 没做，留给未来）。

---

## 音频技术规格

bridge 用 `afplay` 播，macOS afplay 支持的格式：

- ✅ AIFF（推荐，原生无损）
- ✅ WAV
- ✅ MP3（如果系统装了相应解码器）
- ✅ M4A / AAC
- ✅ CAF（macOS 原生缓存格式）
- ❌ OGG, FLAC, OPUS（不支持）

**采样率建议**：
- 22050 Hz / 16-bit / Mono —— 语音足够，文件小
- 44100 Hz / 16-bit / Stereo —— 音乐用，对语音是浪费

**时长建议**：
- 触觉触发的"安抚声" → 2-6 秒（不要超过 10 秒，否则用户松手前后衔接尴尬）
- 短反馈"叮" → 0.3-1 秒

---

## 文件命名约定

约定（不强制）：

```
<emotion>_<context>_<voice_type>.aiff
```

例：
- `cute_robot_comfort` = 可爱+机器人音色+安慰场景
- `sigh_demo_host` = 叹气+演示+主持人音色
- `thank_you_happy_line` = 感谢+开心+台词版（短）

`_host` 通常是较长的"对话"音频，`_line` 是短一句。

---

## 后续扩展库

如果你想做多种触觉反应，建议先录这些：

```
speech/
├── short_tap.aiff           ← 短触摸（< 0.5s）："咦"
├── medium_touch.aiff        ← 中等（0.5-1.2s）："嗯～"
├── cute_robot_comfort.aiff  ← 长按（1.2s+）："唔……" (现有)
├── tickle.aiff              ← 连续多次触摸："哈哈痒"（笑）
└── annoyed.aiff             ← 触摸太久 / 太频繁："好啦好啦"

sfx/                         ← 非语音音效
├── chime_soft.aiff          ← 触摸瞬间的"叮"
├── chime_warm.aiff          ← 长按完成的"嗒"
└── ...
```

dispatcher 加状态机区分不同触发类型——但是 v15 没做，留给 v16+。

---

## 听一下当前音频（在 Mac 上）

```bash
cd "/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge"

# 试听全部
for f in assets/speech/*.aiff; do
  echo "▶ $f"
  afplay "$f"
  echo
done
```

或者直接：

```bash
afplay assets/speech/cute_robot_comfort.aiff
```

---

## 备份原始库

如果想从 Mira-Light-Voice-Full-Ready 那边补别的音频回来：

```bash
SRC="/Users/wangjianle/Downloads/Mira/Mira-Light-Voice-Full-Ready/assets/audio/speech"
DST="/Users/wangjianle/Downloads/GitHub/Mira Light/Mira-3/mira-light-touch-system/audio-bridge/assets/speech"

# 看那边有什么
ls "$SRC/"

# 拷你想要的
cp "$SRC/wake_up_host.aiff" "$DST/"
```

那边总共有 22 个 .aiff（约 5.7 MB），是历史 v1-v10 时为不同 scene 录的。

---

## 相关文档

- 协议 → [PROTOCOL.md](PROTOCOL.md)
- 部署 → [DEPLOYMENT.md](DEPLOYMENT.md)
- 触觉系统整体 → [../../README.md](../../README.md)
