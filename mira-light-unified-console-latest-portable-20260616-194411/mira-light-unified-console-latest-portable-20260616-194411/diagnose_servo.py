#!/usr/bin/env python3
"""
舵机通信诊断脚本
"""

import serial
import sys
import time

def check_serial_ports():
    """检查可用串口"""
    import glob
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyS*')
    print(f"[检查] 找到 {len(ports)} 个串口设备:")
    for port in ports:
        print(f"  - {port}")
    return ports

def test_serial_connection(port, baudrate=115200):
    """测试串口连接"""
    print(f"\n[测试] 串口 {port} @ {baudrate} baud...")
    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        print(f"  [OK] 串口打开成功")

        # 尝试读取任何现有数据
        time.sleep(0.5)
        data = ser.read(100)
        if data:
            print(f"  [信息] 收到数据: {data.hex()}")
        else:
            print(f"  [信息] 无数据（正常）")

        # 发送 ping 命令给舵机 0x01
        print(f"\n  [测试] 发送舵机 ping (ID=1)...")
        ping_cmd = bytes([0xFF, 0x01, 0x04, 0x02, 0x30, 0x01, 0xE9])
        ser.write(ping_cmd)
        print(f"  已发送: {ping_cmd.hex()}")

        response = ser.read(10)
        if response:
            print(f"  [OK] 收到响应: {response.hex()}")
            return True
        else:
            print(f"  [X] 无响应 - 舵机可能未连接或电源关闭")
            return False

    except serial.SerialException as e:
        print(f"  [错误] 串口错误: {e}")
        return False
    except Exception as e:
        print(f"  [错误] {e}")
        return False
    finally:
        try:
            ser.close()
        except:
            pass

def test_multiple_baudrates(port):
    """测试多个波特率"""
    baudrates = [9600, 19200, 57600, 115200, 230400]
    print(f"\n[测试] 不同波特率...")
    for baud in baudrates:
        print(f"\n  --- {baud} baud ---")
        test_serial_connection(port, baud)

def main():
    print("=" * 60)
    print("舵机通信诊断工具")
    print("=" * 60)

    # 检查串口
    ports = check_serial_ports()

    if not ports:
        print("\n[错误] 未找到串口设备！")
        print("请检查：")
        print("  1. USB 转串口适配器是否连接")
        print("  2. 舵机 UART 线是否连接到开发板")
        return 1

    # 测试第一个串口
    print(f"\n测试第一个串口: {ports[0]}")
    success = test_serial_connection(ports[0])

    if not success:
        print("\n[建议] 尝试不同波特率...")
        test_multiple_baudrates(ports[0])

    print("\n" + "=" * 60)
    if success:
        print("[结论] 舵机通信正常！")
    else:
        print("[结论] 舵机无响应")
        print("\n请检查：")
        print("  1. 舵机电源是否开启（检查电源指示灯）")
        print("  2. UART 连接线是否松动（TX↔RX, GND）")
        print("  3. 舵机是否卡住或过载（尝试手动转动）")
        print("  4. 舵机 ID 是否正确（默认通常是 0x01）")
    print("=" * 60)

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
