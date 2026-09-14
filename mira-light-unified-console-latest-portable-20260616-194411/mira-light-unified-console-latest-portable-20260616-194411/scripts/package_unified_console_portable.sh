#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="${1:-$(date +%Y%m%d-%H%M%S)}"
DIST_DIR="$ROOT_DIR/dist"
BUNDLE_NAME="mira-light-unified-console-latest-portable-$STAMP"
BUNDLE_DIR="$DIST_DIR/$BUNDLE_NAME"
ENV_EXAMPLE="$ROOT_DIR/portable/unified-console.env.example"
SOURCE_PRIVATE_ENV="$ROOT_DIR/portable/unified-console.env"
BUNDLE_PRIVATE_ENV="$BUNDLE_DIR/portable/unified-console.env"
BUNDLE_GUIDE="$BUNDLE_DIR/PACKAGE_GUIDE.md"
DIST_GUIDE="$DIST_DIR/$BUNDLE_NAME-README.md"

RSYNC_EXCLUDES=(
  --exclude ".git/"
  --exclude ".omx/"
  --exclude ".venv/"
  --exclude "__pycache__/"
  --exclude "*.pyc"
  --exclude ".DS_Store"
  --exclude ".runtime/"
  --exclude "outputs/"
  --exclude "*.zip"
  --exclude "*.tar.gz"
)

ITEMS=(
  "README.md"
  "NEW_MAC_SETUP_README.md"
  "requirements.txt"
  "portable"
  "assets"
  "config"
  "docs"
  "fixtures"
  "image"
  "mira-light-unified-director-console"
  "mira-light-unified-director-console-keyboard"
  "mira-light-unified-director-console-stable-31"
  "mira-light-shenzhen-console"
  "mira-light-camera-console"
  "mira-light-director-console"
  "camera-render-director-console"
  "Chrome-Camera-Anime"
  "Motions"
  "Motions_Shenzhen"
  "Mira-Light-Voice-Cloud-Ready"
  "Mira-Light-Voice-Full-Ready"
  "board-camera-streaming"
  "scripts"
  "tests"
  "tools"
  "web"
)

copy_item() {
  local item="$1"
  local src="$ROOT_DIR/$item"
  local parent
  if [ ! -e "$src" ]; then
    echo "WARN: missing $item"
    return 0
  fi
  parent="$(dirname "$item")"
  mkdir -p "$BUNDLE_DIR/$parent"
  rsync -a "${RSYNC_EXCLUDES[@]}" "$src" "$BUNDLE_DIR/$parent/"
}

shell_quote() {
  printf "%q" "$1"
}

append_export() {
  local name="$1"
  local value="$2"
  [ -n "$value" ] || return 0
  printf '\nexport %s=%s\n' "$name" "$(shell_quote "$value")" >> "$BUNDLE_PRIVATE_ENV"
}

env_file_value() {
  local name="$1"
  if [ ! -f "$BUNDLE_PRIVATE_ENV" ]; then
    return 0
  fi
  (
    set -a
    # shellcheck disable=SC1090
    . "$BUNDLE_PRIVATE_ENV" >/dev/null 2>&1 || true
    set +a
    eval "printf '%s' \"\${$name:-}\""
  )
}

keychain_secret() {
  local service="$1"
  if command -v security >/dev/null 2>&1; then
    security find-generic-password -s "$service" -w 2>/dev/null || true
  fi
}

echo "== Building Mira Light latest portable package =="
echo "Root:   $ROOT_DIR"
echo "Bundle: $BUNDLE_DIR"

rm -rf "$BUNDLE_DIR"
mkdir -p "$BUNDLE_DIR"

for item in "${ITEMS[@]}"; do
  copy_item "$item"
done

