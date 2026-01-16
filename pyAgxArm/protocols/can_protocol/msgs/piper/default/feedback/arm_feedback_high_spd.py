#!/usr/bin/env python3
# -*-coding:utf8-*-
from ....core.attritube_base import AttributeBase
from typing import Union

class ArmMsgFeedbackHighSpd(AttributeBase):
    '''
    feedback
    
    驱动器信息高速反馈 0x5

    节点 ID:
        0x1~0x06
    
    CAN ID:
        0X251~0x256

    Args:
        motor_speed: 电机当前转速
        current: 电机当前电流
        pos: 电机当前位置
        torque: 经过固定系数转换的力矩,单位0.001N/m
    
    位描述:

        Byte 0: 转速高八位, int16, 电机当前转速 单位: 0.001rad/s
        Byte 1: 转速低八位
        Byte 2: 电流高八位, uint16, 电机当前电流 单位: 0.001A
        Byte 3: 电流低八位
        Byte 4: 位置最高位, int32, 电机当前位置 单位: rad
        Byte 5: 位置次高位
        Byte 6: 位置次低位
        Byte 7: 位置最低位
    '''
    '''
    feedback
    
    High-Speed Feedback of Drive Information 0x5

    Node ID:
        0x1~0x06

    CAN ID:
        0x251~0x256

    Args:
        motor_speed: Motor Speed.
        current: Motor Current.
        pos: Motor Position.
        torque: Torque converted using a fixed coefficient, with a unit of 0.001 N/m.

    
    Bit Description:

        Byte 0: Motor Speed (High Byte), int16, unit: 0.001rad/s
        Byte 1: Motor Speed (Low Byte)
        Byte 2: Motor Current (High Byte), uint16, unit: 0.001A
        Byte 3: Motor Current (Low Byte)
        Byte 4: Motor Position (Most Significant Byte), int32, unit: rad
        Byte 5: Motor Position (Second Most Significant Byte)
        Byte 6: Motor Position (Second Least Significant Byte)
        Byte 7: Motor Position (Least Significant Byte)
    '''
    _derived_fields_ = ("torque",)
    _COEFFICIENT_1 = 1.18125
    _COEFFICIENT_2 = 0.95844
    _VALID_CAN_ID = 0x000
    _VALID_CAN_ID_1 = [0x251, 0x252, 0x253]
    _VALID_CAN_ID_2 = [0x254, 0x255, 0x256]

    def __init__(self,
                 motor_speed: Union[int, float] = 0,
                 current: Union[int, float] = 0,
                 pos: Union[int, float] = 0
                 ):
        self.motor_speed = motor_speed
        self.current = current
        self.pos = pos
    
    @property
    def torque(self) -> float:
        if(self._VALID_CAN_ID in self._VALID_CAN_ID_1):
            return self.current * self._COEFFICIENT_1
        elif(self._VALID_CAN_ID in self._VALID_CAN_ID_2):
            return self.current * self._COEFFICIENT_2
        else:
            return 0.0

class ArmMsgFeedbackHighSpd1(ArmMsgFeedbackHighSpd):
    '''CAN ID:
        0x251'''
    _VALID_CAN_ID = 0x251

class ArmMsgFeedbackHighSpd2(ArmMsgFeedbackHighSpd):
    '''CAN ID:
        0x252'''
    _VALID_CAN_ID = 0x252

class ArmMsgFeedbackHighSpd3(ArmMsgFeedbackHighSpd):
    '''CAN ID:
        0x253'''
    _VALID_CAN_ID = 0x253

class ArmMsgFeedbackHighSpd4(ArmMsgFeedbackHighSpd):
    '''CAN ID:
        0x254'''
    _VALID_CAN_ID = 0x254

class ArmMsgFeedbackHighSpd5(ArmMsgFeedbackHighSpd):
    '''CAN ID:
        0x255'''
    _VALID_CAN_ID = 0x255

class ArmMsgFeedbackHighSpd6(ArmMsgFeedbackHighSpd):
    '''CAN ID:
        0x256'''
    _VALID_CAN_ID = 0x256

class ArmMsgFeedbackAllHighSpd(AttributeBase):
    '''CAN ID:
        0x251~0x256'''
    def __init__(self,
                 joint_1 = ArmMsgFeedbackHighSpd(),
                 joint_2 = ArmMsgFeedbackHighSpd(),
                 joint_3 = ArmMsgFeedbackHighSpd(),
                 joint_4 = ArmMsgFeedbackHighSpd(),
                 joint_5 = ArmMsgFeedbackHighSpd(),
                 joint_6 = ArmMsgFeedbackHighSpd()):
        self.joint_1 = joint_1
        self.joint_2 = joint_2
        self.joint_3 = joint_3
        self.joint_4 = joint_4
        self.joint_5 = joint_5
        self.joint_6 = joint_6
