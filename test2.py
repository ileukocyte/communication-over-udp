from enum import Enum

import zlib


class MessageType(Enum):
    DATA = 0
    ACK = 1
    NACK = 2
    INIT = 3
    FIN = 4
    KEEP_ALIVE = 5
    TIMEOUT = 6
    CHANGE_MAX_FRAGMENT_SIZE = 7
    FRAGMENT_COUNT = 8
    FILE_PATH = 9
    SWITCH_NODES = 10
    ACK_AND_SWITCH = 11
    TEXT = 12


class Message:
    def __init__(self, frag_num, msg_type, data=bytes(), checksum=None):
        self.frag_num = frag_num
        self.msg_type = msg_type
        self.data = data
        self.checksum = self.calc_checksum() if checksum is None else checksum

    def calc_checksum(self):
        frag_num_bytes = self.frag_num.to_bytes(3, byteorder="big")
        msg_type_bytes = self.msg_type.value.to_bytes(1, byteorder="big")

        return zlib.crc32(frag_num_bytes + msg_type_bytes + self.data)

    def serialize(self):
        frag_num_bytes = self.frag_num.to_bytes(3, byteorder="big")
        msg_type_bytes = self.msg_type.value.to_bytes(1, byteorder="big")
        crc_bytes = self.checksum.to_bytes(4, byteorder="big")

        return frag_num_bytes + msg_type_bytes + crc_bytes + self.data

    @staticmethod
    def deserialize(data):
        frag_number = int.from_bytes(data[:3])
        msg_type = None

        for mt in MessageType:
            if mt.value == int(data[3]):
                msg_type = mt

        if not msg_type:
            raise TypeError("The provided message type is not recognized!")

        checksum = int.from_bytes(data[4:8])
        msg_data = data[8:]

        return Message(frag_number, msg_type, msg_data, checksum)
