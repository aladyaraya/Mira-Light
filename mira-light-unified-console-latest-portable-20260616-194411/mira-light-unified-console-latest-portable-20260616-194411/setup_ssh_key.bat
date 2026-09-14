@echo off
chcp 65001 >nul
echo ========================================
echo   Mira Light SSH 密钥配置
echo ========================================
echo.
echo 步骤 1: 显示你的公钥
echo ----------------------------------------
type %USERPROFILE%\.ssh\id_ed25519_mira.pub
echo.
echo ========================================
echo  手动配置步骤
echo ========================================
echo.
echo 方法 A - 自动配置（推荐）:
echo.
echo 1. 运行以下命令登录开发板:
echo    ssh root@192.168.0.183
echo.
echo 2. 登录后，执行以下命令:
echo    mkdir -p ~/.ssh
echo    chmod 700 ~/.ssh
echo    echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQXnZzh9lgg4vUEeIkhg8mAHx6xtpHXP7zLWlFrRYs9 mira-board" ^>^> ~/.ssh/authorized_keys
echo    chmod 600 ~/.ssh/authorized_keys
echo    exit
echo.
echo 方法 B - 使用 PowerShell 一键配置:
echo.
echo 运行以下 PowerShell 命令（会提示输入密码）:
echo.
echo    $pubKey = Get-Content "$env:USERPROFILE\.ssh\id_ed25519_mira.pub" -Raw
echo    ssh root@192.168.0.183 "mkdir -p ~/.ssh ^&amp;&amp; chmod 700 ~/.ssh ^&amp;&amp; echo '$pubKey' ^>^> ~/.ssh/authorized_keys ^&amp;&amp; chmod 600 ~/.ssh/authorized_keys"
echo.
echo ========================================
echo.
pause
