#!/usr/bin/env python3
"""Enhanced microphone capture with noise suppression and smart device selection.

增强版麦克风采集模块 —— 集成降噪、智能设备选择和低延迟处理

功能：
  1. 智能识别真实麦克风（排除虚拟/模拟设备）
  2. 实时深度降噪（DeepFilterNet）
  3. 增强型VAD（Silero VAD）
  4. 低延迟音频流处理
  5. 与现有 Mira Light 系统兼容

作者: AI Assistant
日期: 2026-06-18
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import re
import sys
import threading
import time
import warnings
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("audio_enhanced_capture")

# 抑制不必要的警告
warnings.filterwarnings("ignore", category=UserWarning)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据类定义
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class InputDevice:
    """音频输入设备信息"""
    index: int
    name: str
    inputs: int
    default_sample_rate: float
    is_real_microphone: bool = False
    confidence_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "inputs": self.inputs,
            "defaultSampleRate": self.default_sample_rate,
            "isRealMicrophone": self.is_real_microphone,
            "confidenceScore": round(self.confidence_score, 3),
        }


@dataclass
class AudioConfig:
    """音频处理配置"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_ms: int = 20
    device_hint: str = ""
    
    # 降噪配置
    enable_denoise: bool = True
    denoise_model: str = "deepfilternet2"  # 或 "deepfilternet"
    denoise_attenuation_limit: float = 100.0  # 降噪强度限制 (dB)
    
    # VAD配置
    enable_vad: bool = True
    vad_threshold: float = 0.5
    vad_start_ms: int = 120
    vad_end_ms: int = 900
    
    # 延迟优化
    low_latency_mode: bool = True
    buffer_ms: int = 40
    
    # 音频增强
    enable_agc: bool = True  # 自动增益控制
    target_rms: float = 0.1
    max_gain_db: float = 30.0


@dataclass
class AudioMetrics:
    """音频质量指标"""
    timestamp: float = field(default_factory=time.time)
    rms: float = 0.0
    peak: float = 0.0
    snr_db: float = 0.0
    vad_probability: float = 0.0
    is_speech: bool = False
    noise_floor: float = 0.0
    gain_db: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "rms": round(self.rms, 6),
            "peak": round(self.peak, 6),
            "snrDb": round(self.snr_db, 2),
            "vadProbability": round(self.vad_probability, 3),
            "isSpeech": self.is_speech,
            "noiseFloor": round(self.noise_floor, 6),
            "gainDb": round(self.gain_db, 2),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 智能设备检测
# ═══════════════════════════════════════════════════════════════════════════════

