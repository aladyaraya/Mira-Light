# Mira Light Anime Chain Analysis

Date: 2026-05-25

This note records the repo reading and live verification performed for the Mira Light anime photo/render/print chain.

## Repository Context

This repository is not a single application. It is a working bundle for Mira / Mira Light demos and runtime integration. The main areas are:

- Shenzhen demo console for fixed motion scenes.
- Unified director console for motion, board camera, touch controls, and show state.
- Chrome Camera Anime runtime for camera capture, Seedream rendering, and printing.
- Local bridges for Mira Light control and printer control.
- Vision and tabletop follow scripts.
- Voice runtime packs and OpenClaw-related integration.

The most relevant files for the anime chain are:

- `Start-Camera-Render-Console.command`
- `camera-render-director-console/scripts/console_server.py`
- `tools/camera_render_bridge/bridge_server.py`
- `Chrome-Camera-Anime/manual_insta_capture.py`
- `Chrome-Camera-Anime/digua_remote_render_pipeline.py`
- `Chrome-Camera-Anime/rokid_render_pipeline.py`
- `Chrome-Camera-Anime/pipeline.py`
- `Chrome-Camera-Anime/print_client.py`
- `Motions_Shenzhen/demo_fixed_protocol_v2/scripts/09_wake_photo_sleep_demo.py`
- `mira-light-shenzhen-console/scene_registry.json`

## Two Anime Paths

There are two related but different anime paths.

### 1. Default Chrome Camera Anime Console

The default one-click console starts from:

```bash
./Start-Camera-Render-Console.command
```

Startup sequence:

```text
Start-Camera-Render-Console.command
-> tools/printer_bridge/start_bridge.sh
-> tools/camera_render_bridge/bridge_server.py
-> camera-render-director-console/scripts/console_server.py
-> http://127.0.0.1:8795/
```

The browser button "拍照 + 渲染 + 打印" calls:

```text
POST /api/capture-render
-> POST /v1/camera-render/capture-render
-> Chrome-Camera-Anime/manual_insta_capture.py
```

This default path uses the Mac camera, not the Mira Light board camera:

```text
Mac camera / imagesnap
-> manual_insta_capture.py
-> pipeline.py
-> detect_faces.swift
-> Seedream API
-> print_client.py
-> Printer Bridge / CUPS
```

### 2. Mira Light Board Camera Path

The board-camera path is implemented by:

```text
Chrome-Camera-Anime/digua_remote_render_pipeline.py
```

Default board camera settings:

```text
host: 192.168.0.183
user: root
port: 22
device: /dev/video0
input format: mjpeg
video size: 1280x720
```

The flow is:

```text
local Python
-> ssh root@192.168.0.183
-> remote ffmpeg captures one frame from /dev/video0
-> remote JPEG is base64-encoded
-> local script decodes and saves the JPEG
-> rokid_render_pipeline.py sends it to Seedream
-> generated image is downloaded locally
```

The remote capture command is effectively:

```bash
ffmpeg \
  -hide_banner \
  -loglevel error \
  -f v4l2 \
  -input_format mjpeg \
  -video_size 1280x720 \
  -i /dev/video0 \
  -frames:v 1 \
  -y /tmp/digua-camera-capture.jpg
```

## Full Wake Photo Sleep Chain

The complete stage flow is:

```text
Motions_Shenzhen/demo_fixed_protocol_v2/scripts/09_wake_photo_sleep_demo.py
```

It does more than a raw anime render:

```text
1. SSH to the Mira Light board.
2. Drive servos and LEDs from sleep pose into a wake/photo pose.
3. Capture a real board-camera photo from /dev/video0.
4. Save the source photo locally.
5. Spawn a background render/print worker.
6. Render the source photo with Seedream through rokid_render_pipeline.py.
7. Optionally submit the generated image to CUPS with lp.
8. Return Mira Light to sleep while rendering/printing continues.
```

This scene is registered in:

```text
mira-light-shenzhen-console/scene_registry.json
```

Scene id:

```text
09_wake_photo_sleep
```

Default print settings in that scene:

```text
printer queue: Mi_Wireless_Photo_Printer_9135_IP
media: na_index-4x6_4x6in
```

The worker uses direct CUPS submission:

```bash
lp \
  -d Mi_Wireless_Photo_Printer_9135_IP \
  -o media=na_index-4x6_4x6in \
  -o print-scaling=fill \
  -o print-quality=5 \
  -o fit-to-page=false \
  <generated-image>
```

Use `--no-print` to render without submitting to the printer.

## Seedream Rendering Details

The common Seedream request helper is in:

```text
Chrome-Camera-Anime/pipeline.py
```

Current defaults:

```text
model: doubao-seedream-5-0-260128
api URL: https://ark.cn-beijing.volces.com/api/v3/images/generations
size: 1920x1920
response format: url
env key: ARK_API_KEY
```

The board-camera anime path calls:

```text
Chrome-Camera-Anime/rokid_render_pipeline.py
```

Prompt summary:

```text
Redraw the input photo as a modern high-definition Ghibli/anime-style illustration.
Preserve the original subject, composition, lighting relationship, and key scene elements.
Keep the image clean, bright, cinematic, and suitable for 6-inch photo printing.
```

## Printer Accessibility Check

The printer was checked before running the no-print anime verification.

CUPS visible queues included:

```text
Mi_Wireless_Photo_Printer_1S__2196_
Mi_Wireless_Photo_Printer_1S__6528_
Mi_Wireless_Photo_Printer_9135_
Mi_Wireless_Photo_Printer_9135_IP
Mi_Wireless_Photo_Printer_MacBook_Pro_8_
```

System default destination:

```text
Mi_Wireless_Photo_Printer_9135_
```

Available idle queues:

```text
Mi_Wireless_Photo_Printer_9135_
Mi_Wireless_Photo_Printer_9135_IP
```

Printer Bridge:

```text
http://127.0.0.1:9771/health -> 200 OK
service: openclaw-printer-bridge
queue_name: Mi_Wireless_Photo_Printer_9135_
```

Protected printer status check with the local token succeeded:

```text
active_jobs: []
supported_media: 3x3, 3x3.Fullbleed, 4x6, 4x6.Fullbleed
```

No stuck or incomplete print jobs were present.

## Actual No-Print Anime Verification

The board-camera anime chain was executed successfully without printing.

Command shape:

```bash
DIGUA_SSH_PASSWORD="${DIGUA_SSH_PASSWORD:-}" \
python3 Chrome-Camera-Anime/digua_remote_render_pipeline.py \
  --host "${MIRA_SHENZHEN_BOARD_HOST:-192.168.0.183}" \
  --user "${MIRA_SHENZHEN_BOARD_USER:-root}" \
  --remote-device "${DIGUA_CAMERA_DEVICE:-/dev/video0}" \
  --input-format "${DIGUA_CAMERA_INPUT_FORMAT:-mjpeg}" \
  --video-size "${DIGUA_CAMERA_VIDEO_SIZE:-1280x720}" \
  --capture-dir "$PWD/tmp/anime-chain-check-20260525-083928/source" \
  --output-dir "$PWD/tmp/anime-chain-check-20260525-083928/output" \
  --style-slug "anime-chain-check"
```

Important boundary:

```text
No print command was run.
No Printer Bridge print endpoint was called.
No lp job was submitted.
```

Result:

```text
ok: true
capture host: 192.168.0.183
capture device: /dev/video0
Seedream model: doubao-seedream-5-0-260128
```

Source image:

```text
tmp/anime-chain-check-20260525-083928/source/digua-camera-20260525-083928.jpg
```

Generated anime image:

```text
tmp/anime-chain-check-20260525-083928/output/seedream-chrome-camera-anime-chain-check-20260525-083928.jpeg
```

File validation:

```text
source: 1280x720 JPEG, RGB, about 56 KB
output: 1920x1920 JPEG, RGB, about 338 KB
```

Print queue validation after the run:

```text
lpstat -o: no output
lpstat -W not-completed -o: no output
```

Conclusion:

```text
The Mira Light board-camera anime render chain is executable.
It can capture from /dev/video0 over SSH and generate a Seedream anime image.
The no-print test did not submit any print jobs.
```

## Useful Commands

Only test board camera capture:

```bash
cd Chrome-Camera-Anime

DIGUA_SSH_PASSWORD="" \
python3 digua_remote_render_pipeline.py \
  --host 192.168.0.183 \
  --user root \
  --remote-device /dev/video0 \
  --capture-only \
  --capture-dir "$HOME/Downloads/chrome-camera-anime/digua-remote/source"
```

Board camera capture plus anime render, no printing:

```bash
cd Chrome-Camera-Anime

DIGUA_SSH_PASSWORD="" \
ARK_API_KEY="..." \
python3 digua_remote_render_pipeline.py \
  --host 192.168.0.183 \
  --user root \
  --remote-device /dev/video0 \
  --input-format mjpeg \
  --video-size 1280x720 \
  --output-dir "$HOME/Downloads/chrome-camera-anime/digua-remote"
```

Full wake-photo-sleep sequence without printing:

```bash
ARK_API_KEY="..." \
DIGUA_SSH_PASSWORD="" \
python3 Motions_Shenzhen/demo_fixed_protocol_v2/scripts/09_wake_photo_sleep_demo.py \
  --host 192.168.0.183 \
  --user root \
  --remote-device /dev/video0 \
  --no-print
```

Full wake-photo-sleep sequence with printing enabled:

```bash
ARK_API_KEY="..." \
DIGUA_SSH_PASSWORD="" \
python3 Motions_Shenzhen/demo_fixed_protocol_v2/scripts/09_wake_photo_sleep_demo.py \
  --host 192.168.0.183 \
  --user root \
  --remote-device /dev/video0 \
  --printer-queue Mi_Wireless_Photo_Printer_9135_IP \
  --print-media na_index-4x6_4x6in
```

Check printer status:

```bash
lpstat -e
lpstat -d
lpstat -p
lpstat -o
```

Check Printer Bridge:

```bash
curl http://127.0.0.1:9771/health
```

## Operational Notes

- `Start-Camera-Render-Console.command` is useful for the Mac-camera browser console, but it is not the board-camera anime path by default.
- Use `digua_remote_render_pipeline.py` when the desired source image is the Mira Light board camera.
- Use `09_wake_photo_sleep_demo.py` when the desired behavior includes physical motion, photo pose, capture, render, optional print, and return-to-sleep choreography.
- `ARK_API_KEY` is required for real Seedream rendering.
- Password SSH uses `expect`; key-based SSH can avoid `DIGUA_SSH_PASSWORD`.
- The board must have `ffmpeg` available and `/dev/video0` readable.
- Use `--no-print` for rehearsal and validation when print output is not wanted.
