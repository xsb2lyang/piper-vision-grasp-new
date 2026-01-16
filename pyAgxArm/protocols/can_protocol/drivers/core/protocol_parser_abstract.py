#!/usr/bin/env python3
# -*-coding:utf8-*-

from .protocol_parser_interface import ProtocolParserInterface

class ProtocolParserInterface(ProtocolParserInterface):
    
    def parse_packet(self, **kwargs):
        ...

    def pack(self, **kwargs):
        ...

    