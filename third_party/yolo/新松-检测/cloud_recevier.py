from flask import Flask, request, jsonify
import time

app = Flask(__name__)

@app.route('/detect', methods=['POST'])
def receive_cloud_data():
    """接收检测端发送的检测结果"""
    data = request.json
    print(f"☁️ 云端A接收数据: {data}")
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    print("☁️ 云端A服务启动在 http://127.0.0.1:5002")
    app.run(host='0.0.0.0', port=5002)