# 舵机超时问题 - 完整解决方案

## 🔍 错误原因

```
TimeoutError: timed out waiting for servo response header; observed bytes: <none>
```

**舵机完全没有响应**。最常见的原因是：

1. 🔴 **舵机电源关闭**（90% 可能性）
2. 🟡 **串口连接问题**（5% 可能性）
3. 🟢 **舵机故障**（5% 可能性）

---

## 🚀 立即排查（按顺序）

### **在开发板上执行以下命令**

#### 1. 检查串口设备

```bash
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

**预期看到**：
```
/dev/ttyUSB0
```

如果没有任何输出 → USB 转串口未连接

---

#### 2. 检查舵机电源

```bash
# 如果舵机电源由 GPIO 控制
ls /sys/class/gpio 2>/dev/null
cat /sys/class/gpio/gpio*/value 2>/dev/null
```

**查找电源引脚**：
- 舵机电源模块上的 **LED 指示灯**是否亮起？
- 用万用表测量舵机电源电压（应该 ~12V）

---

#### 3. 快速测试舵机响应

```bash
cd /home/sunrise/Desktop

# 测试舵机 ping
python3 four_servo_control.py ping-all
```

**预期输出**：
```
Pinging servo 0: OK (position: 2048)
Pinging servo 1: OK (position: 1880)
...
```

如果全部超时 → 舵机电源或连接问题

---

#### 4. 运行诊断脚本

```bash
# 上传诊断脚本到开发板
# 然后运行：
cd /home/sunrise/Desktop
python3 diagnose_servo.py
```

---

## 🔧 解决方案（按优先级）

### **方案 1：检查并开启舵机电源（最可能）**

#### A. 如果是 GPIO 控制的电源

找到电源控制脚本（通常在 `send_uart3_led_cmd.py` 或类似）：

```bash
# 查看是否有电源控制脚本
ls /home/sunrise/Desktop/*power* /home/sunrise/Desktop/*enable* 2>/dev/null

# 或者直接检查 GPIO
find /sys/class/gpio -name "value" -exec sh -c 'echo "GPIO $1: $(cat $1)"' _ {} \;
```

**开启舵机电源：**
```bash
# 假设舵机电源在 GPIO 17
echo 1 | sudo tee /sys/class/gpio/gpio17/value
# 或
gpio set 17
```

#### B. 如果是独立电源开关

- 检查舵机电源模块的开关是否打开
- 检查电源适配器是否插好
- 检查电源指示灯是否亮起

---

### **方案 2：检查 UART 连接**

```bash
# 检查串口设备是否存在
ls -la /dev/ttyUSB0

# 检查串口权限
ls -l /dev/ttyUSB0
# 应该属于 dialout 组

# 如果权限不足，临时修复：
sudo chmod 666 /dev/ttyUSB0
```

**检查物理连接：**
- USB 转串口模块是否插好
- UART 线是否松动：
  - TX（发送）→ 接舵机 RX
  - RX（接收）→ 接舵机 TX
  - GND → 接舵机 GND

---

### **方案 3：重启串口服务**

```bash
# 重启串口服务
sudo systemctl restart serial-getty@ttyUSB0 2>/dev/null || true

# 或者拔插 USB 转串口
# 1. 拔掉 USB
# 2. 等待 2 秒
# 3. 重新插入

# 检查是否重新出现
ls -la /dev/ttyUSB*
```

---

### **方案 4：强制复位舵机**

```bash
cd /home/sunrise/Desktop

# 发送复位命令
python3 -c "
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
print('已打开串口')

# 发送复位命令给所有舵机（广播 ID 0xFE）
for i in range(3):
    cmd = bytes([0xFF, 0xFE, 0x04, 0x02, 0x30, 0x01, 0xE9])
    ser.write(cmd)
    print(f'发送复位命令 {i+1}')
    time.sleep(0.5)
    response = ser.read(10)
    if response:
        print(f'收到响应: {response.hex()}')
    else:
        print('无响应')

ser.close()
print('完成')
"
```

---

### **方案 5：降低舵机速度/扭矩**

如果舵机刚上电，可能处于保护状态：

```bash
cd /home/sunrise/Desktop
python3 four_servo_control.py pose 2048 2150 2048 2130 --speeds 50 50 50 50
```

---

### **方案 6：手动移动舵机**

检查舵机是否机械卡住：

1. **断开舵机电源**
2. **手动转动舵机臂** - 应该能轻松转动
3. **如果卡住** - 检查是否有机械干涉
4. **重新上电** - 再次测试

---

## 🎯 诊断清单

请在开发板上依次执行并告诉我结果：

```bash
# 1. 检查串口
ls -la /dev/ttyUSB* && echo "[OK] 串口存在" || echo "[X] 无串口"

# 2. 检查舵机电源（如果有 GPIO）
cat /sys/class/gpio/gpio*/value 2>/dev/null | grep -E "1|0" | head -5

# 3. 测试舵机 ping
cd /home/sunrise/Desktop && python3 four_servo_control.py ping-all 2>&1 | head -10

# 4. 查看详细错误
python3 -c "
import serial
try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    print('串口正常')
    ser.close()
except Exception as e:
    print(f'串口错误: {e}')
"
```

---

## 📊 常见场景

### 场景 1：开发板刚上电

**症状**：所有舵机都超时

**原因**：舵机电源可能需要时间稳定

**解决**：
```bash
# 等待 30 秒让电源稳定
sleep 30
# 再次测试
python3 four_servo_control.py ping-all
```

---

### 场景 2：脚本长时间运行后失败

**症状**：之前工作正常，突然超时

**原因**：舵机过热保护或串口断连

**解决**：
```bash
# 1. 关闭舵机电源 10 秒
# 2. 重新上电
# 3. 等待 5 秒后再运行脚本
```

---

### 场景 3：只有部分舵机失败

**症状**：舵机 0 和 1 正常，2 和 3 超时

**原因**：特定舵机的连接问题

**解决**：
- 检查对应舵机的 UART 线
- 尝试单独测试该舵机

---

## 🔑 关键问题

**请在开发板上运行这 3 个命令并告诉我输出：**

```bash
# 命令 1：检查串口
ls -la /dev/ttyUSB*

# 命令 2：检查舵机状态
cd /home/sunrise/Desktop && python3 four_servo_control.py ping-all 2>&1 | head -20

# 命令 3：简单串口测试
python3 -c "import serial; ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1); print('串口 OK'); ser.close()"
```

根据这些输出，我可以判断具体是哪个问题！
