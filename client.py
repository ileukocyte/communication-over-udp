import ipaddress
import os.path
import random
import socket
import threading
import time
import zlib

# from messages import Message, MessageType
from test2 import Message, MessageType

client_ip = None
client_port = None

server_ip = None
server_port = None

max_fragment_size = 64

data_transferred = False
alive = True

file_err_simulation_mode = False

receiver_mode = False
current_name = None
current_data = []

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send():
    global alive, max_fragment_size, data_transferred, client_ip, client_port, server_port, server_ip, file_err_simulation_mode
    global s, receiver_mode, current_name, current_data

    if not receiver_mode:
        init_msg = Message(0, MessageType.INIT)
        s.sendto(init_msg.serialize(), (server_ip, server_port))

        print("Connection init requested")

        while True:
            try:
                s.settimeout(10)
                ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                received_ack = Message.deserialize(ack)

                if received_ack.msg_type == MessageType.ACK:
                    addr = received_ack.data.decode().split("|")

                    client_ip = addr[0]
                    client_port = int(addr[1])

                    print("Connection successfully initialized")
                    print(f"Client address is {client_ip}:{client_port}")

                    break
            except socket.timeout:
                print("Timeout occurred while waiting for acknowledgement of connection init. Resending...")
                s.sendto(init_msg.serialize(), (server_ip, server_port))

        while not receiver_mode:
            try:
                print("Select the mode or type in \"EXIT\" to terminate the session:")
                print("1. Transfer a file")
                print("2. Set the maximum fragment size")
                print("3. Switch the nodes")
                print(f"4. Turn the file transfer error simulation mode {'on' if not file_err_simulation_mode else 'off'}")
                print("5. Send a text message")

                mode = input().strip().upper()

                if mode == "EXIT":
                    fin_msg = Message(0, MessageType.FIN)

                    s.sendto(fin_msg.serialize(), (server_ip, server_port))

                    print("Connection termination requested")

                    while True:
                        try:
                            s.settimeout(10)
                            ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                            received_ack = Message.deserialize(ack)

                            if received_ack.msg_type == MessageType.ACK:
                                print("Connection successfully terminated")

                                s.close()

                                alive = False

                                break
                        except socket.timeout:
                            print("Timeout occurred while waiting for acknowledgement of connection termination")

                            s.sendto(fin_msg.serialize(), (server_ip, server_port))

                    break
                elif mode == "1":
                    path = input("Enter your file path: ")

                    if not os.path.exists(path):
                        print("The path is invalid! Try again")

                        continue

                    data_transferred = True

                    msg = Message(0, MessageType.FILE_PATH, path.encode())

                    s.sendto(msg.serialize(), (server_ip, server_port))

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

                                s.sendto(msg.serialize(), (server_ip, server_port))
                        except socket.timeout:
                            print("Timeout occurred while waiting for file path acknowledgement")

                            s.sendto(msg.serialize(), (server_ip, server_port))

                    with open(path, "rb") as file:
                        content = file.read()
                        fragments = [content[i:i + max_fragment_size] for i in range(0, len(content), max_fragment_size)]

                        count_msg = Message(0, MessageType.FRAGMENT_COUNT, f"{len(fragments)}".encode())

                        s.sendto(count_msg.serialize(), (server_ip, server_port))

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

                                    s.sendto(count_msg.serialize(), (server_ip, server_port))
                            except socket.timeout:
                                print("Timeout occurred while waiting for fragment count acknowledgement. Resending...")

                                s.sendto(count_msg.serialize(), (server_ip, server_port))

                        window_size = 4
                        base = 0
                        next_frag_num = 0

                        rnd_frag_num = random.randrange(0, len(fragments))

                        # Go-Back-N
                        while base < len(fragments):
                            while next_frag_num < min(base + window_size, len(fragments)):
                                fragment = fragments[next_frag_num]

                                msg = Message(next_frag_num, MessageType.DATA, fragment) if not file_err_simulation_mode or next_frag_num != rnd_frag_num else (
                                    Message(next_frag_num, MessageType.DATA, fragment, checksum=0)
                                )

                                # In order so that the corrupted fragment would be sent correctly next time
                                if next_frag_num == rnd_frag_num:
                                    rnd_frag_num = -1

                                s.sendto(msg.serialize(), (server_ip, server_port))

                                next_frag_num += 1

                            try:
                                s.settimeout(16)

                                while True:
                                    ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                                    received_ack = Message.deserialize(ack)

                                    if received_ack.msg_type == MessageType.ACK and received_ack.frag_num >= base:
                                        print(f"Acknowledgement received for fragment {received_ack.frag_num}")

                                        base = received_ack.frag_num + 1

                                        break
                                    elif received_ack.msg_type == MessageType.ACK_AND_SWITCH and received_ack.frag_num >= base:
                                        print(f"Acknowledgement received for fragment {received_ack.frag_num}")

                                        base = received_ack.frag_num + 1

                                        while True:
                                            print("The server asks if you would like to switch the roles:")
                                            print("1. Yes")
                                            print("2. No")

                                            mode = input().strip().upper()

                                            if mode == "1":
                                                s.sendto(Message(0, MessageType.ACK).serialize(), (server_ip, server_port))

                                                data_transferred = False
                                                receiver_mode = True

                                                break
                                            elif mode == "2":
                                                s.sendto(Message(0, MessageType.NACK).serialize(), (server_ip, server_port))

                                                data_transferred = False

                                                break
                                            else:
                                                print("Invalid input! Please try again!")

                                        break
                                    else:
                                        next_frag_num = base = received_ack.frag_num

                                        print("Invalid or no acknowledgement received. Resending the window...")

                                        break
                            except socket.timeout:
                                next_frag_num = base = received_ack.frag_num

                                print("Timeout occurred while waiting for acknowledgement. Resending the window...")
                elif mode == "2":
                    try:
                        size = int(input("Enter your size in bytes: "))

                        if size < 1:
                            raise ValueError

                        msg = Message(0, MessageType.CHANGE_MAX_FRAGMENT_SIZE, f'{size}'.encode())

                        s.sendto(msg.serialize(), (server_ip, server_port))

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

                                    s.sendto(msg.serialize(), (server_ip, server_port))
                            except socket.timeout:
                                print("Timeout occurred while waiting for fragment size change acknowledgement. Resending...")

                                s.sendto(msg.serialize(), (server_ip, server_port))
                    except ValueError:
                        print("The value is invalid! Try again")
                elif mode == "3":
                    msg = Message(0, MessageType.SWITCH_NODES)

                    s.sendto(msg.serialize(), (server_ip, server_port))

                    print("Node switch requested")

                    while True:
                        try:
                            s.settimeout(10)
                            ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                            received_ack = Message.deserialize(ack)

                            if received_ack.msg_type == MessageType.ACK:
                                print("Starting the switch")

                                break
                        except socket.timeout:
                            print("Timeout occurred while waiting for switch request acknowledgement. Resending...")

                            s.sendto(msg.serialize(), (server_ip, server_port))

                    receiver_mode = True

                    break
                elif mode == "4":
                    file_err_simulation_mode = not file_err_simulation_mode

                    print(f"The file transfer error simulation mode is now {'on' if file_err_simulation_mode else 'off'}!")
                elif mode == "5":
                    data_transferred = True

                    message = input("Enter your message: ")

                    fragments = [message[i:i + max_fragment_size] for i in range(0, len(message), max_fragment_size)]

                    rnd_frag_num = random.randrange(0, len(fragments))

                    count_msg = Message(0, MessageType.FRAGMENT_COUNT, f"{len(fragments)}".encode())

                    s.sendto(count_msg.serialize(), (server_ip, server_port))

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

                                s.sendto(count_msg.serialize(), (server_ip, server_port))
                        except socket.timeout:
                            print("Timeout occurred while waiting for fragment count acknowledgement. Resending...")

                            s.sendto(count_msg.serialize(), (server_ip, server_port))

                    for i, fragment in enumerate(fragments):
                        msg = Message(i, MessageType.TEXT, fragment.encode()) if not file_err_simulation_mode or i != rnd_frag_num else (
                            Message(i, MessageType.TEXT, fragment.encode(), checksum=0)
                        )

                        s.sendto(msg.serialize(), (server_ip, server_port))

                        while True:
                            try:
                                s.settimeout(100)
                                ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                                received_ack = Message.deserialize(ack)

                                if received_ack.msg_type == MessageType.ACK:
                                    print(f"Acknowledgement received for fragment {received_ack.frag_num}")

                                    break
                                elif received_ack.msg_type == MessageType.ACK_AND_SWITCH:
                                    print(f"Acknowledgement received for fragment {received_ack.frag_num}")

                                    while True:
                                        print("The server asks if you would like to switch the roles:")
                                        print("1. Yes")
                                        print("2. No")

                                        mode = input().strip().upper()

                                        if mode == "1":
                                            s.sendto(Message(0, MessageType.ACK).serialize(), (server_ip, server_port))

                                            data_transferred = False
                                            receiver_mode = True

                                            break
                                        elif mode == "2":
                                            s.sendto(Message(0, MessageType.NACK).serialize(), (server_ip, server_port))

                                            data_transferred = False

                                            break
                                        else:
                                            print("Invalid input! Please try again!")

                                    break
                                else:
                                    msg = Message(i, MessageType.TEXT, fragment.encode())

                                    print("The message was not received correctly. Resending...")

                                    s.sendto(msg.serialize(), (server_ip, server_port))
                            except socket.timeout:
                                msg = Message(i, MessageType.TEXT, fragment.encode())

                                print("Timeout occurred while waiting for message acknowledgement. Resending...")

                                s.sendto(msg.serialize(), (server_ip, server_port))
                else:
                    print("Invalid input! Please try again!")
            except socket.error:
                while True:
                    try:
                        reinit_msg = Message(0, MessageType.INIT)
                        s.sendto(reinit_msg.serialize(), (server_ip, server_port))

                        print("Connection re-init requested")

                        try:
                            s.settimeout(10)
                            ack, _ = s.recvfrom(max(1024, max_fragment_size + 8))
                            received_ack = Message.deserialize(ack)

                            if received_ack.msg_type == MessageType.ACK:
                                addr = received_ack.data.decode().split("|")

                                client_ip = addr[0]
                                client_port = int(addr[1])

                                print("Connection successfully re-initialized")
                                print(f"Client address is {client_ip}:{client_port}")

                                data_transferred = False

                                break
                        except socket.timeout:
                            print("Timeout occurred while waiting for acknowledgement of connection re-init. Resending...")

                            s.sendto(reinit_msg.serialize(), (server_ip, server_port))
                    except socket.error:
                        print("Error occurred while trying to re-initialize the connection. Waiting...")

                        time.sleep(10)

        if receiver_mode:
            s.settimeout(None)
            client_switch()
            send()
    else:
        expected_frag_num = 0

        print(f"Server address is {server_ip}:{server_port}")

        while receiver_mode:
            data, addr = s.recvfrom(max(1024, max_fragment_size + 8))
            msg = Message.deserialize(data)

            if msg.msg_type == MessageType.INIT:
                client_ip = addr[0]
                client_port = addr[1]

                print(f"Connection init received from {client_ip}:{client_port}")

                s.sendto(Message(0, MessageType.ACK, f"{client_ip}|{client_port}".encode()).serialize(), addr)

                print("Connection init acknowledged")

                # default
                max_fragment_size = 64
                expected_frag_num = 0
                current_name = None
                current_data = []
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

                receiver_mode = False

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
                            current_data = []

                            expected_frag_num = 0
                else:
                    print(f"Fragment {msg.frag_num} was not received correctly ({expected_frag_num} expected)")

                    s.sendto(Message(msg.frag_num, MessageType.NACK).serialize(), addr)

                    print(f"Negative acknowledgement sent for {msg.frag_num}")
            elif msg.msg_type == MessageType.ACK:
                print("Node switch request acknowledged")
                receiver_mode = False
            elif msg.msg_type == MessageType.NACK:
                print("Negative acknowledgement sent for node switch request")
            elif msg.msg_type == MessageType.TEXT:
                byte_data = msg.data

                if msg.checksum == zlib.crc32(byte_data):
                    current_data[msg.frag_num] = byte_data

                    print(f"Fragment {msg.frag_num} received: {byte_data.decode()}")

                    msg_type = MessageType.ACK_AND_SWITCH if msg.frag_num == len(current_data) - 1 else MessageType.ACK

                    s.sendto(Message(msg.frag_num, msg_type).serialize(), addr)

                    print(f"Fragment {msg.frag_num} acknowledged")

                    if msg.frag_num == len(current_data) - 1:
                        print(b"".join(current_data))

                        current_data = []
                else:
                    print(f"Fragment {msg.frag_num} was not received correctly")

                    s.sendto(Message(msg.frag_num, MessageType.NACK).serialize(), addr)

                    print(f"Negative acknowledgement sent for {msg.frag_num}")

        if not receiver_mode:
            s.settimeout(None)
            client_switch()
            send()


