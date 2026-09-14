#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pipeline


DEFAULT_OUTPUT_DIR = pipeline.DEFAULT_OUTPUT_DIR / "rokid-watch"
DEFAULT_STYLE_SLUG = "rokid-ghibli"
DEFAULT_STYLE_PROMPT = "现代高清的吉卜力动画风格插画"


def build_stylization_payload(
    *,
    image_path: Path,
    model: str,
    size: str,
    response_format: str,
    style_prompt: str,
) -> dict[str, object]:
    prompt = (
        f"请将我提供的照片重绘为一张{style_prompt}。"
        "保留原始照片的主体、构图、光影关系和关键场景元素。"
        "使用细腻、干净、明亮的手绘风格进行重绘，色彩自然通透，氛围温柔，有电影感。"
        "不要改变照片的核心内容，不要额外添加多余人物或主体。"
        "适合6寸照片打印。"
    )
    return {
        "model": model,
        "prompt": prompt,
        "image": [pipeline.encode_image_as_data_uri(image_path)],
        "size": size,
        "response_format": response_format,
    }


def generate_from_image_path(
    *,
    api_key: str,
    image_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    model: str = pipeline.DEFAULT_MODEL,
    size: str = pipeline.DEFAULT_SIZE,
    response_format: str = pipeline.DEFAULT_RESPONSE_FORMAT,
    api_url: str = pipeline.DEFAULT_API_URL,
    timeout: int = pipeline.DEFAULT_TIMEOUT,
    style_slug: str = DEFAULT_STYLE_SLUG,
    style_prompt: str = DEFAULT_STYLE_PROMPT,
    timestamp: str | None = None,
    generate_image_impl=pipeline.generate_image,
    download_image_impl=pipeline.download_image,
) -> dict[str, object]:
    timestamp = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    payload = build_stylization_payload(
        image_path=image_path,
        model=model,
        size=size,
        response_format=response_format,
        style_prompt=style_prompt,
    )
    response = generate_image_impl(
        api_key=api_key,
        api_url=api_url,
        payload=payload,
        timeout=timeout,
    )
    image_url = response["data"][0]["url"]
    output_path = pipeline.build_output_path(output_dir, style_slug=style_slug, timestamp=timestamp)
    download_image_impl(image_url, output_path)
    return {
        "source_image_path": str(image_path),
        "output_path": str(output_path),
        "request_summary": {
            "model": payload["model"],
            "size": payload["size"],
            "response_format": payload["response_format"],
            "image_count": len(payload["image"]),
            "prompt": payload["prompt"],
        },
        "response_model": response.get("model"),
        "response_url": image_url,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a single Rokid photo into a Ghibli-style illustration.")
    parser.add_argument("--api-key", default=os.environ.get("ARK_API_KEY", ""))
    parser.add_argument("--image-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model", default=pipeline.DEFAULT_MODEL)
    parser.add_argument("--size", default=pipeline.DEFAULT_SIZE)
    parser.add_argument("--response-format", default=pipeline.DEFAULT_RESPONSE_FORMAT)
    parser.add_argument("--api-url", default=pipeline.DEFAULT_API_URL)
    parser.add_argument("--timeout", type=int, default=pipeline.DEFAULT_TIMEOUT)
    parser.add_argument("--style-slug", default=DEFAULT_STYLE_SLUG)
    parser.add_argument("--style-prompt", default=DEFAULT_STYLE_PROMPT)
    parser.add_argument("--timestamp")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.api_key:
        print(json.dumps({"ok": False, "error": "Provide --api-key or set ARK_API_KEY."}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    try:
        result = generate_from_image_path(
            api_key=args.api_key,
            image_path=args.image_path,
            output_dir=args.output_dir,
            model=args.model,
            size=args.size,
            response_format=args.response_format,
            api_url=args.api_url,
            timeout=args.timeout,
            style_slug=args.style_slug,
            style_prompt=args.style_prompt,
            timestamp=args.timestamp,
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