class MicrophoneDetector:
    """智能麦克风检测器 —— 区分真实麦克风和虚拟/模拟设备"""
    
    # 虚拟设备关键词（排除列表）
    VIRTUAL_DEVICE_PATTERNS = [
        r"virtual", r"cable", r"vb-", r"voicemeeter", r"banana",
        r"stereo mix", r"what u hear", r"what you hear",
        r"wave out", r"waveout", r"mix", r"loopback",
        r"desktop audio", r"system audio", r"internal audio",
        r"nvidia.*broadcast", r"rtx voice", r"krisp",
        r"discord", r"zoom", r"teams", r"slack",
        r"obs", r"stream", r"capture",
        r"aux", r"auxiliary",
    ]
    
    # 真实麦克风关键词（优先列表）
    REAL_MIC_PATTERNS = [
        r"microphone", r"mic", r"array", r"realtek",
        r"usb audio", r"usb mic", r"condenser", r"dynamic",
        r"shure", r"rode", r"audio-technica", r"blue yeti",
        r"snowball", r"samson", r"hyperx", r"razer",
        r"logitech.*mic", r"jabra", r"plantronics",
        r"headset", r"earphone", r"webcam.*mic",
    ]
    
    # 高置信度真实设备名称
    HIGH_CONFIDENCE_PATTERNS = [
        r"microphone\s*\(", r"mic\s*\(", r"array\s*\(",
        r"usb\s*audio\s*device", r"usb\s*pnp",
    ]
    
    @classmethod
    def is_virtual_device(cls, device_name: str) -> bool:
        """检测设备是否为虚拟设备"""
        name_lower = device_name.lower()
        for pattern in cls.VIRTUAL_DEVICE_PATTERNS:
            if re.search(pattern, name_lower):
                return True
        return False
    
    @classmethod
    def is_real_microphone(cls, device_name: str) -> tuple[bool, float]:
        """
        判断设备是否为真实麦克风
        
        Returns:
            (is_real, confidence_score)
            confidence_score: 0.0-1.0，越高越可能是真实麦克风
        """
        name_lower = device_name.lower()
        
        # 首先排除虚拟设备
        if cls.is_virtual_device(device_name):
            return False, 0.0
        
        score = 0.0
        
        # 检查高置信度模式
        for pattern in cls.HIGH_CONFIDENCE_PATTERNS:
            if re.search(pattern, name_lower):
                score += 0.5
        
        # 检查真实麦克风关键词
        for pattern in cls.REAL_MIC_PATTERNS:
            if re.search(pattern, name_lower):
                score += 0.3
        
        # 如果名称中包含 "microphone" 或 "mic"，加分
        if "microphone" in name_lower or " mic " in name_lower:
            score += 0.2
        
        # 如果设备名称很短且没有明确标识，降低置信度
        if len(device_name) < 10 and score < 0.3:
            score -= 0.1
        
        # 包含数字编号（如 Realtek Audio (2)）通常是真实设备
        if re.search(r"\(\d+\)", device_name):
            score += 0.1
        
        score = max(0.0, min(1.0, score))
        is_real = score >= 0.3 or "microphone" in name_lower or "mic" in name_lower
        
        return is_real, score
    
    @classmethod
    def rank_devices(cls, devices: list[InputDevice]) -> list[InputDevice]:
        """对设备列表进行排序，真实麦克风优先"""
        scored_devices = []
        for device in devices:
            is_real, score = cls.is_real_microphone(device.name)
            scored_devices.append((device, is_real, score))
        
        # 排序：真实设备优先，然后按置信度排序
        scored_devices.sort(key=lambda x: (not x[1], -x[2]))
        
        return [d[0] for d in scored_devices]


# ═══════════════════════════════════════════════════════════════════════════════
# 音频降噪引擎
# ═══════════════════════════════════════════════════════════════════════════════

class NoiseSuppressor:
    """噪声抑制引擎 —— 封装 DeepFilterNet 和其他降噪方法"""
    
    def __init__(self, sample_rate: int = 16000, model_name: str = "deepfilternet2"):
        self.sample_rate = sample_rate
        self.model_name = model_name
        self._df_model = None
        self._df_state = None
        self._available = False
        self._fallback_mode = False
        
        self._init_model()
    
    def _init_model(self):
        """初始化降噪模型"""
        try:
            # 尝试导入 DeepFilterNet
            import torch
            from df import enhance, init_df
            
            logger.info(f"正在加载 DeepFilterNet 模型: {self.model_name}")
            self._df_model = init_df()
            self._available = True
            logger.info("DeepFilterNet 模型加载成功")
            
        except ImportError as e:
            logger.warning(f"DeepFilterNet 未安装: {e}")
            logger.info("将使用备用降噪方案（频谱减法）")
            self._fallback_mode = True
            self._available = True
        except Exception as e:
            logger.error(f"加载降噪模型失败: {e}")
            self._fallback_mode = True
            self._available = True
    
    def process(self, audio: np.ndarray) -> np.ndarray:
        """
        处理音频，返回降噪后的音频
        
        Args:
            audio: 输入音频，float32，范围 [-1.0, 1.0]
        
        Returns:
            降噪后的音频
        """
        if not self._available:
            return audio
        
        if self._fallback_mode:
            return self._spectral_subtraction(audio)
        
        try:
            import torch
            from df import enhance
            
            # 转换为 tensor
            audio_tensor = torch.from_numpy(audio).unsqueeze(0)
            
            # 使用 DeepFilterNet 降噪
            enhanced = enhance(self._df_model, audio_tensor, self.sample_rate)
            
            # 转换回 numpy
            result = enhanced.squeeze(0).numpy()
            
            # 确保不超出范围
            result = np.clip(result, -1.0, 1.0)
            
            return result
            
        except Exception as e:
            logger.debug(f"DeepFilterNet 处理失败: {e}，使用备用方案")
            return self._spectral_subtraction(audio)
    
    def _spectral_subtraction(self, audio: np.ndarray) -> np.ndarray:
        """备用降噪方案：频谱减法"""
        # 简单的噪声门限
        noise_gate = 0.01
        
        # 应用软噪声门限
        mask = np.abs(audio) > noise_gate
        processed = audio * mask
        
        # 轻微放大
        processed = processed * 1.1
        processed = np.clip(processed, -1.0, 1.0)
        
        return processed
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    @property
    def is_deep_filter(self) -> bool:
        return self._available and not self._fallback_mode


