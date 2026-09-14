#!/usr/bin/env bash
# Mira Light 触觉音频桥 —— 双击即起
# 监听 9783 端口，接收板上 touch_dispatcher 发来的 HTTP trigger，播音频

set -u

cd "$(dirname "$0")" || exit 1

# 输出彩色 banner（仅当是终端时）
if [ -t 1 ]; then
    BOLD='\033[1m'; CYAN='\033[36m'; GREEN='\033[32m'; YELLOW='\033[33m'; RESET='\033[0m'
else
    BOLD=''; CYAN=''; GREEN=''; YELLOW=''; RESET=''
fi

printf "${BOLD}${CYAN}Mira Light 触觉音频桥${RESET}\n"
printf "工作目录: %s\n" "$(pwd)"
printf "Python:   %s\n" "$(command -v python3 || echo 'NOT FOUND')"
printf "afplay:   %s\n" "$(command -v afplay || echo 'NOT FOUND')"
printf "\n"

if ! command -v python3 >/dev/null 2>&1; then
    printf "${YELLOW}缺 python3。请先装 Xcode CLI: xcode-select --install${RESET}\n"
    exit 1
fi
if ! command -v afplay >/dev/null 2>&1; then
    printf "${YELLOW}缺 afplay。这个桥仅支持 macOS。${RESET}\n"
    exit 1
fi

# 检查音频文件存在
if [ ! -f "assets/speech/cute_robot_comfort.aiff" ]; then
    printf "${YELLOW}警告: 找不到 assets/speech/cute_robot_comfort.aiff，触摸长按会失败${RESET}\n"
    printf "${YELLOW}你可能需要补回这个文件。当前 assets/ 内容:${RESET}\n"
    ls -la assets/ 2>/dev/null || printf "  (assets/ 目录不存在)\n"
    printf "\n"
fi

printf "${GREEN}启动中...按 Ctrl-C 停止${RESET}\n"
printf "${GREEN}--------------------------------------------${RESET}\n"

# 用 -u 让 print 实时输出，不要缓冲
exec python3 -u audio_bridge_server.py "$@"
