#!/usr/bin/env python3
import argparse
import base64
import json
import math
import mimetypes
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]
DEFAULT_MANIFEST_PATH = ROOT / "manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "outputs"
DEFAULT_STATE_DIR = ROOT / ".runtime" / "state"
DEFAULT_STATE_PATH = DEFAULT_STATE_DIR / "pipeline-state.json"
DEFAULT_CAPTURE_IMAGE_PATH = Path.home() / ".openclaw" / "workspace" / ".cache" / "localmac-camera" / "latest.jpg"
DEFAULT_FACE_DETECTOR = ROOT / "detect_faces.swift"
DEFAULT_MODEL = "doubao-seedream-5-0-260128"
DEFAULT_SIZE = "1920x1920"
DEFAULT_RESPONSE_FORMAT = "url"
DEFAULT_API_URL = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
DEFAULT_TIMEOUT = 180
DEFAULT_BURST_COUNT = 5
DEFAULT_BURST_INTERVAL_SECONDS = 0.8
DEFAULT_RECOVERY_PAUSE_SECONDS = 1.2
DEFAULT_OUTPUT_VALIDATION_RETRIES = max(_env_int("CAMERA_RENDER_OUTPUT_VALIDATION_RETRIES", 1), 0)
DEFAULT_STYLE_PROMPT = "自然光、空气感、电影截图感的吉卜力旅行场景插画"
DEFAULT_POSE_OPTIONS = (
    {
        "id": "standing",
        "label": "站着",
        "prompt": "人物姿势固定为站着。",
    },
    {
        "id": "sitting",
        "label": "坐着",
        "prompt": "人物姿势固定为坐着。",
    },
)
MIN_PRIMARY_FACE_AREA_RATIO = 0.035
MAX_PRIMARY_FACE_CENTER_DISTANCE = 0.32
MIN_PRIMARY_FACE_EDGE_MARGIN = 0.02
COMPETING_FACE_AREA_RATIO = 0.55
COMPETING_FACE_CENTER_DISTANCE_DELTA = 0.08
PORTRAIT_FOCUS_MIN_WIDTH_RATIO = 0.55
PORTRAIT_FOCUS_MAX_WIDTH_RATIO = 0.82
PORTRAIT_FOCUS_FACE_WIDTH_MULTIPLIER = 4.0


def resolve_default_capture_script(root: Path = ROOT) -> Path:
    staged = root / "mac-camera-shot"
    if staged.is_file():
        return staged
    staged = root / "macos-camera" / "mac-camera-shot"
    if staged.is_file():
        return staged
    return (
        root.parents[1]
        / "0313"
        / "openclaw-ha-blueprint"
        / "scripts"
        / "macos-camera"
        / "local-macos"
        / "mac-camera-shot"
    )


DEFAULT_CAPTURE_SCRIPT = resolve_default_capture_script()


def choose_pose(choice=random.choice) -> dict[str, str]:
    return dict(choice(list(DEFAULT_POSE_OPTIONS)))


def _face_center_distance(face: dict[str, object]) -> float:
    center_x = float(face.get("center_x", 0.5))
    center_y = float(face.get("center_y", 0.5))
    return math.hypot(center_x - 0.5, center_y - 0.5)


def _single_face_subject_fallback(detection: dict[str, object]) -> dict[str, object] | None:
    face_count = int(detection.get("face_count", 0))
    if face_count != 1:
        return None
    return {
        "selected_face_index": 0,
        "candidate_face_count": face_count,
        "reason": "single_face_fallback",
        "subject_score": float(detection.get("largest_face_area_ratio", 0.0)),
    }


def _subject_candidates(
    detection: dict[str, object],
    *,
    enforce_thresholds: bool,
) -> list[dict[str, object]]:
    faces = detection.get("faces") or []
    if not isinstance(faces, list) or not faces:
        return []

    candidates: list[dict[str, object]] = []
    for index, face in enumerate(faces):
        area_ratio = float(face.get("area_ratio", 0.0))
        edge_margin = float(face.get("edge_margin", 0.0))
        center_distance = _face_center_distance(face)
        if enforce_thresholds:
            if area_ratio < MIN_PRIMARY_FACE_AREA_RATIO:
                continue
            if edge_margin < MIN_PRIMARY_FACE_EDGE_MARGIN:
                continue
        elif area_ratio <= 0.0:
            continue
        candidates.append(
            {
                **face,
                "index": index,
                "area_ratio": area_ratio,
                "edge_margin": edge_margin,
                "center_distance": center_distance,
                "subject_score": area_ratio * 4.0 - center_distance * 2.0,
            }
        )
    return candidates