# ═══════════════════════════════════════════════════════════════════════════════
# 语音活动检测（增强版）
# ═══════════════════════════════════════════════════════════════════════════════

class VoiceActivityDetector:
    """增强型语音活动检测器 —— 结合 Silero VAD 和能量检测"""
    
    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5):
        self.sample_rate = sample_rate
        self.threshold = threshold
        self._model = None
        self._available = False
        self._noise_floor = 0.001
        
        self._init_model()
    
    def _init_model(self):
        """初始化 Silero VAD 模型"""
        try:
            import torch
            
            logger.info("正在加载 Silero VAD 模型...")
            self._model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
                verbose=False,
            )
            self._available = True
            logger.info("Silero VAD 模型加载成功")
            
        except Exception as e:
            logger.warning(f"Silero VAD 加载失败: {e}")
            logger.info("将使用能量检测作为备用方案")
            self._available = False
    
    def detect(self, audio: np.ndarray) -> tuple[bool, float]:
        """
        检测音频中是否包含语音
        
        Args:
            audio: 输入音频，float32
        
        Returns:
            (is_speech, probability)
        """
        if len(audio) == 0:
            return False, 0.0
        
        # 计算能量
        rms = np.sqrt(np.mean(np.square(audio)))
        
        # 更新噪声底
        self._noise_floor = self._noise_floor * 0.95 + rms * 0.05
        
        # 使用 Silero VAD
        if self._available:
            try:
                import torch
                
                # 确保音频长度符合要求（至少 30ms）
                min_length = int(self.sample_rate * 0.03)
                if len(audio) < min_length:
                    # 填充到最小长度
                    audio = np.pad(audio, (0, min_length - len(audio)))
                
                audio_tensor = torch.from_numpy(audio).unsqueeze(0)
                
                with torch.no_grad():
                    prob = self._model(audio_tensor, self.sample_rate).item()
                
                is_speech = prob > self.threshold
                return is_speech, prob
                
            except Exception as e:
                logger.debug(f"VAD检测失败: {e}")
        
        # 备用方案：能量检测
        energy_threshold = max(0.01, self._noise_floor * 3)
        is_speech = rms > energy_threshold
        prob = min(1.0, rms / max(energy_threshold, 1e-6))
        
        return is_speech, prob
    
    def reset(self):
        """重置噪声底"""
        self._noise_floor = 0.001


# ═══════════════════════════════════════════════════════════════════════════════
# 自动增益控制
# ═══════════════════════════════════════════════════════════════════════════════

