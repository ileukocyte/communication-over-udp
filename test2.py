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


class Message:
    def __init__(self, fragment_number, msg_type, data=bytes(), checksum=None):
        self.fragment_number = fragment_number
        self.msg_type = msg_type
        self.checksum = zlib.crc32(data) if checksum is None else checksum
        self.data = data

    def serialize(self):
        crc_bytes = self.checksum.to_bytes(4, byteorder="big")
        msg_type_bytes = self.msg_type.value.to_bytes(1, byteorder="big")
        frag_num_bytes = self.fragment_number.to_bytes(3, byteorder="big")

        # Concatenate the bytes representations
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
