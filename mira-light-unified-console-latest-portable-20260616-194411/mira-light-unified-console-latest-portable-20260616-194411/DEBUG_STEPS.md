# 调试步骤

## 已添加调试日志

我已在 `digua_remote_render_pipeline.py` 的 `run_ssh_capture()` 函数中添加了调试日志，现在会输出：

```
[DEBUG run_ssh_capture] password='...', type=..., bool=...
```

## 重启控制台并查看调试信息

### 步骤 1：启动控制台

在 PowerShell 中运行：

```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"
python mira-light-unified-director-console/shenzhen_console.py
```

### 步骤 2：触发摄像头抓取

在浏览器中打开控制台，点击"抓取"按钮或等待自动刷新。

### 步骤 3：查看终端输出

在 PowerShell 终端中，你应该看到类似：

```
[DEBUG run_ssh_capture] password='', type=str, bool=False
```

或

```
[DEBUG run_ssh_capture] password='somepassword', type=str, bool=True
```

### 步骤 4：告诉我输出

**请复制 `[DEBUG ...]` 那行并告诉我！**

---

## 预期结果

如果配置正确，应该看到：

```
[DEBUG run_ssh_capture] password='', type=str, bool=False
```

这意味着 password 为空，代码应该走 SSH 而非 plink 路径。

如果看到其他内容（比如 password 不为空），说明有地方设置了密码。

---

## 备用测试脚本

如果不想重启控制台，可以运行独立测试：

```powershell
cd "mira-light-unified-console-latest-portable-20260616-194411"
python test_password_debug.py
```

这个脚本会直接调用 `run_ssh_capture()` 并显示调试信息。

---

**下一步：** 请重启控制台，触发摄像头抓取，然后告诉我终端中的 `[DEBUG ...]` 输出。