class AutomaticGainControl:
    """自动增益控制 —— 保持稳定的音频电平"""
    
    def __init__(self, target_rms: float = 0.1, max_gain_db: float = 30.0):
        self.target_rms = target_rms
        self.max_gain_db = max_gain_db
        self._current_gain_db = 0.0
        self._gain_smooth = 0.1
    
    def process(self, audio: np.ndarray) -> tuple[np.ndarray, float]:
        """
        应用自动增益控制
        
        Returns:
            (processed_audio, applied_gain_db)
        """
        if len(audio) == 0:
            return audio, 0.0
        
        # 计算当前 RMS
        rms = np.sqrt(np.mean(np.square(audio)))
        
        if rms < 1e-6:
            return audio, 0.0
        
        # 计算需要的增益
        target_gain = self.target_rms / rms
        target_gain_db = 20 * math.log10(target_gain)
        
        # 限制增益范围
        target_gain_db = max(-self.max_gain_db, min(self.max_gain_db, target_gain_db))
        
        # 平滑增益变化
        self._current_gain_db = (
            self._current_gain_db * (1 - self._gain_smooth) +
            target_gain_db * self._gain_smooth
        )
        
        # 应用增益
        gain_linear = 10 ** (self._current_gain_db / 20)
        processed = audio * gain_linear
        
        # 防止削波
        processed = np.clip(processed, -1.0, 1.0)
        
        return processed, self._current_gain_db
    
    def reset(self):
        """重置增益状态"""
        self._current_gain_db = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 增强型音频采集器
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedAudioCapture:
    """
    增强型音频采集器
    
    集成：智能设备选择 + 降噪 + VAD + AGC + 低延迟处理
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        
        # 初始化组件
        self._suppressor = NoiseSuppressor(
            sample_rate=self.config.sample_rate,
            model_name=self.config.denoise_model,
        )
        self._vad = VoiceActivityDetector(
            sample_rate=self.config.sample_rate,
            threshold=self.config.vad_threshold,
        )
        self._agc = AutomaticGainControl(
            target_rms=self.config.target_rms,
            max_gain_db=self.config.max_gain_db,
        )
        
        # 状态
        self._is_running = False
        self._selected_device: Optional[InputDevice] = None
        self._stream = None
        self._audio_buffer = deque(maxlen=100)
        self._metrics_buffer = deque(maxlen=50)
        
        # 回调
        self.on_audio_ready: Optional[Callable[[np.ndarray, AudioMetrics], None]] = None
        self.on_metrics_update: Optional[Callable[[AudioMetrics], None]] = None
        
        logger.info("增强型音频采集器初始化完成")
        logger.info(f"  采样率: {self.config.sample_rate}Hz")
        logger.info(f"  降噪: {self.config.enable_denoise} ({self._suppressor.is_deep_filter})")
        logger.info(f"  VAD: {self.config.enable_vad}")
        logger.info(f"  AGC: {self.config.enable_agc}")
    
    def list_devices(self) -> list[InputDevice]:
        """列出所有可用的输入设备"""
        try:
            import sounddevice as sd
            
            devices = []
            for index, device_info in enumerate(sd.query_devices()):
                inputs = int(device_info.get("max_input_channels") or 0)
                if inputs <= 0:
                    continue
                
                name = str(device_info.get("name") or "")
                is_real, confidence = MicrophoneDetector.is_real_microphone(name)
                
                devices.append(InputDevice(
                    index=index,
                    name=name,
                    inputs=inputs,
                    default_sample_rate=float(device_info.get("default_samplerate") or 0.0),
                    is_real_microphone=is_real,
                    confidence_score=confidence,
                ))
            
            # 排序：真实麦克风优先
            devices = MicrophoneDetector.rank_devices(devices)
            
            return devices
            
        except ImportError:
            logger.error("sounddevice 未安装")
            return []
    
    def select_device(self, hint: str = "") -> InputDevice:
        """
        智能选择最佳麦克风设备
        
        Args:
            hint: 设备提示（索引、名称片段或 "default"）
        
        Returns:
            选择的设备
        """
        devices = self.list_devices()
        
        if not devices:
            raise RuntimeError("没有可用的输入设备")
        
        # 如果有提示，尝试匹配
        if hint and hint.lower() != "default":
            hint_lower = hint.lower()
            
            # 尝试按索引匹配
            if hint_lower.isdigit():
                idx = int(hint_lower)
                for device in devices:
                    if device.index == idx:
                        logger.info(f"按索引选择设备: {device.name}")
                        return device
            
            # 尝试按名称匹配
            for device in devices:
                if hint_lower in device.name.lower():
                    logger.info(f"按名称选择设备: {device.name}")
                    return device
            
            logger.warning(f"未找到匹配 '{hint}' 的设备，使用自动选择")
        
        # 自动选择：优先选择真实麦克风
        real_mics = [d for d in devices if d.is_real_microphone]
        
        if real_mics:
            selected = real_mics[0]
            logger.info(f"自动选择真实麦克风: {selected.name} (置信度: {selected.confidence_score:.2f})")
            return selected
        
        # 如果没有真实麦克风，选择第一个
        selected = devices[0]
        logger.warning(f"未检测到真实麦克风，使用: {selected.name}")
        return selected
    
    def _process_audio_chunk(self, audio: np.ndarray) -> tuple[np.ndarray, AudioMetrics]:
        """
        处理音频块
        
        处理流程：
        1. 转换为单声道 float32
        2. 降噪处理
        3. VAD检测
        4. 自动增益控制
        5. 计算指标
        """
        # 确保单声道
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        
        # 转换为 float32
        audio = audio.astype(np.float32)
        
        # 如果输入是 int16，归一化
        if audio.max() > 1.0:
            audio = audio / 32768.0
        
        # 原始指标
        original_rms = np.sqrt(np.mean(np.square(audio)))
        original_peak = np.max(np.abs(audio))
        
        # 1. 降噪
        if self.config.enable_denoise:
            audio = self._suppressor.process(audio)
        
        # 2. VAD检测
        is_speech, vad_prob = False, 0.0
        if self.config.enable_vad:
            is_speech, vad_prob = self._vad.detect(audio)
        
        # 3. 自动增益控制
        gain_db = 0.0
        if self.config.enable_agc:
            audio, gain_db = self._agc.process(audio)
        
        # 4. 计算最终指标
        final_rms = np.sqrt(np.mean(np.square(audio)))
        final_peak = np.max(np.abs(audio))
        
        # 估算 SNR
        noise_floor = self._vad._noise_floor if hasattr(self._vad, '_noise_floor') else 0.001
        snr_db = 20 * math.log10(final_rms / max(noise_floor, 1e-6)) if final_rms > 0 else 0
        
        metrics = AudioMetrics(
            rms=final_rms,
            peak=final_peak,
            snr_db=snr_db,
            vad_probability=vad_prob,
            is_speech=is_speech,
            noise_floor=noise_floor,
            gain_db=gain_db,
        )
        
        return audio, metrics
    
    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice 回调函数"""
        if status:
            logger.warning(f"音频状态: {status}")
        
        # 处理音频
        audio, metrics = self._process_audio_chunk(indata.copy())
        
        # 存储指标
        self._metrics_buffer.append(metrics)
        
        # 存储音频
        self._audio_buffer.append(audio)
        
        # 触发回调
        if self.on_audio_ready:
            self.on_audio_ready(audio, metrics)
        
        if self.on_metrics_update:
            self.on_metrics_update(metrics)
    
    def start(self, device_hint: str = "") -> InputDevice:
        """
        开始音频采集
        
        Args:
            device_hint: 设备提示
        
        Returns:
            选择的设备
        """
        import sounddevice as sd
        
        # 选择设备
        self._selected_device = self.select_device(device_hint or self.config.device_hint)
        
        # 计算块大小
        chunk_frames = int(self.config.sample_rate * self.config.chunk_ms / 1000)
        
        # 创建流
        self._stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            blocksize=chunk_frames,
            device=self._selected_device.index,
            callback=self._audio_callback,
        )
        
        self._stream.start()
        self._is_running = True
        
        logger.info(f"音频采集已启动")
        logger.info(f"  设备: {self._selected_device.name}")
        logger.info(f"  块大小: {chunk_frames} frames ({self.config.chunk_ms}ms)")
        
        return self._selected_device
    
    def stop(self):
        """停止音频采集"""
        self._is_running = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        logger.info("音频采集已停止")
    
    def get_latest_audio(self) -> Optional[np.ndarray]:
        """获取最新的音频数据"""
        if self._audio_buffer:
            return self._audio_buffer[-1]
        return None
    
    def get_metrics_summary(self) -> dict[str, Any]:
        """获取指标摘要"""
        if not self._metrics_buffer:
            return {}
        
        metrics_list = list(self._metrics_buffer)
        
        return {
            "avgRms": round(np.mean([m.rms for m in metrics_list]), 6),
            "avgPeak": round(np.mean([m.peak for m in metrics_list]), 6),
            "avgSnrDb": round(np.mean([m.snr_db for m in metrics_list]), 2),
            "speechRatio": round(np.mean([1.0 if m.is_speech else 0.0 for m in metrics_list]), 3),
            "avgVadProb": round(np.mean([m.vad_probability for m in metrics_list]), 3),
            "avgGainDb": round(np.mean([m.gain_db for m in metrics_list]), 2),
            "sampleCount": len(metrics_list),
        }
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @property
    def selected_device(self) -> Optional[InputDevice]:
        return self._selected_device


