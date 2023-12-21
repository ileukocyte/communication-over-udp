from client import client
from server import server

# 1. The node switching logic sucks since it's based on lots of code duplication
# 2. The server side has no adequate option to terminate the session for now except for stopping the process
# 3. No optimal ARQ has been implemented even though I intended to use Go-Back-N instead of Stop and Wait
# 4. The timeout system is not completely implemented
#    (the client will be continuously resending messages unless manually terminated)
if __name__ == "__main__":
    while True:
        print("Select the mode or type in \"EXIT\" to terminate the session:")
        print("1. Server")
        print("2. Client")

        mode = input().strip().upper()

        if mode == "EXIT":
            break
        elif mode == "1":
            server()
        elif mode == "2":
            client()
        else:
            print("Invalid input! Please try again!")
