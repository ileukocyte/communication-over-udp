import os.path
import socket
import sys
import threading
import time

# from messages import Message, MessageType
from test2 import Message, MessageType
from server import server, server_switch

CLIENT_IP = "192.168.0.179"  # "127.0.0.1"
CLIENT_PORT = 50602
SERVER_IP = "192.168.0.115"  # "127.0.0.1"
SERVER_PORT = 50601

max_fragment_size = 50
data_transferred = False
alive = True


def send(ip, port):
    global alive, max_fragment_size, data_transferred, CLIENT_IP, CLIENT_PORT, SERVER_PORT, SERVER_IP

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    init_msg = Message(0, MessageType.INIT)
    s.sendto(init_msg.serialize(), (ip, port))
    print(f"Connection init sent")

    while True:
        try:
            s.settimeout(10)
            ack, _ = s.recvfrom(1024)
            received_ack = Message.deserialize(ack)

            if received_ack.msg_type == MessageType.ACK:
                print(f"Connection initialized")
                break
        except socket.timeout:
            print(f"Timeout occurred while waiting for acknowledgment of connection init. Resending...")
            s.sendto(init_msg.serialize(), (ip, port))

    while True:
        print('Select the mode or type in "EXIT" to terminate the session:')
        print('1. Transfer a file')
        print('2. Set the maximum fragment size')
        print('3. Switch the nodes')
        print('4. Send a text message')

        mode = input().strip().upper()

        if mode == 'EXIT':
            fin_msg = Message(0, MessageType.FIN)
            s.sendto(fin_msg.serialize(), (ip, port))
            print(f"Connection termination sent")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(1024)
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print(f"Connection terminated")

                        sys.exit()
                except socket.timeout:
                    print(f"Timeout occurred while waiting for acknowledgment of connection termination")
                    s.sendto(fin_msg.serialize(), (ip, port))
        elif mode == '1':
            path = input("Enter your file path: ")

            if not os.path.exists(path):
                print('The path is invalid! Try again')

                continue

            data_transferred = True

            msg = Message(0, MessageType.FILE_PATH, path.encode())

            s.sendto(msg.serialize(), (ip, port))
            print(f"File path sent: {path}")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(1024)
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print(f"File path sent successfully.")
                        break
                    elif received_ack.msg_type == MessageType.NACK:
                        print(f"File path was not received correctly. Resending...")
                        s.sendto(msg.serialize(), (ip, port))
                except socket.timeout:
                    print(f"Timeout occurred while waiting for acknowledgment of file path")
                    s.sendto(msg.serialize(), (ip, port))

            with open(path, 'rb') as file:
                content = file.read()
                fragments = [content[i:i + max_fragment_size] for i in range(0, len(content), max_fragment_size)]

                count_msg = Message(0, MessageType.FRAGMENT_COUNT, f'{len(fragments)}'.encode())

                s.sendto(count_msg.serialize(), (ip, port))
                print(f"Fragment count ({len(fragments)}) sent")

                while True:
                    try:
                        s.settimeout(10)
                        ack, _ = s.recvfrom(1024)
                        received_ack = Message.deserialize(ack)

                        if received_ack.msg_type == MessageType.ACK:
                            print(f"Fragment count sent successfully.")
                            break
                        elif received_ack.msg_type == MessageType.NACK:
                            print(f"Fragment count was not received correctly. Resending...")
                            s.sendto(count_msg.serialize(), (ip, port))
                    except socket.timeout:
                        print(f"Timeout occurred while waiting for acknowledgment of fragment count. Resending...")
                        s.sendto(count_msg.serialize(), (ip, port))

                window_size = 4
                base = 0
                next_sequence_number = 0

                # Send fragments to the receiver using Go-Back-N
                while base < len(fragments):
                    for i in range(base, min(base + window_size, len(fragments))):
                        fragment = fragments[i]
                        msg = Message(i, MessageType.DATA, fragment)
                        s.sendto(msg.serialize(), (ip, port))
                        next_sequence_number += 1

                    s.settimeout(10)

                    try:
                        while True:
                            ack, _ = s.recvfrom(1024)
                            received_ack = Message.deserialize(ack)
                            if received_ack.msg_type == MessageType.ACK and received_ack.fragment_number == base:
                                print(f"Acknowledgment received for fragment {base}.")

                                base += 1

                                break
                            elif received_ack.msg_type == MessageType.ACK_AND_SWITCH and received_ack.fragment_number == base:
                                while True:
                                    print('The server asks if you would like to switch the roles:')
                                    print('1. Yes')
                                    print('2. No')

                                    mode = input().strip().upper()

                                    if mode == '1':
                                        s.sendto(Message(0, MessageType.ACK).serialize(), (ip, port))
                                        data_transferred = False
                                        break
                                    elif mode == '2':
                                        s.sendto(Message(0, MessageType.NACK).serialize(), (ip, port))
                                        data_transferred = False
                                        break
                                    else:
                                        print('Invalid input! Please try again!')
                            else:
                                print("Invalid or no acknowledgment received. Resending the window...")
                                break
                    except socket.timeout:
                        print("Timeout occurred while waiting for acknowledgment. Resending the window...")
        elif mode == '2':
            try:
                size = int(input("Enter your size in bytes: "))

                if size < 1:
                    raise ValueError

                msg = Message(0, MessageType.CHANGE_MAX_FRAGMENT_SIZE, f'{size}'.encode())

                s.sendto(msg.serialize(), (ip, port))
                print(f"Max fragment size ({size}) sent")

                while True:
                    try:
                        s.settimeout(10)
                        ack, _ = s.recvfrom(1024)
                        received_ack = Message.deserialize(ack)

                        if received_ack.msg_type == MessageType.ACK:
                            max_fragment_size = size
                            print(f"Fragment size changed successfully.")
                            break
                        elif received_ack.msg_type == MessageType.NACK:
                            print(f"Fragment size change request was not received correctly. Resending...")
                            s.sendto(msg.serialize(), (ip, port))
                    except socket.timeout:
                        print(f"Timeout occurred while waiting for acknowledgment of fragment size change. Resending...")
                        s.sendto(msg.serialize(), (ip, port))
            except ValueError:
                print('The value is invalid! Try again')
        elif mode == '3':
            msg = Message(0, MessageType.SWITCH_NODES)

            s.sendto(msg.serialize(), (ip, port))
            print(f"Switch request sent")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(1024)
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print(f"Starting the switch.")
                        # CLIENT_IP, SERVER_IP = SERVER_IP, CLIENT_IP
                        # CLIENT_PORT, SERVER_PORT = SERVER_PORT, CLIENT_PORT
                        # server_switch()

                        break
                except socket.timeout:
                    print(f"Timeout occurred while waiting for acknowledgment of the switch request. Resending...")
                    s.sendto(msg.serialize(), (ip, port))

            alive = False
            break
        elif mode == '4':
            message = input("Enter your message: ").encode()

            data_transferred = True

            fragments = [message[i:i + max_fragment_size] for i in range(0, len(message), max_fragment_size)]

            count_msg = Message(0, MessageType.FRAGMENT_COUNT, f'{len(fragments)}'.encode())

            s.sendto(count_msg.serialize(), (ip, port))
            print(f"Fragment count ({len(fragments)}) sent")

            while True:
                try:
                    s.settimeout(10)
                    ack, _ = s.recvfrom(1024)
                    received_ack = Message.deserialize(ack)

                    if received_ack.msg_type == MessageType.ACK:
                        print(f"Fragment count sent successfully.")
                        break
                    elif received_ack.msg_type == MessageType.NACK:
                        print(f"Fragment count was not received correctly. Resending...")
                        s.sendto(count_msg.serialize(), (ip, port))
                except socket.timeout:
                    print(f"Timeout occurred while waiting for acknowledgment of fragment count. Resending...")
                    s.sendto(count_msg.serialize(), (ip, port))

            for i, fragment in enumerate(fragments):
                msg = Message(i, MessageType.TEST_MSG, fragment)
                s.sendto(msg.serialize(), (ip, port))
                print(f"Sent: fragment {i}")

                while True:
                    try:
                        s.settimeout(10)
                        ack, _ = s.recvfrom(1024)
                        received_ack = Message.deserialize(ack)
                        if received_ack.msg_type == MessageType.ACK and received_ack.fragment_number == i:
                            print(f"Fragment {i} sent successfully.")
                            break
                        elif received_ack.msg_type == MessageType.NACK and received_ack.fragment_number == i:
                            print(f"Fragment {i} was not received correctly. Resending...")
                            s.sendto(msg.serialize(), (ip, port))
                        elif received_ack.msg_type == MessageType.ACK_AND_SWITCH and received_ack.fragment_number == i:
                            while True:
                                print('The server asks if you would like to switch the roles:')
                                print('1. Yes')
                                print('2. No')

                                mode = input().strip().upper()

                                if mode == '1':
                                    s.sendto(Message(0, MessageType.ACK).serialize(), (ip, port))
                                    data_transferred = False
                                    break
                                elif mode == '2':
                                    s.sendto(Message(0, MessageType.NACK).serialize(), (ip, port))
                                    data_transferred = False
                                    break
                                else:
                                    print('Invalid input! Please try again!')
                            break
                    except socket.timeout:
                        print(f"Timeout occurred while waiting for acknowledgment of fragment {i}. Resending...")
                        s.sendto(msg.serialize(), (ip, port))
        else:
            print('Invalid input! Please try again!')

    server()


