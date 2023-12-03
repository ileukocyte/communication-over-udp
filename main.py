from client import client
from server import server

if __name__ == '__main__':
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
