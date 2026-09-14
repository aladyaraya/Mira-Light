# Mira Voice Motion Hardware Acceptance Runbook

Current target:

- Windows action bridge: `http://127.0.0.1:19783`
- Board servo endpoint: `192.168.0.183:9527`
- Expected board-side ACK for raw servo frames: `OK...`
- Expected board-side position probe: `READ` / `READ-POS-ALL` returns four servo positions.

## Acceptance Command

Run this before claiming voice motion works:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Test-Mira-Hardware-Motion-Acceptance.ps1 -Json
```

The command must pass all checks:

1. Direct 9527 ACK probe succeeds.
2. Direct 9527 position-change probe succeeds: the board reports servo positions before and after a short movement, and at least one servo changes by the configured threshold.
3. The tired transcript (`wo hao lei a`) routes through the local Mira soul planner.
4. The resulting `voice_tired` trigger runs `voice_demo_tired`.
5. The bridge waits until the scene completes.
6. `runtime.lastError` is empty.

## Current Failure

As of the latest local validation, the configured board target accepts TCP
connections on `9527` but returns an empty response for raw servo frames:

```text
Mira Light bus-servo endpoint 192.168.0.183:9527 did not acknowledge command ...: empty response
```

SSH port `22` is reachable but immediately closes sessions for tested users, so
the Windows package cannot currently restart or replace the board-side service.

The latest Windows route diagnosis is more specific: `192.168.0.183` is not on
the current WLAN subnet (`192.168.120.245`), and Windows selects the `Meta`
tunnel route through `198.18.0.2`. That means the empty ACK can be a VPN route
intercept rather than a real board bridge response.

If the acceptance result contains:

```json
"risk": "vpn-route-risk"
```

fix the network target before debugging servo code:

1. Refresh the board IP on the current WLAN and update `config/bus_servo_runtime.json` plus `Mira-Light-Voice-Full-Ready/config/bus_servo_runtime.json`.
2. Or add a host route for the real board IP through the LAN/WLAN gateway with an elevated shell.
3. Or configure the VPN/Meta tunnel to bypass the board IP.

## Why This Matters

Previously the runtime treated a TCP connection with an empty response as
`ok: true`. That made the voice chain look successful even when no physical
motion was proven.

The transport now requires an `OK` ACK by default. A scene or voice action that
cannot prove board-side acceptance will fail instead of silently succeeding.

The acceptance script also requires a real position-change proof by default.
The board bridge must support `READ`, `READ-POS`, or `READ-POS-ALL`, backed by
`/home/sunrise/Desktop/four_servo_control.py read-pos-all`. This makes the
acceptance stricter than a successful HTTP call: Mira is only motion-ready when
the board confirms both command acceptance and measurable servo movement.

## Board Recovery Path

When SSH is available again, restart the board bridge with the checked-in bridge:

```powershell
$env:MIRA_SHENZHEN_BOARD_PASSWORD='<board-password>'
python .\Motions_Shenzhen\demo_fixed_protocol_v2\scripts\recover_board_services.py --servo-device /dev/ttyS1
```

The checked-in board bridge defaults to the old verified four-servo center
positions `2048,2150,2048,2130` and exposes the `READ` position command used by
the hardware acceptance script.

Then rerun:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Test-Mira-Hardware-Motion-Acceptance.ps1 -Json
```

Only after this passes should the full realtime voice session be considered
motion-ready.
