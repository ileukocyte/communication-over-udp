import ipaddress
import os.path
import random
import socket
import threading
import time

# from messages import Message, MessageType
from test2 import Message, MessageType

keep_alive_socket = None

client_ip = None
client_port = None

server_ip = None
server_port = None

max_fragment_size = 64

data_transferred = False
alive = True

file_err_simulation_mode = False


def send(ip, port):
    global alive, max_fragment_size, data_transferred, client_ip, client_port, server_port, server_ip, file_err_simulation_mode

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    init_msg = Message(0, MessageType.INIT)
    s.sendto(init_msg.serialize(), (ip, port))

    print("Connection init requested")

    while True:
        try:
            s.settimeout(10)
            ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
            received_ack = Message.deserialize(ack)

            if received_ack.msg_type == MessageType.ACK:
                print("Connection successfully initialized")

                break
        except socket.timeout:
            print("Timeout occurred while waiting for acknowledgement of connection init. Resending...")
            s.sendto(init_msg.serialize(), (ip, port))

    while True:
        print("Select the mode or type in \"EXIT\" to terminate the session:")
        print("1. Transfer a file")
        print("2. Set the maximum fragment size")
        print("3. Switch the nodes")
        print(f"4. Turn the file transfer error simulation mode {'on' if not file_err_simulation_mode else 'off'}")

        mode = input().strip().upper()

        if mode == "EXIT":
            fin_msg = Message(0, MessageType.FIN)
            s.sendto(fin_msg.serialize(), (ip, port))
            print("Connection termination requested")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print("Connection successfully terminated")

                        alive = False

                        s.close()

                        break
                except socket.timeout:
                    print("Timeout occurred while waiting for acknowledgement of connection termination")

                    s.sendto(fin_msg.serialize(), (ip, port))

            break
        elif mode == "1":
            path = input("Enter your file path: ")

            if not os.path.exists(path):
                print("The path is invalid! Try again")

                continue

            data_transferred = True

            msg = Message(0, MessageType.FILE_PATH, path.encode())

            s.sendto(msg.serialize(), (ip, port))

            print(f"File path sent: {path}")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print("File path sent successfully")

                        break
                    elif received_ack.msg_type == MessageType.NACK:
                        print("File path was not received correctly. Resending...")

                        s.sendto(msg.serialize(), (ip, port))
                except socket.timeout:
                    print("Timeout occurred while waiting for file path acknowledgement")

                    s.sendto(msg.serialize(), (ip, port))

            with open(path, "rb") as file:
                content = file.read()
                fragments = [content[i:i + max_fragment_size] for i in range(0, len(content), max_fragment_size)]

                count_msg = Message(0, MessageType.FRAGMENT_COUNT, f"{len(fragments)}".encode())

                s.sendto(count_msg.serialize(), (ip, port))

                print(f"Fragment count ({len(fragments)}) sent")

                while True:
                    try:
                        s.settimeout(10)
                        ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                        received_ack = Message.deserialize(ack)

                        if received_ack.msg_type == MessageType.ACK:
                            print("Fragment count successfully received")

                            break
                        elif received_ack.msg_type == MessageType.NACK:
                            print("Fragment count was not received correctly. Resending...")

                            s.sendto(count_msg.serialize(), (ip, port))
                    except socket.timeout:
                        print("Timeout occurred while waiting for fragment count acknowledgement. Resending...")

                        s.sendto(count_msg.serialize(), (ip, port))

                window_size = 4
                base = 0
                next_sequence_number = 0

                rnd_frag_num = random.randrange(0, len(fragments))

                # Go-Back-N
                while base < len(fragments):
                    while next_sequence_number < min(base + window_size, len(fragments)):
                        fragment = fragments[next_sequence_number]

                        msg = Message(next_sequence_number, MessageType.DATA, fragment) if not file_err_simulation_mode or next_sequence_number != rnd_frag_num else (
                            Message(next_sequence_number, MessageType.DATA, fragment, checksum=0)
                        )

                        if next_sequence_number == rnd_frag_num:
                            rnd_frag_num = -1

                        s.sendto(msg.serialize(), (ip, port))

                        next_sequence_number += 1

                    try:
                        s.settimeout(16)

                        while True:
                            ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                            received_ack = Message.deserialize(ack)

                            if received_ack.msg_type == MessageType.ACK and received_ack.fragment_number >= base:
                                print(f"Acknowledgement received for fragment {received_ack.fragment_number}")

                                base = received_ack.fragment_number + 1

                                break
                            elif received_ack.msg_type == MessageType.ACK_AND_SWITCH and received_ack.fragment_number >= base:
                                print(f"Acknowledgement received for fragment {received_ack.fragment_number}")

                                base = received_ack.fragment_number + 1

                                while True:
                                    print("The server asks if you would like to switch the roles:")
                                    print("1. Yes")
                                    print("2. No")

                                    mode = input().strip().upper()

                                    if mode == "1":
                                        s.sendto(Message(0, MessageType.ACK).serialize(), (ip, port))

                                        data_transferred = False

                                        break
                                    elif mode == "2":
                                        s.sendto(Message(0, MessageType.NACK).serialize(), (ip, port))

                                        data_transferred = False

                                        break
                                    else:
                                        print("Invalid input! Please try again!")

                                break
                            else:
                                next_sequence_number = received_ack.fragment_number

                                print("Invalid or no acknowledgement received. Resending the window...")

                                break
                    except socket.timeout:
                        next_sequence_number = base

                        print("Timeout occurred while waiting for acknowledgement. Resending the window...")
        elif mode == "2":
            try:
                size = int(input("Enter your size in bytes: "))

                if size < 1:
                    raise ValueError

                msg = Message(0, MessageType.CHANGE_MAX_FRAGMENT_SIZE, f'{size}'.encode())

                s.sendto(msg.serialize(), (ip, port))

                print(f"Maximum fragment size ({size}) sent")

                while True:
                    try:
                        s.settimeout(10)
                        ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                        received_ack = Message.deserialize(ack)

                        if received_ack.msg_type == MessageType.ACK:
                            max_fragment_size = size

                            print("Fragment size changed successfully")

                            break
                        elif received_ack.msg_type == MessageType.NACK:
                            print("Fragment size change request was not received correctly. Resending...")

                            s.sendto(msg.serialize(), (ip, port))
                    except socket.timeout:
                        print("Timeout occurred while waiting for fragment size change acknowledgement. Resending...")

                        s.sendto(msg.serialize(), (ip, port))
            except ValueError:
                print("The value is invalid! Try again")
        elif mode == "3":
            msg = Message(0, MessageType.SWITCH_NODES)

            s.sendto(msg.serialize(), (ip, port))

            print("Node switch requested")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print("Starting the switch")
                        # client_switch()
                        # server_switch()

                        break
                except socket.timeout:
                    print("Timeout occurred while waiting for switch request acknowledgement. Resending...")

                    s.sendto(msg.serialize(), (ip, port))

            alive = False

            break
        elif mode == "4":
            file_err_simulation_mode = not file_err_simulation_mode

            print(f"The file transfer error simulation mode is now {'on' if file_err_simulation_mode else 'off'}!")
        else:
            print("Invalid input! Please try again!")


