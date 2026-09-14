#!/usr/bin/env python3
"""Independent Mira Light voice-state motion demos.

These action-cluster scripts are tuned from the three reference videos in
Mira-Light-Voice-Cloud-Ready/docs/0525:
- listening: 0df6af9bf4b0303177c7b607efc3e988-听.mp4
- thinking: 0b5c990939c341f348ffc253b333e121-思考.mp4
- answer: 25059b3751e232cdc7c054d3ce610046-答.mp4
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass


NEUTRAL = 2048
NATURAL_POSE = (2048, 2150, 2048, 2130)
CLAMP_LO = 1688
CLAMP_HI = 2408
SERVO_CONTROL_PATH = "/home/sunrise/Desktop/four_servo_control.py"
DEFAULT_SPEEDS = (220, 180, 220, 200)
ANSWER_AUDIO_DELAY_SECONDS = 0.40
ANSWER_REPEAT_TO_SECONDS = 13.0

Pose = tuple[int, int, int, int]
Speeds = tuple[int, int, int, int]
TimelineMarker = tuple[float, list[int], str]


@dataclass(frozen=True)
class MotionStep:
    label: str
    pose: Pose
    speeds: Speeds
    hold: float


@dataclass(frozen=True)
class MotionDemo:
    id: str
    title: str
    video: str
    description: str
    script: tuple[MotionStep, ...]
    audio_delay_seconds: float = 0.0
    uses_answer_audio: bool = False
    repeat_to_seconds: float = 0.0
    pose_origin: Pose = NATURAL_POSE
    pose_scale: tuple[float, float, float, float] = (2.0, 2.0, 2.0, 2.0)
    speed_scale: float = 2.0


def step(label: str, p0: int, p1: int, p2: int, p3: int, speeds: Speeds, hold: float) -> MotionStep:
    return MotionStep(label=label, pose=(p0, p1, p2, p3), speeds=speeds, hold=hold)


LISTENING_SCRIPT: tuple[MotionStep, ...] = (
    step("enter book gaze", 2048, 2160, 1900, 2130, (120, 80, 80, 105), 0.16),
    step("lower toward desk", 2048, 2180, 1840, 2130, (130, 85, 85, 110), 0.22),
    step("settle on book plane", 2048, 2190, 1780, 2130, (115, 75, 75, 95), 0.28),
    step("prepare search left", 2010, 2185, 1800, 2070, (155, 85, 85, 125), 0.12),
    step("find book left", 1930, 2200, 1760, 2010, (190, 105, 105, 155), 0.30),
    step("left search rebound", 1985, 2185, 1810, 2060, (135, 80, 80, 110), 0.16),
    step("center inspect low", 2048, 2195, 1760, 2130, (145, 85, 85, 120), 0.22),
    step("tiny closer look", 2048, 2210, 1720, 2130, (130, 75, 75, 100), 0.14),
    step("closer rebound", 2048, 2185, 1810, 2130, (120, 75, 75, 95), 0.18),
    step("prepare search right", 2090, 2185, 1800, 2190, (155, 85, 85, 125), 0.12),
    step("find book right", 2170, 2200, 1760, 2250, (190, 105, 105, 155), 0.30),
    step("right search rebound", 2110, 2185, 1810, 2200, (135, 80, 80, 110), 0.16),
    step("return to book center", 2048, 2190, 1760, 2130, (145, 85, 85, 120), 0.22),
    step("confirm book found", 2048, 2220, 1700, 2130, (150, 90, 90, 120), 0.16),
    step("hold low attention", 2048, 2190, 1780, 2130, (100, 70, 70, 90), 0.34),
)


THINKING_SCRIPT: tuple[MotionStep, ...] = (
    step("enter thought low center", 2048, 2208, 1970, 2130, (180, 110, 110, 145), 0.12),
    step("thought swing 1 left", 1940, 2228, 1880, 1990, (220, 130, 130, 175), 0.22),
    step("thought swing 1 right", 2160, 2228, 1880, 2240, (220, 130, 130, 175), 0.22),
    step("thought swing 2 left", 1930, 2238, 1860, 1980, (230, 135, 135, 180), 0.22),
    step("thought swing 2 right", 2170, 2238, 1860, 2250, (230, 135, 135, 180), 0.22),
    step("thought swing 3 left", 1940, 2233, 1845, 2000, (220, 130, 130, 175), 0.22),
    step("thought swing 3 right", 2160, 2233, 1845, 2240, (220, 130, 130, 175), 0.22),
    step("left breathe down", 1940, 2228, 1845, 2010, (110, 75, 75, 100), 0.22),
    step("left breathe up", 1970, 2208, 1900, 2040, (120, 80, 80, 110), 0.18),
    step("return low center", 2048, 2198, 1920, 2130, (125, 75, 75, 105), 0.26),
    step("front deep pause", 2048, 2223, 1840, 2130, (85, 60, 60, 80), 0.42),
    step("prepare right thought", 2090, 2206, 1910, 2190, (130, 80, 80, 110), 0.16),
    step("right thought", 2160, 2218, 1870, 2240, (150, 90, 90, 125), 0.34),
    step("right breathe down", 2160, 2228, 1845, 2220, (85, 60, 60, 75), 0.28),
    step("right breathe up", 2120, 2208, 1900, 2180, (95, 65, 65, 85), 0.22),
    step("idea prepare", 2048, 2198, 1900, 2130, (120, 75, 75, 100), 0.16),
    step("idea lift half", 2048, 2238, 1920, 2130, (180, 110, 110, 140), 0.14),
    step("idea lift full", 2048, 2278, 1940, 2130, (230, 140, 140, 170), 0.22),
    step("idea small rebound", 2048, 2228, 1880, 2130, (120, 80, 80, 100), 0.18),
    step("ready to answer", 2048, 2198, 1900, 2130, (150, 90, 90, 120), 0.24),
)


ANSWER_SCRIPT: tuple[MotionStep, ...] = (
    step("pre-open prepare", 2048, 2160, 2020, 2130, (180, 110, 110, 150), 0.10),
    step("pre-open lift", 2048, 2260, 2110, 2130, (260, 160, 160, 210), 0.18),
    step("pre-open settle", 2048, 2220, 2060, 2130, (160, 100, 100, 140), 0.12),
    step("en front", 2048, 2220, 2060, 2130, (220, 135, 135, 180), 0.16),
    step("book name prep left", 2000, 2220, 2040, 2080, (220, 130, 130, 180), 0.08),
    step("book name left", 1940, 2250, 2020, 2020, (280, 160, 160, 220), 0.18),
    step("book name rebound", 1990, 2220, 2050, 2070, (170, 105, 105, 145), 0.10),
    step("author prep right", 2080, 2220, 2050, 2180, (220, 130, 130, 180), 0.08),
    step("author right", 2160, 2260, 2100, 2240, (280, 165, 165, 220), 0.18),
    step("designed center", 2048, 2210, 2000, 2130, (180, 110, 110, 150), 0.16),
    step("cute prep down", 2048, 2160, 1960, 2130, (180, 110, 110, 150), 0.10),
    step("cute lift", 1960, 2320, 2140, 2020, (340, 205, 205, 260), 0.18),
    step("cute rebound", 2080, 2240, 2040, 2190, (190, 120, 120, 160), 0.22),
    step("period lower", 2048, 2140, 1940, 2130, (160, 95, 95, 130), 0.28),
    step("period still", 2048, 2140, 1940, 2130, (80, 60, 60, 80), 0.16),
    step("second sentence open", 2048, 2220, 2060, 2130, (220, 135, 135, 180), 0.12),
    step("contrast left", 1960, 2240, 2020, 2040, (260, 150, 150, 205), 0.18),
    step("contrast rebound", 2020, 2210, 2040, 2090, (170, 100, 100, 140), 0.10),
    step("adult child prep", 2080, 2220, 2060, 2190, (220, 130, 130, 180), 0.08),
    step("adult child right", 2160, 2280, 2120, 2240, (290, 170, 170, 220), 0.20),
    step("family daily center", 2048, 2200, 2000, 2130, (180, 105, 105, 150), 0.20),
    step("punch pause down", 2048, 2130, 1920, 2130, (150, 95, 95, 120), 0.24),
    step("punch silence hold", 2048, 2130, 1920, 2130, (70, 55, 55, 70), 0.12),
    step("punch launch half", 2048, 2250, 2060, 2130, (300, 180, 180, 230), 0.08),
    step("punch up", 2048, 2350, 2200, 2130, (430, 250, 250, 320), 0.16),
    step("punch rebound", 2048, 2260, 2050, 2130, (190, 120, 120, 160), 0.08),
    step("laugh right", 2220, 2320, 2060, 2280, (360, 200, 200, 290), 0.14),
    step("laugh right rebound", 2120, 2240, 2020, 2200, (200, 120, 120, 160), 0.08),
    step("laugh left", 1880, 2320, 2120, 1980, (360, 200, 200, 290), 0.14),
    step("laugh left rebound", 1980, 2220, 2000, 2050, (200, 120, 120, 160), 0.14),
    step("final sentence open", 2048, 2230, 2060, 2130, (230, 140, 140, 180), 0.12),
    step("clear glance left", 1950, 2260, 2020, 2030, (280, 165, 165, 220), 0.18),
    step("knowledge right", 2160, 2300, 2120, 2230, (300, 180, 180, 230), 0.20),
    step("fits center", 2048, 2220, 2000, 2130, (190, 115, 115, 155), 0.18),
    step("ending cute", 1960, 2240, 2060, 2020, (230, 135, 135, 190), 0.22),
    step("ending soften", 2048, 2170, 1980, 2130, (150, 95, 95, 125), 0.22),
    step("return natural", 2048, 2150, 2048, 2130, (120, 80, 80, 100), 0.30),
)


DEMOS: dict[str, MotionDemo] = {
    "listening": MotionDemo(
        id="listening",
        title="听",
        video="0df6af9bf4b0303177c7b607efc3e988-听.mp4",
        description="动作簇式倾听：小幅注意力漂移、轻点头、可循环等待用户输入。",
        script=LISTENING_SCRIPT,
    ),
    "thinking": MotionDemo(
        id="thinking",
        title="想",
        video="0b5c990939c341f348ffc253b333e121-思考.mp4",
        description="动作簇式思考：低头搜索、呼吸停顿、两段式灵感抬起。",
        script=THINKING_SCRIPT,
        pose_scale=(3.0, 3.0, -5.0, 5.0),
    ),
    "answer": MotionDemo(
        id="answer",
        title="答",
        video="25059b3751e232cdc7c054d3ce610046-答.mp4",
        description="跟 12.5 秒讲书音频同步的顺序动作簇第一版。",
        script=ANSWER_SCRIPT,
        audio_delay_seconds=ANSWER_AUDIO_DELAY_SECONDS,
        uses_answer_audio=True,
        repeat_to_seconds=ANSWER_REPEAT_TO_SECONDS,
        pose_scale=(2.0, 2.0, 2.5, 2.5),
    ),
}


def clamp(value: int) -> int:
    return max(CLAMP_LO, min(CLAMP_HI, int(value)))


def scaled_pose(demo: MotionDemo, pose: Pose) -> list[int]:
    scaled: list[int] = []
    for index, value in enumerate(pose):
        origin = demo.pose_origin[index]
        scale = demo.pose_scale[index]
        scaled.append(clamp(round(origin + (int(value) - origin) * scale)))
    return scaled


def normalized_speeds(demo: MotionDemo, speeds: Speeds) -> list[int]:
    return [max(1, round(int(speed) * demo.speed_scale)) for speed in speeds]


def bounded_hold(hold: float) -> float:
    return max(0.0, float(hold))


def get_demo(demo_id: str) -> MotionDemo:
    try:
        return DEMOS[demo_id]
    except KeyError as exc:
        raise ValueError(f"Unknown voice motion demo: {demo_id}") from exc


def expanded_script(demo: MotionDemo | str) -> tuple[MotionStep, ...]:
    selected = get_demo(demo) if isinstance(demo, str) else demo
    target_seconds = max(0.0, float(selected.repeat_to_seconds))
    if not target_seconds or not selected.script:
        return selected.script
    expanded: list[MotionStep] = []
    elapsed = 0.0
    while elapsed < target_seconds:
        for step_item in selected.script:
            hold = bounded_hold(step_item.hold)
            remaining = round(target_seconds - elapsed, 3)
            if remaining <= 0:
                break
            if hold > remaining:
                expanded.append(
                    MotionStep(
                        label=step_item.label,
                        pose=step_item.pose,
                        speeds=step_item.speeds,
                        hold=remaining,
                    )
                )
                elapsed = target_seconds
                break
            expanded.append(step_item)
            elapsed = round(elapsed + hold, 3)
            if elapsed >= target_seconds:
                break
    return tuple(expanded)


def normalized_steps(demo: MotionDemo | str, *, time_scale: float = 1.0) -> list[tuple[str, list[int], list[int], float]]:
    selected = get_demo(demo) if isinstance(demo, str) else demo
    bounded_time_scale = max(0.05, float(time_scale))
    return [
        (
            step_item.label,
            scaled_pose(selected, step_item.pose),
            normalized_speeds(selected, step_item.speeds),
            round(bounded_hold(step_item.hold) * bounded_time_scale, 3),
        )
        for step_item in expanded_script(selected)
    ]


def normalized_timeline(demo: MotionDemo | str) -> list[TimelineMarker]:
    selected = get_demo(demo) if isinstance(demo, str) else demo
    timeline: list[TimelineMarker] = []
    elapsed = 0.0
    for step_item in expanded_script(selected):
        timeline.append((round(elapsed, 3), scaled_pose(selected, step_item.pose), step_item.label))
        elapsed += bounded_hold(step_item.hold)
    return timeline


def script_duration_seconds(demo: MotionDemo | str) -> float:
    selected = get_demo(demo) if isinstance(demo, str) else demo
    return round(sum(bounded_hold(step_item.hold) for step_item in expanded_script(selected)), 3)


def render_board_script(
    demo: MotionDemo | str,
    *,
    servo_control_path: str = SERVO_CONTROL_PATH,
    time_scale: float = 1.0,
) -> str:
    selected = get_demo(demo) if isinstance(demo, str) else demo
    steps = normalized_steps(selected, time_scale=time_scale)
    steps_json = json.dumps(steps, ensure_ascii=True)
    done_marker = f"mira_voice_motion_{selected.id}_done"
    return f"""python3 - <<'PY'
