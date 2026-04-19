import requests
import time

# 检测端地址（必须与main_detect.py中的Flask地址一致）
DETECT_URL = "http://127.0.0.1:5000/update_classes"


def send_class_update(classes):
    """发送类别更新请求到检测端"""
    payload = {"classes": classes}
    try:
        response = requests.post(DETECT_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ 云端A发送类别更新: {classes} → {response.json()}")
        else:
            print(f"❌ 云端A发送失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 云端A发送异常: {str(e)}")


if __name__ == '__main__':
    print("☁️ 云端A模拟启动，开始发送类别更新...")

    # 模拟云端A每5秒发送一次类别更新
    while True:
        # 1. 发送bolt(0)和sensor(9)的类别
        send_class_update([0])
        time.sleep(5)

        # 2. 发送washer(2)和cable(4)的类别
        send_class_update([2, 4])
        time.sleep(5)