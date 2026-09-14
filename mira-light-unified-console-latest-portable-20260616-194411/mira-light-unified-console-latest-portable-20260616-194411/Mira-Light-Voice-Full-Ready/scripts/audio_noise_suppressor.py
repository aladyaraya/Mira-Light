#!/usr/bin/env python3
"""Lightweight real-time audio noise suppressor using only numpy.

纯 numpy 实时音频降噪器 —— 零额外依赖

降噪策略（三阶段管道）：
  1. 高通滤波：去除低频噪声（空调、风扇、电网嗡嗡声）
  2. 频谱门限：在频域中抑制低于噪声底的频率分量
  3. 自动增益：补偿降噪后的音量损失

这些方法在 numpy 中实现，延迟 < 5ms，适合实时音频流。

用法：
  from audio_noise_suppressor import NoiseSuppressor
  suppressor = NoiseSuppressor(sample_rate=24000)
  clean_pcm = suppressor.process(raw_int16_bytes)
"""

from __future__ import annotations

import math
import struct
import sys
from typing import Optional


def _require_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        raise RuntimeError(
            "numpy is required. Install with: pip install numpy"
        )


class NoiseSuppressor:
    """纯 numpy 实时降噪器。

    处理流程：
      int16 PCM bytes -> float32 -> 高通滤波 -> 频谱门限 -> AGC -> int16 PCM bytes

    所有状态在内部维护，线程安全（通过 GIL）。
    """

    def __init__(
        self,
        sample_rate: int = 24000,
        highpass_cutoff: float = 80.0,
        spectral_gate_strength: float = 1.5,
        spectral_gate_floor_db: float = -40.0,
        agc_target_rms: float = 0.04,
        agc_max_gain_db: float = 12.0,
        noise_estimate_frames: int = 50,
    ):
        """
        Args:
            sample_rate: 采样率 (Hz)，与输入音频一致
            highpass_cutoff: 高通滤波截止频率 (Hz)，去除 80Hz 以下的低频噪声
            spectral_gate_strength: 频谱门限强度倍数，越大降噪越强但可能损伤语音
            spectral_gate_floor_db: 频谱门限最低衰减 (dB)，-40 表示最大衰减 40dB
            agc_target_rms: AGC 目标 RMS 电平
            agc_max_gain_db: AGC 最大增益 (dB)
            noise_estimate_frames: 用于估算噪声底的初始帧数
        """
        self.sample_rate = sample_rate
        self.highpass_cutoff = highpass_cutoff
        self.gate_strength = spectral_gate_strength
        self.gate_floor_db = spectral_gate_floor_db
        self.agc_target = agc_target_rms
        self.agc_max_gain_db = agc_max_gain_db
        self.noise_estimate_frames = noise_estimate_frames

        # 内部状态
        self._np = _require_numpy()
        self._frame_count = 0
        self._noise_spectrum: Optional = None  # 估算的噪声频谱
        self._noise_avg = None                  # 噪声底估算中间值
        self._agc_gain_db = 0.0

        # 高通滤波器状态（一阶 IIR）
        rc = 1.0 / (2.0 * math.pi * highpass_cutoff)
        dt = 1.0 / sample_rate
        alpha = rc / (rc + dt)
        self._hp_alpha = alpha
        self._hp_prev = 0.0

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def process(self, pcm_bytes: bytes) -> bytes:
        """处理一段 int16 PCM 音频数据。

        Args:
            pcm_bytes: 原始 int16 PCM 字节（单声道）

        Returns:
            降噪后的 int16 PCM 字节
        """
        np = self._np

        # 1. 解码 int16 -> float32
        n_samples = len(pcm_bytes) // 2
        if n_samples == 0:
            return pcm_bytes
        audio = np.frombuffer(pcm_bytes, dtype="<i2").astype(np.float32) / 32768.0

        # 2. 高通滤波
        audio = self._highpass(audio)

        # 3. 频谱门限降噪
        audio = self._spectral_gate(audio)

        # 4. 自动增益
        audio = self._agc(audio)

        # 5. 编码回 int16
        clipped = np.clip(audio, -1.0, 1.0)
        result = (clipped * 32767.0).astype("<i2").tobytes()

        self._frame_count += 1
        return result

    def process_float32(self, audio) -> "np.ndarray":
        """处理 float32 numpy 数组，返回降噪后的 float32 数组。"""
        np = self._np
        audio = np.asarray(audio, dtype=np.float32).copy()

        audio = self._highpass(audio)
        audio = self._spectral_gate(audio)
        audio = self._agc(audio)

        self._frame_count += 1
        return np.clip(audio, -1.0, 1.0)

    @property
    def is_ready(self) -> bool:
        """噪声底估算是否已完成"""
        return self._noise_spectrum is not None

    @property
    def frame_count(self) -> int:
        return self._frame_count

    # ------------------------------------------------------------------
    # 高通滤波器（一阶 IIR，去除低频噪声）
    # ------------------------------------------------------------------

    def _highpass(self, audio: "np.ndarray") -> "np.ndarray":
        """一阶 IIR 高通滤波，去除低频噪声（空调、风扇、电网嗡嗡声）"""
        np = self._np
        alpha = self._hp_alpha
        prev = self._hp_prev

        # 向量化处理
        out = np.empty_like(audio)
        out[0] = audio[0] - prev
        for i in range(1, len(audio)):
            out[i] = alpha * (out[i - 1] + audio[i] - audio[i - 1])

        self._hp_prev = float(out[-1])
        return out

    # ------------------------------------------------------------------
    # 频谱门限降噪
    # ------------------------------------------------------------------

    def _spectral_gate(self, audio: "np.ndarray") -> "np.ndarray":
        """频谱门限：估算噪声底，抑制低于噪声底的频率分量"""
        np = self._np
        n = len(audio)

        # 使用 512 点 FFT（约 21ms @ 24kHz），足够实时
        fft_size = 512
        if n < fft_size:
            # 块太短，跳过频谱处理
            return audio

        # 分帧处理（50% 重叠）
        hop = fft_size // 2
        window = np.hanning(fft_size)

        # 填充到整数帧
        padded = np.zeros(n + hop, dtype=np.float32)
        padded[:n] = audio

        n_frames = (len(padded) - fft_size) // hop + 1
        output = np.zeros_like(padded)
        window_sum = np.zeros_like(padded)

        for i in range(n_frames):
            start = i * hop
            frame = padded[start:start + fft_size] * window

            # FFT
            spectrum = np.fft.rfft(frame)
            magnitude = np.abs(spectrum)
            phase = np.angle(spectrum)

            # 估算噪声底（前 N 帧用于估算）
            if self._noise_spectrum is None:
                if self._frame_count < self.noise_estimate_frames:
                    # 还在估算阶段，不做降噪
                    self._update_noise_estimate(magnitude)
                    output[start:start + fft_size] += frame
                    window_sum[start:start + fft_size] += window
                    continue
                else:
                    # 估算完成
                    self._noise_spectrum = self._noise_avg

            # 应用频谱门限
            noise = self._noise_spectrum
            gate_threshold = noise * self.gate_strength

            # 计算衰减因子
            ratio = np.where(
                magnitude > gate_threshold,
                1.0,
                magnitude / np.maximum(gate_threshold, 1e-10),
            )

            # 限制最小衰减
            floor_linear = 10.0 ** (self.gate_floor_db / 20.0)
            ratio = np.maximum(ratio, floor_linear)

            # 应用衰减
            enhanced_magnitude = magnitude * ratio
            enhanced_spectrum = enhanced_magnitude * np.exp(1j * phase)

            # IFFT
            enhanced_frame = np.fft.irfft(enhanced_spectrum, n=fft_size)

            # 重叠相加
            output[start:start + fft_size] += enhanced_frame * window
            window_sum[start:start + fft_size] += window

        # 归一化重叠相加
        valid = window_sum > 1e-8
        output[valid] /= window_sum[valid]

        return output[:n]

    def _update_noise_estimate(self, magnitude: "np.ndarray") -> None:
        """更新噪声底估算（指数移动平均）"""
        np = self._np
        if self._noise_avg is None:
            self._noise_avg = magnitude.copy()
        else:
            alpha = 0.1
            self._noise_avg = (
                self._noise_avg * (1 - alpha) + magnitude * alpha
            )

    # ------------------------------------------------------------------
    # 自动增益控制
    # ------------------------------------------------------------------

    def _agc(self, audio: "np.ndarray") -> "np.ndarray":
        """简单的自动增益控制"""
        np = self._np

        rms = float(np.sqrt(np.mean(np.square(audio))))
        if rms < 1e-6:
            return audio

        # 计算需要的增益
        target_gain = self.agc_target / rms
        target_gain_db = 20.0 * math.log10(max(target_gain, 1e-10))

        # 限制增益范围
        target_gain_db = max(-self.agc_max_gain_db, min(self.agc_max_gain_db, target_gain_db))

        # 平滑增益变化（避免突变）
        smooth = 0.15
        self._agc_gain_db = self._agc_gain_db * (1 - smooth) + target_gain_db * smooth

        # 应用增益
        gain_linear = 10.0 ** (self._agc_gain_db / 20.0)
        result = audio * gain_linear

        return np.clip(result, -1.0, 1.0)

    def reset(self):
        """重置所有内部状态"""
        self._frame_count = 0
        self._noise_spectrum = None
        self._noise_avg = None
        self._agc_gain_db = 0.0
        self._hp_prev = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 智能麦克风选择器
