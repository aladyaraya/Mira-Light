# Mira Light Camera Director Console

This is a lightweight local console for the camera attached to the Mira Light board.
It reuses the existing Digua camera capture path from `Chrome-Camera-Anime/digua_remote_render_pipeline.py`.

## Runtime Shape

```text
browser
  -> mira-light-camera-console/camera_console.py
  -> SSH root@192.168.0.183
  -> ffmpeg -f v4l2 -input_format mjpeg -video_size 1280x720 -i /dev/video0 -frames:v 1
  -> base64 JPEG over SSH stdout
  -> local latest image display
```

The server captures at a fixed interval, defaulting to 10 seconds, and the browser polls the latest saved frame.

## Run

From the repository root:

```bash
./Start-Mira-Light-Camera-Director-Console.command
```

Short alias:

```bash
./Start-Mira-Light-Camera-Console.command
```

Default URL:

```text
http://127.0.0.1:8788/
```

## Configuration

Useful environment variables:

```text
MIRA_CAMERA_CONSOLE_HOST=127.0.0.1
MIRA_CAMERA_CONSOLE_PORT=8788
MIRA_CAMERA_BOARD_HOST=192.168.0.183
MIRA_CAMERA_BOARD_PORT=22
MIRA_CAMERA_BOARD_USER=root
MIRA_CAMERA_BOARD_PASSWORD=<board-password>
MIRA_CAMERA_INTERVAL_SECONDS=10
MIRA_CAMERA_CONSOLE_DATA_DIR=~/Documents/Mira-Light-Camera-Console
DIGUA_CAMERA_DEVICE=/dev/video0
DIGUA_CAMERA_INPUT_FORMAT=mjpeg
DIGUA_CAMERA_VIDEO_SIZE=1280x720
MIRA_CAMERA_V4L2_CTRLS=white_balance_automatic=1,auto_exposure=3,exposure_dynamic_framerate=1,brightness=96,contrast=36,saturation=72,gain=4,gamma=105,backlight_compensation=0
```

`MIRA_CAMERA_V4L2_CTRLS` is optional. When set, the console applies the comma-separated
V4L2 controls on the board immediately before every frame capture. This is the safest
place to tune white balance, brightness, gamma, and exposure-like controls because many
UVC cameras reset controls when the device is reopened.

If `MIRA_CAMERA_BOARD_PASSWORD` is unset, the launcher falls back to `MIRA_SHENZHEN_BOARD_PASSWORD`, and then to `<board-password>`.
