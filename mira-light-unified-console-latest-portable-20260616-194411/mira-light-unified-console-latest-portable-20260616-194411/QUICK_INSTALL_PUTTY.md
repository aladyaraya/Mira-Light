# PuTTY / Plink 安装 - 快速指南

## ⚡ 最快的安装方法

### 方法 1：运行自动安装脚本（推荐）

双击运行项目目录下的：
```
install_plink.bat
```

等待下载和安装完成，然后重新打开 PowerShell。

---

### 方法 2：手动下载（如果方法 1 失败）

#### 步骤 1：下载 plink.exe

**点击链接下载：**
- https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe

或者：
- https://www.chiark.greenend.org.uk/~sgtatham/putty/latest/w64/plink.exe

#### 步骤 2：保存文件

将下载的 `plink.exe` 保存到：
```
C:\Users\guozh\AppData\Local\PuTTY\plink.exe
```

如果目录不存在，手动创建文件夹 `C:\Users\guozh\AppData\Local\PuTTY\`

#### 步骤 3：添加到 PATH

1. 按 `Win + R`，输入 `sysdm.cpl`，回车
2. 点击 "高级" → "环境变量"
3. 在 "用户变量" 中找到 `Path`，点击 "编辑"
4. 点击 "新建"
5. 添加路径：`C:\Users\guozh\AppData\Local\PuTTY`
6. 点击 "确定" 保存所有窗口

#### 步骤 4：验证

打开**新的** PowerShell 窗口，运行：
```powershell
plink -V
```

应该看到类似输出：
```
plink: Release 0.78
```

---

### 方法 3：下载完整 PuTTY 安装包

如果上面的方法都失败：

1. 访问：https://www.putty.org/
2. 点击 "Download PuTTY"
3. 下载 64-bit Windows 安装程序（.msi）
4. 运行安装程序，按提示完成安装
5. 重启 PowerShell

---

## ✅ 验证安装

安装完成后，在 PowerShell 中运行：

```powershell
# 查看版本
plink -V

# 测试连接到开发板（会提示输入密码）
plink root@192.168.0.183 "echo 'PuTTY 测试成功'"
```

---

## 🎯 安装后

重新启动 Mira Light 控制台，**plink 错误应该消失**！

---

**推荐顺序：**
1. 先试 `install_plink.bat`（双击运行）
2. 如果失败，使用方法 2 手动下载
3. 如果还失败，使用方法 3 下载完整安装包
