# PuTTY 手动安装指南

由于网络下载超时，请按以下步骤手动安装 PuTTY：

## 方法 1：手动下载（推荐）

1. **下载 PuTTY**
   - 访问：https://www.putty.org/
   - 点击 "Download PuTTY"
   - 下载 64-bit Windows 安装程序

2. **运行安装程序**
   - 双击下载的 `.msi` 文件
   - 按提示完成安装
   - 确保勾选 "Add to PATH"

3. **验证安装**
   打开新的 PowerShell 窗口，运行：
   ```powershell
   plink -V
   ```
   应该看到版本信息。

## 方法 2：直接下载 plink.exe（轻量）

如果只需要命令行工具 `plink`：

1. **下载 plink.exe**
   - 访问：https://www.chiark.greenend.org.uk/~sgtatham/putty/latest/w64/plink.exe
   - 或访问：https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe

2. **保存到本地**
   - 保存到：`C:\Users\guozh\AppData\Local\PuTTY\plink.exe`
   - 如果目录不存在，创建它

3. **添加到 PATH**
   在 PowerShell 中运行：
   ```powershell
   $env:Path += ";C:\Users\guozh\AppData\Local\PuTTY"
   [System.Environment]::SetEnvironmentVariable('Path', $env:Path, 'User')
   ```

4. **验证**
   ```powershell
   plink -V
   ```

## 方法 3：使用国内镜像（如果访问国外网站慢）

### 备选下载地址：

1. **GitHub 镜像**
   - https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe
   - Git for Windows 包含 plink

2. **使用 Git for Windows**
   如果已经安装了 Git for Windows：
   ```powershell
   # Git Bash 自带 plink
   & "C:\Program Files\Git\usr\bin\plink.exe" -V
   ```

## 方法 4：使用 Chocolatey（如果已安装）

```powershell
choco install putty
```

如果没有 Chocolatey，可以先安装：https://chocolatey.org/install

## 验证安装

安装完成后，在 PowerShell 中运行：

```powershell
# 测试 plink
plink -V

# 测试 SSH 连接到开发板（会提示输入密码）
plink root@192.168.0.183 "echo 'Plink 测试成功'"
```

## 临时方案（无需安装 PuTTY）

如果暂时无法安装 PuTTY，可以：

1. **使用 WSL**
   ```powershell
   wsl
   ssh root@192.168.0.183
   ```

2. **在 WSL 中运行控制台**
   ```powershell
   wsl
   cd /mnt/d/PROJECT/Mira/20260626代码加语音/mira-light-unified-console-latest-portable-20260616-194411
   python3 mira-light-unified-director-console/shenzhen_console.py
   ```

---

**推荐：** 方法 1 或 2，下载完成后应该就能解决 plink 错误。
