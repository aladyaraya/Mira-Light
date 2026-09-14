# 完整解决方案

## 当前状态

❌ **网络下载超时** - 无法自动下载 PuTTY
✅ **SSH 密钥已配置** - 无密码登录可用
✅ **排队模式已开启** - Gateway 配置正确

---

## 方案选择

### 方案 A：手动下载 PuTTY（推荐）

#### 步骤 1：下载 plink.exe

**方法 A1：浏览器下载（最简单）**

1. 打开浏览器
2. 访问：https://www.putty.org/
3. 点击 "Download PuTTY"
4. 下载 64-bit Windows installer
5. 运行安装程序，按提示完成

**方法 A2：直接下载 plink.exe（轻量）**

如果浏览器能打开，直接访问：
```
https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe
```

或者备用地址：
```
https://www.chiark.greenend.org.uk/~sgtatham/putty/latest/w64/plink.exe
```

保存到：`C:\Users\guozh\AppData\Local\plink.exe`

#### 步骤 2：添加到 PATH

1. 按 `Win + R`，输入 `sysdm.cpl`
2. 点击 "高级" → "环境变量"
3. 在 "用户变量" 中找到 `Path`
4. 点击 "编辑" → "新建"
5. 添加：`C:\Users\guozh\AppData\Local`
6. 点击 "确定" 保存

#### 步骤 3：验证

打开**新的** PowerShell：
```powershell
plink -V
```

---

### 方案 B：使用 WSL（无需安装 PuTTY）

如果你不想下载 PuTTY，可以直接在 WSL 中运行控制台：

```powershell
# 1. 启动 WSL
wsl

# 2. 进入项目目录
cd /mnt/d/PROJECT/Mira/20260626代码加语音/mira-light-unified-console-latest-portable-20260616-194411

# 3. 启动控制台
python3 mira-light-unified-director-console/shenzhen_console.py
```

**优点：**
- ✅ 无需安装 PuTTY
- ✅ 无需处理 Windows PATH
- ✅ 所有功能正常工作
- ✅ 追书功能可用

---

### 方案 C：临时修复代码（跳过 plink 检查）

如果暂时无法安装 PuTTY 也不想用 WSL，我可以修改代码，让它**强制使用 SSH 密钥**而不检查 plink。

但这需要修改 `digua_remote_render_pipeline.py` 的代码逻辑。

**警告：** 这会修改项目代码，不是长久之计。

---

## 🎯 推荐选择

| 方案 | 难度 | 时间 | 完整性 |
|------|------|------|--------|
| **方案 A** - 手动下载 PuTTY | ⭐ 简单 | 5 分钟 | ✅ 完整 |
| **方案 B** - 使用 WSL | ⭐ 简单 | 1 分钟 | ✅ 完整 |
| **方案 C** - 修改代码 | ⭐⭐⭐ 复杂 | 15 分钟 | ⚠️ 临时 |

### 我的建议

**立即：** 使用方案 B（WSL）来运行控制台
**之后：** 有空时手动下载 PuTTY（方案 A）

---

## 立即可用的命令

### WSL 一键启动

复制以下命令到 PowerShell：

```powershell
wsl bash -c "cd '/mnt/d/PROJECT/Mira/20260626代码加语音/mira-light-unified-console-latest-portable-20260616-194411' && python3 mira-light-unified-director-console/shenzhen_console.py"
```

### 或者分步

```powershell
wsl
cd /mnt/d/PROJECT/Mira/20260626代码加语音/mira-light-unified-console-latest-portable-20260616-194411
python3 mira-light-unified-director-console/shenzhen_console.py
```

---

**你想选择哪个方案？**
