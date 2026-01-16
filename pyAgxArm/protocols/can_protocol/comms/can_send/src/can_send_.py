#!/usr/bin/env python3
#codeing =utf-8 
import os
import ctypes
from ctypes import *

so = ctypes.cdll.LoadLibrary
# 当前文件所在目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼出 .so 的路径
SO_PATH = os.path.join(CURRENT_DIR, "libcan_send.so")
lib = so(SO_PATH) #刚刚生成的库文件的路径
# 使用 ctypes 库时定义 C 函数指针类型的一种方式。这用于告诉 ctypes 我们期望 C 函数指针指向的函数返回类型是 None，即没有返回值。
# 如果你的 C++ 函数有其他的返回类型，你需要相应地调整 ctypes.CFUNCTYPE 中的参数，以确保类型匹配。
# 例如，如果 C++ 函数返回 int，则可以使用 ctypes.CFUNCTYPE(ctypes.c_int)。
# func_t = ctypes.CFUNCTYPE(None)

# 设置函数的参数类型和返回类型，以便 ctypes 在调用时能够正确地处理参数和返回值。
# 这是确保 Python 与 C++ 之间的接口正确匹配的关键步骤。
lib.open_can.argtypes = [ctypes.c_char_p]#指定函数的参数类型。
lib.open_can.restype = ctypes.c_int#指定函数的返回类型。

# get_can_name
lib.get_can_name.argtypes = [
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
]
lib.get_can_name.restype = ctypes.c_int

lib.send_int_data.argtypes = [ctypes.c_int, ctypes.c_int, \
    ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8, ctypes.c_uint8]
lib.send_int_data.restype = ctypes.c_bool
# can_channel = b'can0'
# sock = lib.open_can(ctypes.c_char_p(can_channel))
# lib.send_int_data(sock, 0x110, 
#                   1, 2, 3, 4, 5, 6, 7, 8)
def get_can_sock(channel:str) -> int:
    can_channel = channel.encode("utf-8")
    return lib.open_can(ctypes.c_char_p(can_channel))

def get_can_name(sock: int) -> str:
    buf = ctypes.create_string_buffer(32)
    ret = lib.get_can_name(sock, buf, 32)
    if ret != 0:
        return ""
    return buf.value.decode()

def can_send(sock, id, data:list) -> bool:
    return lib.send_int_data(sock, id, 
                  data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])

data = [1, 2, 3, 4, 5, 6, 7, 8]
a=get_can_sock("can0")
print("device =", get_can_name(a))
b=get_can_sock("can1")
print("device =", get_can_name(b))
print(a)
print(b)
c = can_send(b, 0x110, data)
print(c)