def _subject_selection_payload(
    selected: dict[str, object],
    *,
    candidate_face_count: int,
    reason: str,
) -> dict[str, object]:
    payload = {
        "selected_face_index": int(selected["index"]),
        "candidate_face_count": candidate_face_count,
        "subject_score": float(selected["subject_score"]),
        "reason": reason,
    }
    for key in ("center_distance", "area_ratio", "edge_margin"):
        if key in selected:
            payload[key] = float(selected[key])
    return payload


def select_primary_subject(detection: dict[str, object]) -> dict[str, object] | None:
    single_face = _single_face_subject_fallback(detection)
    if single_face is not None:
        return single_face

    faces = detection.get("faces") or []
    candidates = _subject_candidates(detection, enforce_thresholds=True)
    if not isinstance(faces, list) or not faces or not candidates:
        return None

    candidates.sort(
        key=lambda face: (
            float(face["center_distance"]),
            -float(face["area_ratio"]),
            -float(face["edge_margin"]),
        )
    )
    selected = candidates[0]
    if float(selected["center_distance"]) > MAX_PRIMARY_FACE_CENTER_DISTANCE:
        return None

    for other in candidates[1:]:
        if (
            float(other["center_distance"]) <= float(selected["center_distance"]) + COMPETING_FACE_CENTER_DISTANCE_DELTA
            and float(other["area_ratio"]) >= float(selected["area_ratio"]) * COMPETING_FACE_AREA_RATIO
        ):
            return None

    return _subject_selection_payload(
        selected,
        candidate_face_count=len(faces),
        reason="center_dominant",
    )


def select_best_available_subject(detection: dict[str, object]) -> dict[str, object] | None:
    primary = select_primary_subject(detection)
    if primary is not None:
        return primary

    faces = detection.get("faces") or []
    candidates = _subject_candidates(detection, enforce_thresholds=False)
    if not isinstance(faces, list) or not faces or not candidates:
        return None

    selected = max(
        candidates,
        key=lambda face: (
            float(face["subject_score"]),
            -float(face["center_distance"]),
            float(face["area_ratio"]),
            float(face["edge_margin"]),
        ),
    )
    return _subject_selection_payload(
        selected,
        candidate_face_count=len(faces),
        reason="best_effort_fallback",
    )