import json
import subprocess
import time

STEPS = json.loads({steps_json!r})
SERVO_CONTROL = {servo_control_path!r}
DONE_MARKER = {done_marker!r}

start = time.monotonic()
processes = []
for label, pose, speeds, hold in STEPS:
    command = ["python3", SERVO_CONTROL, "pose", *[str(int(v)) for v in pose], "--speeds", *[str(int(v)) for v in speeds]]
    elapsed = time.monotonic() - start
    print(f"{{elapsed:05.2f}}s {{label}} pose={{pose}} speeds={{speeds}} hold={{hold}}", flush=True)
    processes.append(subprocess.Popen(command))
    if hold > 0:
        time.sleep(float(hold))

deadline = time.monotonic() + 2.0
for process in processes:
    remaining = max(0.1, deadline - time.monotonic())
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        process.terminate()
print(DONE_MARKER, flush=True)
PY"""


def demo_payload(demo: MotionDemo | str, *, include_script: bool = True) -> dict:
    selected = get_demo(demo) if isinstance(demo, str) else demo
    payload = {
        "id": selected.id,
        "title": selected.title,
        "video": selected.video,
        "description": selected.description,
        "timeline": normalized_timeline(selected),
        "timelineMarkers": len(expanded_script(selected)),
        "steps": normalized_steps(selected),
        "scriptDurationSeconds": script_duration_seconds(selected),
        "baseScriptSteps": len(selected.script),
        "repeatToSeconds": selected.repeat_to_seconds,
        "poseOrigin": list(selected.pose_origin),
        "poseScale": list(selected.pose_scale),
        "audioDelaySeconds": selected.audio_delay_seconds,
        "usesAnswerAudio": selected.uses_answer_audio,
        "servoControlPath": SERVO_CONTROL_PATH,
        "speeds": None,
        "amplitudeScale": 1.0,
        "speedScale": selected.speed_scale,
        "poseBias": [0, 0, 0, 0],
    }
    if include_script:
        payload["boardScript"] = render_board_script(selected)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("demo", nargs="?", default="answer", choices=sorted(DEMOS))
    parser.add_argument("--dry-run", action="store_true", help="Print demo metadata and generated board script")
    args = parser.parse_args()
    payload = demo_payload(args.demo, include_script=True)
    if args.dry_run:
        print(json.dumps({k: v for k, v in payload.items() if k != "boardScript"}, indent=2, ensure_ascii=False))
        print("\n--- board script ---")
    print(payload["boardScript"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
