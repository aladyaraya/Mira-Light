# Chrome Camera Anime

Place built-in landscape images in [landscapes](__HOME__/Documents/GitHub/Javis-Hackathon/.worktrees/feat-chrome-camera-anime/tools/chrome_camera_anime/landscapes) and register them in [manifest.json](__HOME__/Documents/GitHub/Javis-Hackathon/.worktrees/feat-chrome-camera-anime/tools/chrome_camera_anime/landscapes/manifest.json).

The current runtime is queue-backed:

- `chrome_watch_daemon.py`: detects Chrome launch edges and enqueues jobs
- `worker_daemon.py`: owns the local queue, keeps camera access single-threaded, and runs generation jobs concurrently
- `manual_insta_capture.py`: one-shot manual trigger that captures from `Insta360 Link 2 Pro`, renders immediately, and can optionally print
- `print_client.py`: submits finished anime images to the existing Xiaomi 1S printer bridge with `4x6.Fullbleed`
- `xiaomi_home_print.py`: pushes finished images to the connected Xiaomi phone, opens Xiaomi Home print preview, and submits the print with keyboard navigation
- `print_status_poller.py`: optionally updates local job status from `lpstat`
- `digua_remote_render_pipeline.py`: captures one frame from the Digua board camera over SSH and renders it through the same Seedream anime path

Job state lives under `~/.openclaw-chrome-camera-anime/jobs/<job_id>/job.json`.

The worktree is currently seeded with one bundled landscape entry:

- `test2-landscape.png`

The runtime behavior is:

- opening Chrome enqueues a job
- the single capture worker serializes access to the webcam
- single capture mode: take one frame, detect face, and proceed immediately on success
- the generation queue sends portrait + landscape to Seedream
- the generated anime image lands in `~/Downloads/chrome-camera-anime/`
- the finished image is immediately submitted either to Xiaomi Home on the connected phone or to the legacy local Xiaomi 1S print bridge, depending on `rokid-watch` config
- the optional poller marks jobs `print_active` or `print_completed` from local `lpstat`

Manual Insta trigger examples:

- capture + render + print once: `python3 ~/.openclaw-chrome-camera-anime/runtime/manual_insta_capture.py`
- capture only: `python3 ~/.openclaw-chrome-camera-anime/runtime/manual_insta_capture.py --capture-only`
- capture + render without printing: `python3 ~/.openclaw-chrome-camera-anime/runtime/manual_insta_capture.py --no-print`

There is also a separate resident expression monitor:

- `expression_monitor.swift`: keeps an `AVCaptureSession` open, samples the latest frame every 5 seconds, and emits local JSON with `expression` and `mood_trend`
- `install_expression_monitor_launchd.py`: installs a separate `launchd` agent under `~/.openclaw-expression-monitor/`

The expression monitor is intentionally separate from the Chrome print pipeline so the two services can evolve independently. If both need the same webcam at the same time, camera arbitration still needs to be added.

## Digua remote camera one-shot render

Use this when the camera source is the Digua board at `192.168.0.183`:

```bash
DIGUA_SSH_PASSWORD=... \
python3 digua_remote_render_pipeline.py \
  --bind-address 192.168.0.164 \
  --capture-dir ~/Downloads/chrome-camera-anime/digua-remote/source \
  --output-dir ~/Downloads/chrome-camera-anime/digua-remote
```

The script captures `/dev/video0` with remote `ffmpeg`, saves the source JPEG locally, then calls the same Seedream single-image anime renderer used by the Rokid flow. It does not submit anything to a printer.