# ═══════════════════════════════════════════════════════════════════════════════

import re


# 虚拟设备关键词
_VIRTUAL_PATTERNS = [
    r"virtual", r"cable", r"vb-", r"voicemeeter", r"banana",
    r"stereo mix", r"what u hear", r"what you hear",
    r"wave out", r"waveout", r"loopback",
    r"desktop audio", r"system audio",
    r"nvidia.*broadcast", r"rtx voice", r"krisp",
    r"discord", r"zoom", r"teams", r"slack",
    r"obs", r"stream", r"capture",
    r"steam.*streaming", r"steam.*mic",
]

# 真实麦克风关键词
_REAL_MIC_PATTERNS = [
    r"microphone", r"mic\s*\(", r"array\s*\(",
    r"usb audio", r"usb mic", r"usb pnp",
    r"realtek", r"realtek.*audio",
    r"headset", r"webcam.*mic",
    r"condenser", r"shure", r"rode", r"blue yeti",
]


def is_virtual_device(name: str) -> bool:
    """判断是否为虚拟音频设备"""
    name_lower = name.lower()
    return any(re.search(p, name_lower) for p in _VIRTUAL_PATTERNS)


def score_real_microphone(name: str) -> float:
    """
    对设备名称评分，判断是真实麦克风的置信度。

    Returns:
        0.0 ~ 1.0 的置信度分数
    """
    name_lower = name.lower()

    # 虚拟设备直接 0 分
    if is_virtual_device(name):
        return 0.0

    score = 0.0

    # 高置信度模式
    if re.search(r"microphone\s*\(|mic\s*\(|array\s*\(", name_lower):
        score += 0.5
    if re.search(r"usb\s*(audio|pnp)", name_lower):
        score += 0.4
    if "realtek" in name_lower:
        score += 0.3
    if "microphone" in name_lower or " mic " in name_lower:
        score += 0.2
    if "array" in name_lower:
        score += 0.15
    if "headset" in name_lower or "webcam" in name_lower:
        score += 0.1

    return min(1.0, score)