for command_file in "$ROOT_DIR"/*.command; do
  [ -e "$command_file" ] || continue
  copy_item "$(basename "$command_file")"
done

mkdir -p "$BUNDLE_DIR/portable"
if [ -f "$SOURCE_PRIVATE_ENV" ]; then
  cp "$SOURCE_PRIVATE_ENV" "$BUNDLE_PRIVATE_ENV"
else
  cp "$ENV_EXAMPLE" "$BUNDLE_PRIVATE_ENV"
fi
chmod 600 "$BUNDLE_PRIVATE_ENV"

ark_value="$(env_file_value ARK_API_KEY)"
if [ -z "$ark_value" ]; then
  ark_value="${ARK_API_KEY:-}"
fi
if [ -z "$ark_value" ]; then
  ark_value="$(keychain_secret mira-light-ark-api-key)"
fi
if [ -n "$ark_value" ]; then
  append_export "ARK_API_KEY" "$ark_value"
  echo "Private env: ARK_API_KEY included."
else
  echo "Private env: ARK_API_KEY not found; anime rendering will need key setup on the new Mac."
fi

if [ -n "${OPENCLAW_PRINTER_BRIDGE_TOKEN:-}" ]; then
  append_export "OPENCLAW_PRINTER_BRIDGE_TOKEN" "$OPENCLAW_PRINTER_BRIDGE_TOKEN"
  echo "Private env: printer bridge token included from current shell."
fi

cat > "$BUNDLE_DIR/START_HERE_8790.command" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
exec "$ROOT_DIR/Start-Mira-Light-Unified-Director-Console.command"
SH

cat > "$BUNDLE_DIR/START_HERE_8791_KEYBOARD.command" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
exec "$ROOT_DIR/Start-Mira-Light-Unified-Director-Console-Keyboard.command"
SH

cat > "$BUNDLE_DIR/START_HERE.command" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
exec "$ROOT_DIR/Start-Mira-Light-Latest-Console.command"
SH

cat > "$BUNDLE_DIR/README_START_HERE.md" <<'MD'
# Mira Light 最新控制台启动说明

推荐流程：

1. 首次到新电脑：双击 `portable/setup_new_mac.sh`
2. 日常启动：双击 `START_HERE.command`
3. 最新推荐控制台：`http://127.0.0.1:8791/`
4. 兼容旧流程控制台：`http://127.0.0.1:8790/`
5. 同一 Wi-Fi 下的 iPad 可打开：`http://<Mac 局域网 IP>:8791/`

入口文件：

- `START_HERE.command`：最新推荐入口，启动 8791 键盘增强版统一控制台
- `START_HERE_8791_KEYBOARD.command`：直接启动 8791 键盘增强版
- `START_HERE_8790.command`：兼容旧流程，启动经典 8790 控制台

这个包已经包含：

- 8791 最新键盘增强版统一控制台
- 8790 兼容版统一控制台
- 8777 Celebration 页面
- 摸摸语音桥
- 相机 / anime / 动作脚本 / 语音包 / 文档 / 测试 / 工具脚本

这个包不会包含：

- `.git`
- `.omx`
- 顶层 `tmp`
- 顶层 `runtime`
- `.venv`
- `dist`

详细说明见 `PACKAGE_GUIDE.md` 和 `docs/unified-console-portable/`。

注意：`portable/unified-console.env` 含私有开发配置，不要公开传播。
MD

cat > "$BUNDLE_GUIDE" <<'MD'
# Mira Light 最新便携控制台说明

## 这是什么

这是当前整理后的最新版 Mira Light 可分发运行包。解压后，在另一台 Mac 上完成一次初始化，就可以直接使用。

推荐入口：

- `START_HERE.command`
- `Start-Mira-Light-Latest-Console.command`
- `http://127.0.0.1:8791/`

兼容入口：

- `START_HERE_8790.command`
- `Start-Mira-Light-Unified-Director-Console.command`
- `http://127.0.0.1:8790/`

## 这版已经包含的能力

- 8791 键盘增强版统一控制台
- 长按连续舵机微调
- 舵机逐帧 Record / Save / Clear
- 本地轨迹录制 / 文件回放面板
- 默认开启摸摸系统
- 默认开启灯光 / 头部命令
- 通过 `MIRA_REMOTE_DESKTOP_DIR` 适配不同板端桌面路径

## 在新 Mac 上如何使用

1. 如果 macOS 拦截，先去隔离：

```bash
xattr -dr com.apple.quarantine /path/to/mira-light-unified-console-latest-portable-*
```

2. 解压整个 zip
3. 双击 `portable/setup_new_mac.sh`
4. 等待它完成 Homebrew 依赖和 Python 依赖安装
5. 双击 `START_HERE.command`

## 包内关键默认配置

包里自带可直接用的 `portable/unified-console.env` 私有配置。

关键默认值：

- 板子地址：`192.168.0.183`
- 摸摸语音桥端口：`9783`
- 最新控制台端口：`8791`
- Celebration 页面端口：`8777`
- 板端桌面目录：`/home/sunrise/Desktop`

## 分发和使用注意事项

- 真机动作是否成功，仍然取决于板子 SSH 和板端脚本是否可达
- 日常推荐使用 8791 页面
- 8790 仍保留在包里，用于兼容旧流程
- `portable/unified-console.env` 含私有配置，分发时请只在可信环境内使用
MD

chmod +x \
  "$BUNDLE_DIR/START_HERE.command" \
  "$BUNDLE_DIR/START_HERE_8790.command" \
  "$BUNDLE_DIR/START_HERE_8791_KEYBOARD.command" \
  "$BUNDLE_DIR/Start-Mira-Light-Latest-Console.command" \
  "$BUNDLE_DIR/Start-Mira-Light-Unified-Director-Console.command" \
  "$BUNDLE_DIR/Start-Mira-Light-Unified-Director-Console-Keyboard.command" \
  "$BUNDLE_DIR/Build-Mira-Light-8790-Portable-Package.command" \
  "$BUNDLE_DIR/Build-Mira-Light-Latest-Portable-Package.command" \
  "$BUNDLE_DIR/portable/setup_new_mac.sh" \
  "$BUNDLE_DIR/portable/check_new_mac_prereqs.sh" \
  "$BUNDLE_DIR/scripts/package_unified_console_portable.sh" || true

(
  cd "$BUNDLE_DIR"
  find . -type f -not -path "./MANIFEST.sha256" -print0 \
    | sort -z \
    | xargs -0 shasum -a 256 \
    > MANIFEST.sha256
)

(
  cd "$DIST_DIR"
  rm -f "$BUNDLE_NAME.zip"
  /usr/bin/zip -qr "$BUNDLE_NAME.zip" "$BUNDLE_NAME"
)

cp "$BUNDLE_GUIDE" "$DIST_GUIDE"

echo
du -sh "$BUNDLE_DIR" "$DIST_DIR/$BUNDLE_NAME.zip"
echo "ZIP: $DIST_DIR/$BUNDLE_NAME.zip"
echo "GUIDE: $DIST_GUIDE"