def keep_alive():
    global server_ip, server_port, data_transferred, alive

    s_ka = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while alive:
        time.sleep(10)

        if not data_transferred and not receiver_mode:
            try:
                s_ka.sendto(Message(0, MessageType.KEEP_ALIVE).serialize(), (server_ip, server_port))

                try:
                    s_ka.settimeout(10)
                    ack, _ = s_ka.recvfrom(1024)
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        continue
                except socket.timeout:
                    print("Timeout occurred while waiting for keep-alive acknowledgement. Waiting...")

                    s_ka.sendto(Message(0, MessageType.TIMEOUT).serialize(), (server_ip, server_port))
            except socket.error:
                print("Error occurred while trying to receive keep-alive acknowledgement. Waiting...")

    s_ka.settimeout(None)
    s_ka.close()


def client_switch():
    global client_ip, client_port, server_port, server_ip

    client_port, server_port = server_port, client_port
    client_ip, server_ip = server_ip, client_ip


def client():
    global alive, server_ip, server_port, s

    while True:
        try:
            ip = input("Enter the server IP address: ").strip()

            ipaddress.IPv4Address(ip)

            server_ip = ip

            port = input("Enter the server port: ").strip()

            try:
                if 0 <= int(port) <= 65535:
                    server_port = int(port)

                    if not alive:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                        alive = True

                    sender_thread = threading.Thread(target=send)
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