def pick_best_microphone(devices: list) -> dict:
    """
    从设备列表中选择最佳真实麦克风。

    Args:
        devices: sounddevice.query_devices() 返回的设备列表，
                或 [{'index': int, 'name': str, 'max_input_channels': int}, ...]

    Returns:
        选择的设备信息字典，或 None
    """
    candidates = []

    for dev in devices:
        if isinstance(dev, dict):
            index = dev.get("index", dev.get("id", -1))
            name = dev.get("name", "")
            inputs = dev.get("max_input_channels", 0)
        else:
            index = getattr(dev, "index", -1)
            name = getattr(dev, "name", "")
            inputs = getattr(dev, "max_input_channels", 0)

        if inputs <= 0:
            continue

        score = score_real_microphone(name)
        if score > 0:
            candidates.append({
                "index": index,
                "name": name,
                "inputs": inputs,
                "score": score,
                "isVirtual": is_virtual_device(name),
            })

    if not candidates:
        return None

    # 按分数降序排列
    candidates.sort(key=lambda d: -d["score"])
    return candidates[0]


def resolve_best_mic_index(
    device_hint: str = "",
    prefer_real: bool = True,
    samplerate: int = 24000,
    channels: int = 1,
    dtype: str = "int16",
) -> Optional[int]:
    """
    解析最佳麦克风设备索引。

    Args:
        device_hint: 用户指定的设备提示（索引或名称片段）
        prefer_real: 是否优先选择真实麦克风
        samplerate: 所需的采样率（用于验证设备兼容性）
        channels: 所需的通道数
        dtype: 所需的数据类型

    Returns:
        设备索引，或 None（表示使用系统默认）
    """
    import sounddevice as sd

    devices = sd.query_devices()
    input_devices = []
    for i, dev in enumerate(devices):
        if int(dev.get("max_input_channels", 0)) > 0:
            input_devices.append({"index": i, **dict(dev)})

    if not input_devices:
        return None

    def is_device_compatible(idx: int) -> bool:
        """验证设备是否支持所需的音频参数"""
        try:
            sd.check_input_settings(
                device=idx,
                samplerate=samplerate,
                channels=channels,
                dtype=dtype,
            )
            return True
        except Exception:
            return False

    # 如果有明确提示
    if device_hint and device_hint.lower() not in ("default", ""):
        hint_lower = device_hint.lower()

        # 按索引
        if hint_lower.isdigit():
            idx = int(hint_lower)
            for d in input_devices:
                if d["index"] == idx:
                    if is_device_compatible(idx):
                        return idx
                    # 指定设备不兼容，继续尝试自动选择
                    break

        # 按名称
        for d in input_devices:
            if hint_lower in d["name"].lower():
                if is_device_compatible(d["index"]):
                    return d["index"]
                break

    # 自动选择最佳麦克风（按分数排序，逐个验证兼容性）
    if prefer_real:
        candidates = []
        for dev in input_devices:
            score = score_real_microphone(dev.get("name", ""))
            if score > 0:
                candidates.append({**dev, "score": score})

        candidates.sort(key=lambda d: -d["score"])

        for cand in candidates:
            idx = cand["index"]
            if is_device_compatible(idx):
                return idx

    # 回退到系统默认（验证兼容性）
    try:
        default_idx = sd.default.device[0]
        if default_idx is not None and default_idx >= 0:
            if is_device_compatible(int(default_idx)):
                return int(default_idx)
    except Exception:
        pass

    # 最后回退：返回第一个兼容的输入设备
    for d in input_devices:
        if is_device_compatible(d["index"]):
            return d["index"]

    # 全都不兼容，返回 None 让 sounddevice 使用系统默认
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 命令行测试
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="轻量级音频降噪器测试")
    parser.add_argument("--list-devices", action="store_true", help="列出音频设备")
    parser.add_argument("--test", action="store_true", help="测试降噪效果")
    parser.add_argument("--sample-rate", type=int, default=24000)
    parser.add_argument("--seconds", type=float, default=5.0)
    args = parser.parse_args()

    if args.list_devices:
        import sounddevice as sd
        print("\n音频输入设备：")
        print("-" * 60)
        for i, dev in enumerate(sd.query_devices()):
            inputs = int(dev.get("max_input_channels", 0))
            if inputs <= 0:
                continue
            name = dev.get("name", "")
            score = score_real_microphone(name)
            virtual = is_virtual_device(name)
            marker = "[REAL]" if score > 0 else ("[VIRTUAL]" if virtual else "[UNKNOWN]")
            print(f"  [{i:2d}] {marker} score={score:.2f} | {name}")
        print("-" * 60)

        best = pick_best_microphone([dict(d, index=i) for i, d in enumerate(sd.query_devices())])
        if best:
            print(f"\n推荐设备: [{best['index']}] {best['name']} (score={best['score']:.2f})")
        sys.exit(0)

    if args.test:
        import sounddevice as sd
        import numpy as np

        # 选择最佳设备
        device_idx = resolve_best_mic_index()
        if device_idx is None:
            print("错误：没有找到输入设备")
            sys.exit(1)

        dev = sd.query_devices(device_idx)
        print(f"使用设备: [{device_idx}] {dev['name']}")
        print(f"采样率: {args.sample_rate} Hz")
        print(f"录制时长: {args.seconds} 秒")
        print("\n请说话...")

        # 录制原始音频
        frames = int(args.sample_rate * args.seconds)
        original = sd.rec(frames, samplerate=args.sample_rate, channels=1,
                          dtype="int16", device=device_idx)
        sd.wait()

        print("录制完成，正在降噪...")

        # 降噪处理
        suppressor = NoiseSuppressor(sample_rate=args.sample_rate)
        original_bytes = original.tobytes()
        denoised_bytes = suppressor.process(original_bytes)
        denoised = np.frombuffer(denoised_bytes, dtype="<i2").reshape(-1, 1)

        # 计算指标
        orig_rms = float(np.sqrt(np.mean(np.square(original.astype(np.float32)))))
        denoised_rms = float(np.sqrt(np.mean(np.square(denoised.astype(np.float32)))))

        print(f"\n原始 RMS: {orig_rms:.2f}")
        print(f"降噪后 RMS: {denoised_rms:.2f}")
        print(f"降噪帧数: {suppressor.frame_count}")
        print(f"噪声底就绪: {suppressor.is_ready}")

        # 播放对比
        print("\n播放原始音频...")
        sd.play(original, args.sample_rate)
        sd.wait()

        print("播放降噪后音频...")
        sd.play(denoised, args.sample_rate)
        sd.wait()

        print("\n测试完成")
        sys.exit(0)

    parser.print_help()