def keep_alive():
    global server_ip, server_port, data_transferred, alive

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while alive:
        if not data_transferred:
            s.sendto(Message(0, MessageType.KEEP_ALIVE).serialize(), (server_ip, server_port))

            try:
                s.settimeout(10)
                ack, _ = s.recvfrom(1024)
                received_ack = Message.deserialize(ack)

                if received_ack.msg_type == MessageType.ACK:
                    time.sleep(10)
            except socket.timeout:
                print("Timeout occurred while waiting for keep-alive acknowledgement. Waiting...")
                s.sendto(Message(0, MessageType.TIMEOUT).serialize(), (server_ip, server_port))
        else:
            time.sleep(10)

    s.close()


def client_switch():
    global client_ip, client_port, server_port, server_ip

    client_port, server_port = server_port, client_port
    client_ip, server_ip = server_ip, client_ip


def client():
    global alive, server_ip, server_port

    while True:
        try:
            ip = input("Enter the server IP address: ").strip()

            ipaddress.IPv4Address(ip)

            server_ip = ip

            port = input("Enter the server port: ").strip()

            try:
                if 0 <= int(port) <= 65535:
                    server_port = int(port)

                    alive = True

                    sender_thread = threading.Thread(target=send, args=(server_ip, server_port))
                    keep_alive_thread = threading.Thread(target=keep_alive)

                    sender_thread.start()
                    keep_alive_thread.start()

                    sender_thread.join()
                    keep_alive_thread.join()

                    break
                else:
                    raise ValueError()
            except ValueError:
                print("The port is invalid! Try again!")
        except ipaddress.AddressValueError:
            print("The address is invalid! Try again!")
