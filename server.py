import ipaddress
import os
import socket
import zlib

#from messages import Message, MessageType
from test2 import Message, MessageType

server_ip = None
server_port = None

client_ip = None
client_port = None

current_name = None
current_data = []

max_fragment_size = 0


def receive(ip, port):
    global current_name, current_data, max_fragment_size, client_ip, client_port

    expected_frag_num = 0

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((ip, port))

    while True:
        data, addr = s.recvfrom(max(1024, max_fragment_size + 8))
        msg = Message.deserialize(data)

        if msg.msg_type == MessageType.INIT:
            print("Connection init received")

            s.sendto(Message(0, MessageType.ACK).serialize(), addr)

            print("Connection init acknowledged")

            client_ip = addr[0]
            client_port = addr[1]

            # default
            max_fragment_size = 64
            expected_frag_num = 0
        elif msg.msg_type == MessageType.FIN:
            print("Termination request received")

            s.sendto(Message(0, MessageType.ACK).serialize(), addr)

            print("Termination request acknowledged")
        elif msg.msg_type == MessageType.KEEP_ALIVE:
            print("Keep-alive message received")

            s.sendto(Message(0, MessageType.ACK).serialize(), addr)

            print("Keep-alive message acknowledged")
        elif msg.msg_type == MessageType.FILE_PATH:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                print(f"File path received: {byte_data.decode()}")

                s.sendto(Message(0, MessageType.ACK).serialize(), addr)

                print("File path acknowledged")

                current_name = os.path.basename(byte_data.decode())
            else:
                print("File path was not received correctly")

                s.sendto(Message(0, MessageType.NACK).serialize(), addr)

                print("Negative acknowledgement sent")
        elif msg.msg_type == MessageType.FRAGMENT_COUNT:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                print(f"Fragment count received: {byte_data.decode()}")

                s.sendto(Message(0, MessageType.ACK).serialize(), addr)

                print("Fragment count acknowledged")

                current_data = [b""] * int(byte_data.decode())
            else:
                print("Fragment count was not received correctly")

                s.sendto(Message(0, MessageType.NACK).serialize(), addr)

                print("Negative acknowledgement sent")
        elif msg.msg_type == MessageType.CHANGE_MAX_FRAGMENT_SIZE:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                max_fragment_size = int(byte_data.decode())

                print(f"Max fragment size received: {byte_data.decode()}")

                s.sendto(Message(0, MessageType.ACK).serialize(), addr)

                print(f"Max fragment size acknowledged")
            else:
                print("Max fragment size was not received correctly")

                s.sendto(Message(0, MessageType.NACK).serialize(), addr)

                print("Negative acknowledgement sent")
        elif msg.msg_type == MessageType.SWITCH_NODES:
            print(f"Node switch requested")

            s.sendto(Message(0, MessageType.ACK).serialize(), addr)

            print(f"Node switch request acknowledged")

            break
        elif msg.msg_type == MessageType.DATA:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data) and msg.frag_num == expected_frag_num:
                current_data[msg.frag_num] = byte_data

                print(f"Fragment {msg.frag_num} received: {byte_data.decode()}")

                expected_frag_num += 1

                msg_type = MessageType.ACK_AND_SWITCH if expected_frag_num == len(current_data) else MessageType.ACK

                s.sendto(Message(msg.frag_num, msg_type).serialize(), addr)

                print(f"Fragment {msg.frag_num} acknowledged")

                if expected_frag_num == len(current_data):
                    with open(current_name, "wb") as file:
                        file.write(b"".join(current_data))

                        current_name = None
                        current_data = None

                        expected_frag_num = 0
            else:
                print(f"Fragment {msg.frag_num} was not received correctly")

                s.sendto(Message(expected_frag_num - 1, MessageType.NACK).serialize(), addr)

                print(f"Negative acknowledgement sent for {expected_frag_num - 1}")
        elif msg.msg_type == MessageType.ACK:
            print("Node switch request acknowledged")
        elif msg.msg_type == MessageType.NACK:
            print("Negative acknowledgement sent for node switch request")


def server_switch():
    global client_ip, client_port, server_port, server_ip

    client_port, server_port = server_port, client_port
    client_ip, server_ip = server_ip, client_ip


def server():
    global server_ip, server_port

    while True:
        try:
            ip = input("Enter the server IP address: ").strip()

            ipaddress.IPv4Address(ip)

            server_ip = ip

            port = input("Enter the server port: ").strip()

            try:
                if 0 <= int(port) <= 65535:
                    server_port = int(port)

                    receive(server_ip, server_port)

                    break
                else:
                    raise ValueError()
            except ValueError:
                print("The port is invalid! Try again!")
        except ipaddress.AddressValueError:
            print("The address is invalid! Try again!")
