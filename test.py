# from bitarray import bitarray
from messages import MessageType, Message

# message = 'abCd141aX'
#
# if len(message) % 2 != 0 and len(message) != 0:
#     message = message[:len(message) - 1]
#
# new_data = [''] * (len(message) // 2)
#
# for i in range(0, len(message), 2):
#     new_data[i // 2] = f'{message[i + 1]}{message[i]}'
#
# print(' '.join(new_data))

# fragments = [message[i:i + 2] for i in range(0, len(message), 2) for _ in range(5)]
# repeated_with_index = [(index // 5, fragment) for index, fragment in enumerate(fragments)]
# print(repeated_with_index)

# print(int(MessageType.FILE_PATH.value.to01(), 2))

msg = Message(2, MessageType.FILE_PATH, b'C:/Users/alexi/Desktop/hello.txt')

#print(msg.checksum)
#print(int.from_bytes(((test2.MessageType.FILE_PATH.value & 0xF) << 4).to_bytes(1, byteorder="big")) >> 4)
#print(Message(2, MessageType.FILE_PATH, b'C:/Users/alexi/Desktop/hello.txt').serialize())
#print(test2.Message(2, test2.MessageType.FILE_PATH, b'C:/Users/alexi/Desktop/hello.txt').serialize())

test = Message.deserialize(msg.serialize())

print(f'frag_number: {test.frag_num}, msg_type: {test.msg_type}, crc: {test.checksum}, data: {test.data.decode()}')

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
