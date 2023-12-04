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
    TEXT = bitarray("1100")


class Message:
    def __init__(self, frag_num, msg_type, data=bytes(), checksum=None):
        self.frag_num = frag_num
        self.msg_type = msg_type
        self.data = data
        self.checksum = self.calc_checksum() if checksum is None else checksum

    def calc_checksum(self):
        frag_num_bytes = self.frag_num.to_bytes(3, byteorder="big")
        msg_type_bytes = int(self.msg_type.value.to01(), 2).to_bytes(1, byteorder="big")
        return zlib.crc32(frag_num_bytes + msg_type_bytes + self.data)

    def serialize(self):
        frag_num = bin(self.frag_num & 0xFFFFFF)[2:].zfill(24)
        crc = bin(self.checksum)[2:].zfill(32)

        arr = bitarray(frag_num)

        arr.extend(self.msg_type.value)
        arr.extend(bitarray(crc))
        arr.extend(bitarray('0000'))  # reserved
        arr.frombytes(self.data)

        return arr.tobytes()

    @staticmethod
    def deserialize(data):
        bitarr = bitarray()
        bitarr.frombytes(data)

        frag_number = int(bitarr[:24].to01(), 2)
        msg_type = None

        for mt in MessageType:
            if mt.value == bitarr[24:28]:
                msg_type = mt

        if not msg_type:
            raise TypeError("The provided message type is not recognized!")

        checksum = int(bitarr[28:60].to01(), 2)
        msg_data = bitarr[64:].tobytes()

        return Message(frag_number, msg_type, msg_data, checksum)
