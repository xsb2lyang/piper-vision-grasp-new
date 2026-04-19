import socket
import time


def arm_receiver():
    host = '127.0.0.1'
    port = 5001  # 与 main_detect.py 中的 ARM_PORT 一致

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)  # 允许最多5个待处理连接
    print(f"✅ 机械臂接收脚本启动，监听 {host}:{port} (持续接收模式)")

    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"🔗 机械臂客户端连接: {addr}")

            while True:
                data = conn.recv(1024).decode().strip()
                if not data:  # 连接关闭
                    print(f"⚠️ 机械臂连接断开: {addr}")
                    break
                print(f"📦 机械臂接收数据: {data}")

            conn.close()  # 关闭当前连接后继续等待新连接

    except KeyboardInterrupt:
        print("\n🛑 机械臂接收服务已停止")
    finally:
        server_socket.close()


if __name__ == '__main__':
    arm_receiver()