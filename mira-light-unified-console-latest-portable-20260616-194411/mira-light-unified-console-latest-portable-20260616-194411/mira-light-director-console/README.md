# Mira Light Director Console Bundle

This folder is a self-contained copy of the Mira-Light web director console layer.
It preserves the console UI, scene launch manifests, and local console proxy used by
the original Mira-Light booth demo.

## Contents

- `web/`: Director Console, Silent Console, shared frontend logic, styles, and scene showcase pages.
- `scripts/console_server.py`: local static server and `/api/*` proxy for the Mira Light bridge.
- `scripts/mira_light_signal_delivery.py`: shared scene-launch payload helpers used by `Motions/*/scene_script.py`.
- `scripts/scenes.py`: reference scene metadata and choreography definitions from the original runtime.
- `Motions/`: per-scene director-console manifests and test notes.
- `config/mira_light_signal_delivery.schema.json`: signal-delivery schema referenced by scene metadata.
- `docs/mira-light-director-console-spec.md`: design explanation for the director-console layout.

## Runtime Shape

The console is intentionally a thin local control layer:

```text
browser
  -> scripts/console_server.py
  -> Mira Light bridge, default http://127.0.0.1:9783
  -> Mira Light runtime / mock lamp / live lamp
```

The copied console can serve the UI immediately, but live scene/status data still
comes from a running Mira Light bridge that exposes `/v1/mira-light/*`.

## Run Locally

From this folder:

```bash
python3 scripts/console_server.py --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

Useful environment variables:

```text
MIRA_LIGHT_CONSOLE_BRIDGE_URL=http://127.0.0.1:9783
MIRA_LIGHT_BRIDGE_TOKEN=<optional bridge token>
MIRA_LIGHT_VISION_EVENT_PATH=<optional latest vision JSON>
MIRA_LIGHT_VISION_BRIDGE_STATE_PATH=<optional vision bridge state JSON>
MIRA_LIGHT_VISION_OPERATOR_STATE_PATH=<optional operator lock JSON>
```

## Notes

- `web/index.html` is the full Director Console.
- `web/silent.html` is the Silent Console variant.
- The lamp target shown in the UI is fixed to `tcp://192.168.31.10:9527`, matching the original booth setup.
- `Motions/*/scene_script.py` imports `scripts/mira_light_signal_delivery.py`, so those files are copied together.