def keep_alive():
    global SERVER_IP, SERVER_PORT, data_transferred, alive

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    timeout_occurred = False

    while alive:
        if not data_transferred:
            s.sendto(Message(0, MessageType.KEEP_ALIVE).serialize(), (SERVER_IP, SERVER_PORT))

            try:
                s.settimeout(10)
                ack, _ = s.recvfrom(1024)
                received_ack = Message.deserialize(ack)

                if received_ack.msg_type == MessageType.ACK:
                    time.sleep(10)
            except socket.timeout:
                print(f"Timeout occurred while waiting for acknowledgment of keep-alive. Terminating...")
                s.sendto(Message(0, MessageType.TIMEOUT).serialize(), (SERVER_IP, SERVER_PORT))
                timeout_occurred = True
                break
        else:
            time.sleep(10)

    if timeout_occurred and alive:
        while True:
            print('Select the mode or type in "EXIT" to terminate the session:')
            print('1. Server')
            print('2. Client')

            mode = input().strip().upper()

            if mode == 'EXIT':
                break
            elif mode == '1':
                server()
            elif mode == '2':
                client()
            else:
                print('Invalid input! Please try again!')


def client():
    sender_thread = threading.Thread(target=send, args=(SERVER_IP, SERVER_PORT))
    keep_alive_thread = threading.Thread(target=keep_alive)

    sender_thread.start()
    keep_alive_thread.start()

    sender_thread.join()
    keep_alive_thread.join()
