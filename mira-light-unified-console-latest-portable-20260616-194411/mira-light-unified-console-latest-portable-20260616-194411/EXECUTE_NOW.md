# SSH 公钥配置 - 立即执行

## 请复制以下命令到 PowerShell 执行：

```powershell
ssh root@192.168.0.183 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOQXnZzh9lgg4vUEeIkhg8mAHx6xtpHXP7zLWlFrRYs9 mira-board' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '✅ 配置成功' && wc -l ~/.ssh/authorized_keys"
```

## 执行步骤：

1. **打开 PowerShell**
2. **粘贴上面的命令并按回车**
3. **输入开发板密码**（输入时不显示字符，这是正常的）
4. **按回车**

## 成功标志：

看到以下输出表示配置成功：
```
✅ 配置成功
      1 ~/.ssh/authorized_keys
```

## 如果失败：

可能是以下原因：
- 密码错误
- 网络问题
- SSH 服务未启动

**请告诉我执行结果**，我会帮你进一步诊断！
