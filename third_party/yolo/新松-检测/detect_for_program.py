import warnings

warnings.filterwarnings('ignore')
import cv2
import requests
import socket
import threading
from flask import Flask, request, jsonify
from ultralytics import YOLO
import time

# ================== 配置参数 ==================
# 1. 机械臂通信配置（本地测试用）
ARM_IP = "127.0.0.1"  # 本地回环地址
ARM_PORT = 5001  # 机械臂接收端口

# 2. 云端通信配置（局域网测试用）
CLOUD_API = "http://127.0.0.1:5002/detect"  # 云端接收地址

# 3. 模型配置
MODEL_PATH = '/home/l/PycharmProjects/ultralytics-yolo11/yolo11n.pt'  #检测权重的路径
CLASSES = ["bolt", "nut", "washer", "screw", "cable", "connector", "circuit", "motor", "gear", "sensor"]  # 类别自行设置

# 4. 全局状态
current_classes = []  # 当前检测的类别列表


# ================== 机械臂通信函数 ==================
def send_to_arm(objects):
    """发送检测结果到机械臂接收脚本（TCP）"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ARM_IP, ARM_PORT))
        # 格式化指令: "x,y,cls,conf"
        cmd = ";".join([f"{x},{y},{cls},{conf}" for x, y, cls, conf in objects])
        sock.sendall((cmd + "\n").encode())
        sock.close()
        print(f"✅ 机械臂已发送: {cmd}")
    except Exception as e:
        print(f"❌ 机械臂发送失败: {str(e)}")


# ================== 云端通信函数 ==================
def send_to_cloud(results):
    """发送检测结果到云端接收脚本（HTTP）"""
    try:
        payload = {
            "objects": [
                {
                    "x": int(obj[0]),
                    "y": int(obj[1]),
                    "class": CLASSES[int(obj[2])],
                    "confidence": float(obj[3])
                } for obj in results
            ]
        }
        response = requests.post(CLOUD_API, json=payload, timeout=2)
        if response.status_code == 200:
            print("✅ 云端已接收")
        else:
            print(f"❌ 云端返回: {response.status_code}")
    except Exception as e:
        print(f"❌ 云端发送失败: {str(e)}")


# ================== 检测端Flask接口 ==================
app = Flask(__name__)


@app.route('/update_classes', methods=['POST'])
def update_classes():
    """接收云端A发送的类别更新请求"""
    global current_classes
    data = request.json
    if 'classes' not in data or not isinstance(data['classes'], list):
        return jsonify({"error": "Invalid format. Use {\"classes\": [0,2,5]}"}), 400

    # 验证类别索引是否在0-9范围内
    valid_classes = [c for c in data['classes'] if 0 <= c < len(CLASSES)]
    if not valid_classes:
        return jsonify({"error": "No valid classes provided"}), 400

    current_classes = valid_classes
    print(f"🔄 类别更新: {valid_classes} (当前检测: {current_classes})")
    return jsonify({"status": "success", "current_classes": valid_classes})


# ================== 主推理循环 ==================
def main():
    global current_classes

    # 初始化模型
    model = YOLO(MODEL_PATH)
    print(f"ℹ️ 模型加载完成: {MODEL_PATH}")

    # 打开摄像头（0=默认摄像头）
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("❌ 无法打开摄像头")

    print("🚀 实时检测启动（按ESC退出）")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # 1. 模型推理（动态使用current_classes）
        results = model.predict(
            frame,#这里直接用cv开的摄像头获取的图像给模型，避免云端切换检测目标时相机反复启动
            imgsz=640,
            classes=current_classes,  # 关键：动态生效
            conf=0.3,
            iou=0.5
        )

        # 2. 处理检测结果
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])# 获取框的坐标分别是左上角和右下角的坐标
                cls = int(box.cls[0])
                conf = float(box.conf[0])

                # 仅保留当前类别列表中的结果
                if cls in current_classes:
                    cx = (x1 + x2) // 2     #中心坐标x
                    cy = (y1 + y2) // 2     #中心坐标y
                    detections.append([cx, cy, cls, conf])

        # 3. 发送机械臂数据
        if detections:
            threading.Thread(target=send_to_arm, args=(detections,)).start()

        # 4. 发送云端数据
        if detections:
            threading.Thread(target=send_to_cloud, args=(detections,)).start()

        # 5. 显示结果（调试用）
        for d in detections:
            cv2.circle(frame, (d[0], d[1]), 5, (0, 255, 0), -1)
            cv2.putText(frame, CLASSES[d[2]], (d[0] + 10, d[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Detection", frame)

        # 退出条件
        if cv2.waitKey(1) & 0xFF == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()


# ================== 启动脚本 ==================
if __name__ == '__main__':
    # 启动Flask服务（后台线程）
    threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": 5000, "debug": False}, daemon=True).start()

    # 启动主检测循环
    main()