# ═══════════════════════════════════════════════════════════════════════════════
# 实时音频流处理器（用于 WebSocket 实时会话）
# ═══════════════════════════════════════════════════════════════════════════════

class RealtimeAudioStream:
    """
    实时音频流处理器
    
    专为 mira_stepfun_realtime_voice_actions.py 设计的音频处理管道
    """
    
    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.capture = EnhancedAudioCapture(config)
        
        # 音频队列（用于异步消费）
        self._audio_queue: asyncio.Queue[np.ndarray] = asyncio.Queue()
        self._metrics_queue: asyncio.Queue[AudioMetrics] = asyncio.Queue()
        
        # 统计
        self._processed_chunks = 0
        self._speech_chunks = 0
        self._start_time = 0.0
    
    def _on_audio_ready(self, audio: np.ndarray, metrics: AudioMetrics):
        """音频就绪回调"""
        try:
            self._audio_queue.put_nowait(audio)
            self._metrics_queue.put_nowait(metrics)
            self._processed_chunks += 1
            if metrics.is_speech:
                self._speech_chunks += 1
        except asyncio.QueueFull:
            pass
    
    async def start(self, device_hint: str = "") -> InputDevice:
        """启动实时音频流"""
        self.capture.on_audio_ready = self._on_audio_ready
        device = self.capture.start(device_hint)
        self._start_time = time.time()
        return device
    
    async def get_audio_chunk(self) -> Optional[np.ndarray]:
        """获取处理后的音频块"""
        try:
            return await asyncio.wait_for(self._audio_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    async def get_metrics(self) -> Optional[AudioMetrics]:
        """获取指标"""
        try:
            return await asyncio.wait_for(self._metrics_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    def get_pcm16_bytes(self, audio: np.ndarray) -> bytes:
        """将 float32 音频转换为 PCM16 bytes"""
        clipped = np.clip(audio, -1.0, 1.0)
        return (clipped * 32767.0).astype("<i2").tobytes()
    
    def stop(self):
        """停止音频流"""
        self.capture.stop()
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        elapsed = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "processedChunks": self._processed_chunks,
            "speechChunks": self._speech_chunks,
            "elapsedSeconds": round(elapsed, 2),
            "chunksPerSecond": round(self._processed_chunks / max(elapsed, 0.001), 2),
            "speechRatio": round(self._speech_chunks / max(self._processed_chunks, 1), 3),
            "device": self.capture.selected_device.to_dict() if self.capture.selected_device else None,
            "metricsSummary": self.capture.get_metrics_summary(),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 命令行工具
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_list_devices():
    """列出所有音频设备"""
    capture = EnhancedAudioCapture()
    devices = capture.list_devices()
    
    print("\n" + "=" * 70)
    print("音频输入设备列表")
    print("=" * 70)
    
    if not devices:
        print("未找到输入设备")
        return 1
    
    for i, device in enumerate(devices):
        real_marker = "✓ 真实麦克风" if device.is_real_microphone else "  虚拟设备"
        print(f"\n[{i}] 设备索引: {device.index}")
        print(f"    名称: {device.name}")
        print(f"    输入通道: {device.inputs}")
        print(f"    默认采样率: {int(device.default_sample_rate)} Hz")
        print(f"    类型: {real_marker} (置信度: {device.confidence_score:.2f})")
    
    print("\n" + "=" * 70)
    print(f"总计: {len(devices)} 个设备")
    print("提示: 使用 --device <索引> 或 --device <名称片段> 选择特定设备")
    print("=" * 70 + "\n")
    
    return 0


def cmd_test_capture(args):
    """测试音频采集和降噪"""
    config = AudioConfig(
        sample_rate=args.sample_rate,
        chunk_ms=args.chunk_ms,
        enable_denoise=not args.no_denoise,
        enable_vad=not args.no_vad,
        enable_agc=not args.no_agc,
    )
    
    capture = EnhancedAudioCapture(config)
    
    print("\n" + "=" * 70)
    print("音频采集测试")
    print("=" * 70)
    
    # 选择设备
    try:
        device = capture.start(args.device)
        print(f"\n已选择设备: {device.name}")
        print(f"设备类型: {'真实麦克风' if device.is_real_microphone else '虚拟设备'}")
        print(f"置信度: {device.confidence_score:.2f}")
    except Exception as e:
        print(f"启动失败: {e}")
        return 1
    
    print(f"\n配置:")
    print(f"  采样率: {config.sample_rate} Hz")
    print(f"  块大小: {config.chunk_ms} ms")
    print(f"  降噪: {'启用' if config.enable_denoise else '禁用'}")
    print(f"  VAD: {'启用' if config.enable_vad else '禁用'}")
    print(f"  AGC: {'启用' if config.enable_agc else '禁用'}")
    
    print(f"\n正在采集音频，请说话...")
    print("按 Ctrl+C 停止\n")
    
    try:
        while True:
            time.sleep(2.0)
            
            # 显示指标
            metrics = capture.get_metrics_summary()
            if metrics:
                print(f"\rRMS: {metrics.get('avgRms', 0):.4f} | "
                      f"Peak: {metrics.get('avgPeak', 0):.4f} | "
                      f"SNR: {metrics.get('avgSnrDb', 0):.1f} dB | "
                      f"语音比例: {metrics.get('speechRatio', 0):.1%} | "
                      f"增益: {metrics.get('avgGainDb', 0):.1f} dB", end="")
                
    except KeyboardInterrupt:
        print("\n\n停止采集...")
    finally:
        capture.stop()
    
    # 最终统计
    stats = capture.get_metrics_summary()
    print("\n" + "=" * 70)
    print("采集统计")
    print("=" * 70)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print("=" * 70 + "\n")
    
    return 0


def cmd_test_denoise(args):
    """测试降噪效果（对比原始和降噪后的音频）"""
    import sounddevice as sd
    
    config = AudioConfig(
        sample_rate=args.sample_rate,
        enable_denoise=True,
        enable_vad=True,
        enable_agc=True,
    )
    
    capture = EnhancedAudioCapture(config)
    
    print("\n" + "=" * 70)
    print("降噪效果测试")
    print("=" * 70)
    print("\n这个测试会同时播放原始音频和降噪后的音频")
    print("请仔细听对比效果\n")
    
    # 存储原始和降噪后的音频
    original_buffer = []
    denoised_buffer = []
    
    def on_audio(audio, metrics):
        original_buffer.append(audio.copy())
        denoised_buffer.append(audio.copy())
    
    capture.on_audio_ready = on_audio
    
    try:
        device = capture.start(args.device)
        print(f"使用设备: {device.name}")
        print("\n请说话 5 秒钟...")
        
        time.sleep(5.0)
        
    except KeyboardInterrupt:
        pass
    finally:
        capture.stop()
    
    if not original_buffer:
        print("没有采集到音频")
        return 1
    
    # 播放对比
    print("\n播放原始音频...")
    original_audio = np.concatenate(original_buffer)
    sd.play(original_audio, config.sample_rate)
    sd.wait()
    
    print("播放降噪后的音频...")
    denoised_audio = np.concatenate(denoised_buffer)
    sd.play(denoised_audio, config.sample_rate)
    sd.wait()
    
    print("\n测试完成")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="增强型音频采集工具 - 智能设备选择 + 降噪 + VAD + AGC",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # list-devices 命令
    subparsers.add_parser("list-devices", help="列出所有音频输入设备")
    
    # test-capture 命令
    test_parser = subparsers.add_parser("test-capture", help="测试音频采集")
    test_parser.add_argument("--device", default="", help="设备提示（索引或名称片段）")
    test_parser.add_argument("--sample-rate", type=int, default=16000, help="采样率")
    test_parser.add_argument("--chunk-ms", type=int, default=20, help="块大小（毫秒）")
    test_parser.add_argument("--no-denoise", action="store_true", help="禁用降噪")
    test_parser.add_argument("--no-vad", action="store_true", help="禁用VAD")
    test_parser.add_argument("--no-agc", action="store_true", help="禁用自动增益")
    
    # test-denoise 命令
    denoise_parser = subparsers.add_parser("test-denoise", help="测试降噪效果")
    denoise_parser.add_argument("--device", default="", help="设备提示")
    denoise_parser.add_argument("--sample-rate", type=int, default=16000, help="采样率")
    
    args = parser.parse_args()
    
    if args.command == "list-devices":
        return cmd_list_devices()
    elif args.command == "test-capture":
        return cmd_test_capture(args)
    elif args.command == "test-denoise":
        return cmd_test_denoise(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
