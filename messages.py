from enum import Enum
from bitarray import bitarray

import zlib


class MessageType(Enum):
    DATA = bitarray("0000")
    ACK = bitarray("0001")
    NACK = bitarray("0010")
    INIT = bitarray("0011")
    FIN = bitarray("0100")
    KEEP_ALIVE = bitarray("0101")
    TIMEOUT = bitarray("0110")
    CHANGE_MAX_FRAGMENT_SIZE = bitarray("0111")
    FRAGMENT_COUNT = bitarray("1000")
    FILE_PATH = bitarray("1001")
    SWITCH_NODES = bitarray("1010")
    ACK_AND_SWITCH = bitarray("1011")


class Message:
    def __init__(self, fragment_number, msg_type, data=bytes(), checksum=None):
        self.fragment_number = fragment_number
        self.msg_type = msg_type
        self.checksum = zlib.crc32(data) if not checksum else checksum
        self.data = data

    def serialize(self):
        frag_num = bin(self.fragment_number & 0xFFFFFF)[2:].zfill(24)
        crc = bin(self.checksum)[2:].zfill(32)

        arr = bitarray(frag_num)

        arr.extend(self.msg_type.value)
        arr.extend(bitarray(crc))
        arr.frombytes(self.data)

        return arr.tobytes()

    @staticmethod
    def deserialize(data):
        bitarr = bitarray()
        bitarr.frombytes(data)

        bitarr = bitarr[:len(bitarr) - 4]

        frag_number = int(bitarr[:24].to01(), 2)
        msg_type = None

        for mt in MessageType:
            if mt.value == bitarr[24:28]:
                msg_type = mt

        if not msg_type:
            raise TypeError("The provided message type is not recognized!")

        checksum = int(bitarr[28:60].to01(), 2)
        msg_data = bitarr[60:].tobytes()

        return Message(frag_number, msg_type, msg_data, checksum)
