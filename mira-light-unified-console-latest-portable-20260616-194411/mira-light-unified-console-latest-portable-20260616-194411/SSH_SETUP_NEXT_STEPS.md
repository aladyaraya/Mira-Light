# SSH 密钥配置完成 - 下一步操作

## ✅ 已完成

1. ✓ SSH 密钥对已生成
   - 私钥：`C:\Users\guozh\.ssh\id_ed25519_mira`
   - 公钥：`C:\Users\guozh\.ssh\id_ed25519_mira.pub`

2. ✓ 网络连通性已验证
   - 开发板 IP: 192.168.0.183
   - SSH 端口: 22
   - 状态: 可达（延迟 ~86ms）

3. ✓ OpenSSH 客户端可用
   - 位置: `C:\Windows\System32\OpenSSH\ssh.exe`

## ⚠️ 需要手动完成的步骤

SSH 密钥复制需要交互式密码输入，无法完全自动化。请按以下步骤操作：

### 方法 A: 一键命令（最简单）

1. **打开 PowerShell**
2. **复制并执行以下命令**（会提示输入密码）：

```powershell
ssh root@192.168.0.183 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQXnZzh9lgg4vUEeIkhg8mAHx6xtpHXP7zLWlFrRYs9 mira-board' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '配置成功' && wc -l ~/.ssh/authorized_keys"
```

3. **输入开发板密码**（如果 SSH 密钥认证已配置过，则无需密码）
4. 看到 `配置成功` 和行数即表示完成

### 方法 B: 分步执行

```powershell
# 1. 登录开发板
ssh root@192.168.0.183

# 2. 在开发板上执行（复制粘贴这整行）：
mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQXnZzh9lgg4vUEeIkhg8mAHx6xtpHXP7zLWlFrRYs9 mira-board' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '配置成功' && wc -l ~/.ssh/authorized_keys

# 3. 如果看到 "配置成功" 和行数，退出：
exit
```

### 方法 C: 使用批处理文件

双击运行项目目录下的：
```
setup_ssh_key.bat
```

## 🧪 测试配置

配置完成后，测试无密码登录：

```powershell
ssh root@192.168.0.183 "echo 'SSH 密钥认证成功'"
```

如果看到 `SSH 密钥认证成功` 而**没有提示输入密码**，说明配置正确！

## 🔑 你的公钥内容

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQXnZzh9lgg4vUEeIkhg8mAHx6xtpHXP7zLWlFrRYs9 mira-board
```

## 📋 后续步骤

SSH 密钥配置成功后：

1. **重启 Mira Light 控制台**
2. **检查 SSH 自检** - 应该显示 "通过"
3. **测试舵机位置读取** - 应该能成功
4. **如果需要追书功能** - 在 WSL 或 Git Bash 中运行控制台

## ❓ 遇到问题？

### SSH 仍然提示密码？

确认公钥已正确复制到开发板：
```powershell
ssh root@192.168.0.183 "cat ~/.ssh/authorized_keys"
```
应该能看到你的公钥内容。

### 权限错误？

在开发板上检查并修复权限：
```powershell
ssh root@192.168.0.183 "chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
```

### 找不到私钥文件？

控制台默认使用哪个私钥？如果不在默认位置，可以：
1. 重命名密钥为标准名称：
   ```powershell
   Copy-Item "$env:USERPROFILE\.ssh\id_ed25519_mira" "$env:USERPROFILE\.ssh\id_ed25519" -Force
   Copy-Item "$env:USERPROFILE\.ssh\id_ed25519_mira.pub" "$env:USERPROFILE\.ssh\id_ed25519.pub" -Force
   ```
2. 或者在 SSH 命令中指定：
   ```powershell
   ssh -i "$env:USERPROFILE\.ssh\id_ed25519_mira" root@192.168.0.183
   ```

---

**下一步**: 请在 PowerShell 中执行上面的"方法 A"命令，配置 SSH 密钥。
