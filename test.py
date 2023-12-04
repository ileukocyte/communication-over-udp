# from bitarray import bitarray
#from messages import MessageType, Message


# print(int(MessageType.FILE_PATH.value.to01(), 2))
#
# msg = Message(2, MessageType.FILE_PATH, b'C:/Users/alexi/Desktop/hello.txt')
#
# print(msg.checksum)
#
# test = Message.deserialize(msg.serialize())
#
# print(f'frag_number: {test.frag_num}, msg_type: {test.msg_type}, crc: {test.checksum}, data: {test.data.decode()}')

# byte_data = msg.serialize()
#
# bitarr = bitarray()
# bitarr.frombytes(byte_data)
#
# bitarr = bitarr[:len(bitarr) - 4]
#
# print(bitarr.to01())
#
# frag_number = int(bitarr[:24].to01(), 2)
# msg_type = None
#
# for mt in BitMessageType:
#     if mt.value == bitarr[24:28]:
#         msg_type = mt
#
# crc = int(bitarr[28:60].to01(), 2)
# data = bitarr[60:].tobytes().decode()

# print(f'frag_number: {frag_number}, msg_type: {msg_type}, crc: {crc}, data: {data}')
