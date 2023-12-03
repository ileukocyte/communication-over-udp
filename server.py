import os
import socket
import zlib

from messages import Message, MessageType

SERVER_IP = "127.0.0.1"
SERVER_PORT = 50601

CLIENT_IP = None
CLIENT_PORT = None

current_name = None
current_data = []


def receive(ip, port):
    global current_name, current_data, CLIENT_IP, CLIENT_PORT

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((ip, port))

    while True:
        data, addr = s.recvfrom(1024)
        msg = Message.deserialize(data)

        if msg.msg_type == MessageType.INIT:
            print("Received init message")
            s.sendto(Message(0, MessageType.ACK).serialize(), addr)
            print(f"Sent acknowledgment")

            CLIENT_IP = addr[0]
            CLIENT_PORT = addr[1]
        elif msg.msg_type == MessageType.FIN:
            print("Received termination message")

            s.sendto(Message(0, MessageType.ACK).serialize(), addr)
            print(f"Sent acknowledgment")
        elif msg.msg_type == MessageType.KEEP_ALIVE:
            print("Received keep-alive message")

            s.sendto(Message(0, MessageType.ACK).serialize(), addr)
            print(f"Sent acknowledgment")
        elif msg.msg_type == MessageType.FILE_PATH:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                print(f"Received file path: {byte_data.decode()}")
                s.sendto(Message(0, MessageType.ACK).serialize(), addr)
                print(f"Sent acknowledgment")

                current_name = os.path.relpath(byte_data.decode())
            else:
                print(f"File path received incorrectly")
                s.sendto(Message(0, MessageType.NACK).serialize(), addr)
                print(f"Sent NACK")
        elif msg.msg_type == MessageType.FRAGMENT_COUNT:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                print(f"Received fragment count: {byte_data.decode()}")
                s.sendto(Message(0, MessageType.ACK).serialize(), addr)
                print(f"Sent acknowledgment")

                current_data = [None] * int(byte_data.decode())
            else:
                print(f"Fragment count received incorrectly")
                s.sendto(Message(0, MessageType.NACK).serialize(), addr)
                print(f"Sent NACK")
        elif msg.msg_type == MessageType.CHANGE_MAX_FRAGMENT_SIZE:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                print(f"Received fragment size: {byte_data.decode()}")
                s.sendto(Message(0, MessageType.ACK).serialize(), addr)
                print(f"Sent acknowledgment")
            else:
                print(f"Fragment size received incorrectly")
                s.sendto(Message(0, MessageType.NACK).serialize(), addr)
                print(f"Sent NACK")
        elif msg.msg_type == MessageType.TEST_MSG:
            byte_data = msg.data

            if msg.checksum == zlib.crc32(byte_data):
                print(f"Received fragment {msg.fragment_number}: {byte_data.decode()}")

                msg_type = MessageType.ACK if msg.fragment_number < len(current_data) - 1 else MessageType.ACK_AND_SWITCH

                s.sendto(Message(msg.fragment_number, msg_type).serialize(), addr)
                print(f"Sent acknowledgment for: {msg.fragment_number}")

                if msg.fragment_number == len(current_data) - 1:
                    """flatten array, write file, reset global vars"""

                # FOR FILE TRANSFER
                # if msg.fragment_number == len(current_data) - 1:
                #     """flatten array, write file, reset global vars"""
            else:
                print(f"Fragment {msg.fragment_number} received incorrectly")
                s.sendto(Message(msg.fragment_number, MessageType.NACK).serialize(), addr)
                print(f"Sent NACK for: {msg.fragment_number}")
        elif msg.msg_type == MessageType.SWITCH_NODES:
            print(f"Received switch req")
            s.sendto(Message(0, MessageType.ACK).serialize(), addr)
            print(f"Sent acknowledgment")
            break
        elif msg.msg_type == MessageType.DATA:
            byte_data = msg.data
        elif msg.msg_type == MessageType.ACK:
            """switch the nodes"""

        # decoded = data.decode()
        #
        # if decoded == "keep_alive":
        #     print("Received keep-alive message.")
        #
        #     # Send an acknowledgment for keep-alive
        #     ack = "ACK:keep_alive"
        #     s.sendto(ack.encode(), addr)
        #     print(f"Sent acknowledgment: {ack}")
        # else:
        #     message_info, fragment = decoded.split(":")
        #     total_fragments = int(message_info)
        #     print(f"Received fragment: {fragment}")
        #
        #     # Simulate positive acknowledgment for the received fragment
        #     ack = f"ACK:{total_fragments}"
        #     s.sendto(ack.encode(), addr)
        #     print(f"Sent acknowledgment: {ack}")


def server_switch():
    global CLIENT_IP, CLIENT_PORT, SERVER_PORT, SERVER_IP

    CLIENT_PORT, SERVER_PORT = SERVER_PORT, CLIENT_PORT
    CLIENT_IP, SERVER_IP = SERVER_IP, CLIENT_IP


def server():
    receive(SERVER_IP, SERVER_PORT)