def resolve_face_detector_command(detector_script: Path, image_path: Path) -> list[str]:
    compiled_detector = detector_script.with_suffix("")
    if detector_script.suffix == ".swift" and compiled_detector.is_file():
        return [str(compiled_detector), str(image_path)]
    return ["swift", str(detector_script), str(image_path)]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Chrome-triggered camera-to-anime Seedream requests."
    )
    parser.add_argument("--api-key", default=os.environ.get("ARK_API_KEY", ""))
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--capture-script", type=Path, default=DEFAULT_CAPTURE_SCRIPT)
    parser.add_argument("--latest-image-path", type=Path, default=DEFAULT_CAPTURE_IMAGE_PATH)
    parser.add_argument("--detector-script", type=Path, default=DEFAULT_FACE_DETECTOR)
    parser.add_argument("--portrait-image", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--size", default=DEFAULT_SIZE)
    parser.add_argument("--response-format", default=DEFAULT_RESPONSE_FORMAT)
    parser.add_argument("--style-slug", default="anime")
    parser.add_argument("--style-prompt", default=DEFAULT_STYLE_PROMPT)
    parser.add_argument("--burst-count", type=int, default=DEFAULT_BURST_COUNT)
    parser.add_argument("--burst-interval-seconds", type=float, default=DEFAULT_BURST_INTERVAL_SECONDS)
    parser.add_argument("--allow-multiple-people", action="store_true")
    parser.add_argument("--timestamp")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_landscape_manifest(manifest_path: Path) -> list[dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    resolved = []
    for entry in entries:
        item = dict(entry)
        item["path"] = manifest_path.parent / entry["path"]
        resolved.append(item)
    return resolved


def choose_landscape(entries: list[dict], state_path: Path) -> dict:
    if not entries:
        raise ValueError("landscape manifest is empty")

    state = load_json(state_path)
    last_landscape_id = state.get("last_landscape_id")
    candidates = entries
    if last_landscape_id and len(entries) > 1:
        filtered = [entry for entry in entries if entry["id"] != last_landscape_id]
        if filtered:
            candidates = filtered
    choice = random.choice(candidates)
    write_json(
        state_path,
        {
            **state,
            "selection_mode": "random",
            "last_landscape_id": choice["id"],
        },
    )
    return choice


def encode_image_as_data_uri(image_path: Path) -> str:
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type:
        mime_type = "application/octet-stream"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def build_generation_payload(
    *,
    portrait_path: Path,
    landscape_path: Path,
    model: str,
    size: str,
    response_format: str,
    style_prompt: str,
    pose_instruction: dict[str, str] | None = None,
    allow_multiple_people: bool = False,
) -> dict[str, object]:
    pose_instruction = pose_instruction or choose_pose()
    subject_prompt = (
        "画面中只能出现镜头中央最主要、正对镜头的主人公一人。"
        "生成结果必须是画面当中最主要的唯一主人公，也就是1人，而不是多人。"
        "即使原始照片里有其他人，也不要生成其他人、同伴、路人、分身或额外角色。"
        "严格禁止双人照、多人合照、群像叙事、背景路人和任何额外人物。"
    )
    if allow_multiple_people:
        subject_prompt = (
            "允许保留原始照片中的多人关系，不需要强制只保留一个人物。"
            "如果原始照片中有两个人或多个人，可以自然地一起出现在画面里。"
            "不要无故新增原照片里不存在的额外人物或路人。"
        )
    prompt = (
        f"请将我提供的人物和风景照片合并为一张{style_prompt}，"
        "保留人物真实的五官特征、发型、眼镜和整体气质。"
        "具体要求如下："
        "人物应当是完整全身，四肢和身体轮廓完整可见。"
        "人物比例不要过大，约占画面的四分之一到三分之一，位于画面中下部，背景环境是主要视觉主体。"
        "人物脚下必须是明确可站立的实体地面，例如沙滩、步道、草地、街道、室内地板、岩石或栈桥，脚和地面的接触关系要清楚自然。"
        "除非原始人物照片明确是在游泳、涉水或水上活动，否则不要让人物站在海里、湖里、河里或泳池里，不要让水面切到人物的小腿、膝盖、腰部或胸口。"
        "如果背景是海边、湖边或泳池边，人物也应站在岸边、沙滩、码头、栈桥或其他干燥地面上，水体只作为周围环境，不要淹没人物身体。"
        f"{pose_instruction['prompt']}"
        f"{subject_prompt}"
        "人物与环境真实融合，像旅行途中被拍到的一帧，而不是贴在风景前面的角色立绘。"
        "构图像吉卜力电影截图中的旅行场景，重点呈现天空、山野、树木、草地、街道或建筑等手绘环境层次。"
        "面部结构柔和但真实，表情自然，可以轻微微笑。"
        "风格上强调自然光、空气感、电影截图感、手绘背景层次和温暖通透的色彩。"
        "不要大头照，不要半身头像，不要扁平头像插画，不要Q版，不要过大眼睛，不要贴纸感前景。"
        "避免过分光滑、平涂、廉价二次元立绘感。"
        "尺寸比例：6寸照片，竖版输出。"
    )
    return {
        "model": model,
        "prompt": prompt,
        "image": [
            encode_image_as_data_uri(portrait_path),
            encode_image_as_data_uri(landscape_path),
        ],
        "size": size,
        "response_format": response_format,
    }


def build_output_path(output_dir: Path, *, style_slug: str, timestamp: str) -> Path:
    return output_dir / f"seedream-chrome-camera-{style_slug}-{timestamp}.jpeg"


def build_output_metadata_path(output_path: Path) -> Path:
    return output_path.with_suffix(".metadata.json")


def write_output_metadata(output_path: Path, metadata: dict[str, object]) -> Path:
    metadata_path = build_output_metadata_path(output_path)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata_path


def default_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def prepare_generation_portrait(
    *,
    portrait_path: Path,
    artifact_dir: Path,
    portrait_detection: dict[str, object] | None,
    subject_selection: dict[str, object] | None,
) -> dict[str, object]:
    portrait_path = Path(portrait_path)
    prepared = {
        "portrait_path": str(portrait_path),
        "portrait_source_path": str(portrait_path),
        "portrait_crop": None,
    }

    faces = (portrait_detection or {}).get("faces") or []
    if not portrait_path.is_file() or not isinstance(faces, list) or not subject_selection:
        return prepared

    selected_index = subject_selection.get("selected_face_index")
    if not isinstance(selected_index, int) or selected_index < 0 or selected_index >= len(faces):
        return prepared

    selected_face = faces[selected_index]
    face_width_ratio = float(selected_face.get("width", 0.0))
    face_center_x = float(selected_face.get("center_x", 0.5))
    if face_width_ratio <= 0.0:
        return prepared

    try:
        from PIL import Image
    except ImportError:
        return prepared

    artifact_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(portrait_path) as image:
        width, height = image.size
        if width <= 1 or height <= 1:
            return prepared

        target_width_ratio = min(
            PORTRAIT_FOCUS_MAX_WIDTH_RATIO,
            max(
                PORTRAIT_FOCUS_MIN_WIDTH_RATIO,
                face_width_ratio * PORTRAIT_FOCUS_FACE_WIDTH_MULTIPLIER,
            ),
        )
        crop_width = min(width, max(1, int(round(width * target_width_ratio))))
        if crop_width >= width:
            return prepared

        center_x = face_center_x * width
        left = int(round(center_x - crop_width / 2.0))
        left = max(0, min(left, width - crop_width))
        crop_box = (left, 0, left + crop_width, height)
        focused = image.crop(crop_box)
        focused_path = artifact_dir / f"{portrait_path.stem}-focus{portrait_path.suffix or '.jpg'}"
        focused.save(focused_path)

    prepared["portrait_path"] = str(focused_path)
    prepared["portrait_crop"] = {
        "left": left,
        "top": 0,
        "width": crop_width,
        "height": height,
    }
    return prepared


def capture_camera_image(
    *,
    capture_script: Path,
    latest_image_path: Path,
    runner=subprocess.run,
) -> Path:
    runner([str(capture_script)], check=True, capture_output=True, text=True)
    if not latest_image_path.is_file():
        raise FileNotFoundError(f"missing captured image: {latest_image_path}")
    return latest_image_path


def capture_best_portrait(
    *,
    artifact_dir: Path,
    capture_script: Path,
    latest_image_path: Path,
    detector_script: Path,
    burst_count: int = DEFAULT_BURST_COUNT,
    burst_interval_seconds: float = DEFAULT_BURST_INTERVAL_SECONDS,
    capture_image=capture_camera_image,
    detect_faces_impl=None,
) -> dict[str, object]:
    detector = detect_faces_impl or detect_faces
    artifact_dir.mkdir(parents=True, exist_ok=True)
    if burst_count < 1:
        raise ValueError("burst_count must be >= 1")

    best_candidate: dict[str, object] | None = None

    for index in range(burst_count):
        capture_image(
            capture_script=capture_script,
            latest_image_path=latest_image_path,
        )
        staged_path = artifact_dir / f"capture-{index + 1}.jpg"
        shutil.copy2(latest_image_path, staged_path)
        detection = detector(staged_path, detector_script, runner=subprocess.run)
        subject_selection = select_best_available_subject(detection)
        candidate = {
            "portrait_path": str(staged_path),
            "portrait_detection": detection,
            "subject_selection": subject_selection,
        }
        if subject_selection is not None:
            if best_candidate is None:
                best_candidate = candidate
            elif float(subject_selection.get("subject_score", 0.0)) > float(
                (best_candidate.get("subject_selection") or {}).get("subject_score", 0.0)
            ):
                best_candidate = candidate
        if index < burst_count - 1 and burst_interval_seconds > 0:
            time.sleep(burst_interval_seconds)

    if best_candidate is None:
        if DEFAULT_RECOVERY_PAUSE_SECONDS > 0:
            time.sleep(DEFAULT_RECOVERY_PAUSE_SECONDS)
        capture_image(
            capture_script=capture_script,
            latest_image_path=latest_image_path,
        )
        staged_path = artifact_dir / f"capture-{burst_count + 1}-recovery.jpg"
        shutil.copy2(latest_image_path, staged_path)
        detection = detector(staged_path, detector_script, runner=subprocess.run)
        subject_selection = select_best_available_subject(detection)
        if subject_selection is not None:
            return {
                "portrait_path": str(staged_path),
                "portrait_detection": detection,
                "subject_selection": subject_selection,
            }
        raise ValueError("No primary subject detected in captured photo")
    return best_candidate


def detect_faces(
    image_path: Path,
    detector_script: Path,
    *,
    runner=subprocess.run,
) -> dict[str, object]:
    result = runner(
        resolve_face_detector_command(detector_script, image_path),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def ensure_portrait_detected(
    image_path: Path,
    *,
    detector_script: Path,
    detector=detect_faces,
    runner=subprocess.run,
) -> dict[str, object]:
    payload = detector(image_path, detector_script, runner=runner)
    subject_selection = select_best_available_subject(payload)
    if subject_selection is None:
        raise ValueError("No primary subject detected in captured photo")
    payload = {
        **payload,
        "subject_selection": subject_selection,
    }
    return payload


def validate_generated_output(
    output_path: Path,
    *,
    detector_script: Path,
    allow_multiple_people: bool = False,
    detector=detect_faces,
    runner=subprocess.run,
) -> dict[str, object]:
    detection = detector(output_path, detector_script, runner=runner)
    face_count = int(detection.get("face_count", 0))
    if face_count >= 2 and not allow_multiple_people:
        raise ValueError("Generated image contains multiple detected faces")
    status = "multi_subject" if allow_multiple_people and face_count >= 2 else "single_subject" if face_count == 1 else "detector_no_face"
    return {
        "status": status,
        "face_count": face_count,
        "largest_face_area_ratio": float(detection.get("largest_face_area_ratio", 0.0)),
        "subject_selection": select_best_available_subject(detection) if allow_multiple_people else select_primary_subject(detection),
    }


def generate_image(
    *,
    api_key: str,
    api_url: str,
    payload: dict[str, object],
    timeout: int,
) -> dict[str, object]:
    if not api_key.strip():
        raise ValueError("Provide ARK_API_KEY or pass --api-key before generating images.")
    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Seedream request failed with {exc.code}: {body}") from exc


def download_image(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=DEFAULT_TIMEOUT) as response:
        output_path.write_bytes(response.read())
    return output_path


def generate_from_paths(
    *,
    api_key: str,
    portrait_path: Path,
    landscape_path: Path,
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    response_format: str = DEFAULT_RESPONSE_FORMAT,
    api_url: str = DEFAULT_API_URL,
    timeout: int = DEFAULT_TIMEOUT,
    style_slug: str = "anime",
    style_prompt: str = DEFAULT_STYLE_PROMPT,
    pose_instruction: dict[str, str] | None = None,
    timestamp: str | None = None,
    landscape_id: str | None = None,
    detector_script: Path = DEFAULT_FACE_DETECTOR,
    allow_multiple_people: bool = False,
    generate_image_impl=generate_image,
    download_image_impl=download_image,
    detect_faces_impl=detect_faces,
    validate_generated_output_impl=validate_generated_output,
) -> dict[str, object]:
    timestamp = timestamp or default_timestamp()
    pose_instruction = pose_instruction or choose_pose()
    payload = build_generation_payload(
        portrait_path=portrait_path,
        landscape_path=landscape_path,
        model=model,
        size=size,
        response_format=response_format,
        style_prompt=style_prompt,
        pose_instruction=pose_instruction,
        allow_multiple_people=allow_multiple_people,
    )
    output_path = build_output_path(output_dir, style_slug=style_slug, timestamp=timestamp)
    last_validation_error: Exception | None = None
    total_attempts = max(int(DEFAULT_OUTPUT_VALIDATION_RETRIES), 0) + 1

    for attempt in range(1, total_attempts + 1):
        response = generate_image_impl(
            api_key=api_key,
            api_url=api_url,
            payload=payload,
            timeout=timeout,
        )
        image_url = response["data"][0]["url"]
        download_image_impl(image_url, output_path)
        try:
            output_subject_validation = validate_generated_output_impl(
                output_path,
                detector_script=detector_script,
                allow_multiple_people=allow_multiple_people,
                detector=detect_faces_impl,
            )
            break
        except Exception as exc:
            if not should_retry_generation_after_validation_error(exc) or attempt >= total_attempts:
                raise
            last_validation_error = exc
    else:
        if last_validation_error is not None:
            raise last_validation_error
        raise RuntimeError("generation validation retry loop exited unexpectedly")
    result = {
        "portrait_path": str(portrait_path),
        "output_path": str(output_path),
        "request_summary": {
            "model": payload["model"],
            "size": payload["size"],
            "response_format": payload["response_format"],
            "image_count": len(payload["image"]),
            "prompt": payload["prompt"],
            "pose_instruction": pose_instruction,
            "generation_attempts": attempt,
        },
        "response_model": response.get("model"),
        "response_url": image_url,
        "pose_instruction": pose_instruction,
        "output_subject_validation": output_subject_validation,
    }
    if landscape_id is not None:
        result["landscape"] = {
            "id": landscape_id,
            "path": str(landscape_path),
        }
    return result


def run_pipeline(
    *,
    api_key: str,
    manifest_path: Path,
    output_dir: Path,
    state_path: Path,
    capture_script: Path = DEFAULT_CAPTURE_SCRIPT,
    latest_image_path: Path = DEFAULT_CAPTURE_IMAGE_PATH,
    detector_script: Path = DEFAULT_FACE_DETECTOR,
    model: str = DEFAULT_MODEL,
    size: str = DEFAULT_SIZE,
    response_format: str = DEFAULT_RESPONSE_FORMAT,
    api_url: str = DEFAULT_API_URL,
    timeout: int = DEFAULT_TIMEOUT,
    style_slug: str = "anime",
    style_prompt: str = DEFAULT_STYLE_PROMPT,
    timestamp: str | None = None,
    portrait_image: Path | None = None,
    burst_count: int = DEFAULT_BURST_COUNT,
    burst_interval_seconds: float = DEFAULT_BURST_INTERVAL_SECONDS,
    allow_multiple_people: bool = False,
    capture_image=capture_camera_image,
    detect_faces=detect_faces,
    generate_image=generate_image,
    download_image=download_image,
) -> dict[str, object]:
    timestamp = timestamp or default_timestamp()
    entries = load_landscape_manifest(manifest_path)
    landscape = choose_landscape(entries, state_path)
    portrait_path = portrait_image or capture_image(
        capture_script=capture_script,
        latest_image_path=latest_image_path,
    )
    portrait_detection = ensure_portrait_detected(
        portrait_path,
        detector_script=detector_script,
        detector=detect_faces,
    )
    payload = build_generation_payload(
        portrait_path=portrait_path,
        landscape_path=landscape["path"],
        model=model,
        size=size,
        response_format=response_format,
        style_prompt=style_prompt,
        allow_multiple_people=allow_multiple_people,
    )
    result = generate_from_paths(
        api_key=api_key,
        portrait_path=portrait_path,
        landscape_path=landscape["path"],
        output_dir=output_dir,
        model=model,
        size=size,
        response_format=response_format,
        api_url=api_url,
        timeout=timeout,
        style_slug=style_slug,
        style_prompt=style_prompt,
        timestamp=timestamp,
        landscape_id=landscape["id"],
        detector_script=detector_script,
        allow_multiple_people=allow_multiple_people,
        generate_image_impl=generate_image,
        download_image_impl=download_image,
        detect_faces_impl=detect_faces,
    )
    result["portrait_detection"] = portrait_detection
    return result


def main(
    argv: list[str] | None = None,
    *,
    run_pipeline_impl=run_pipeline,
) -> int:
    args = parse_args(argv)
    if not args.api_key:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "Provide --api-key or set ARK_API_KEY.",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2

    try:
        result = run_pipeline_impl(
            api_key=args.api_key,
            manifest_path=args.manifest,
            output_dir=args.output_dir,
            state_path=args.state_path,
            capture_script=args.capture_script,
            latest_image_path=args.latest_image_path,
            detector_script=args.detector_script,
            portrait_image=args.portrait_image,
            model=args.model,
            size=args.size,
            response_format=args.response_format,
            api_url=args.api_url,
            timeout=args.timeout,
            style_slug=args.style_slug,
            style_prompt=args.style_prompt,
            timestamp=args.timestamp,
            burst_count=args.burst_count,
            burst_interval_seconds=args.burst_interval_seconds,
            allow_multiple_people=args.allow_multiple_people,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
