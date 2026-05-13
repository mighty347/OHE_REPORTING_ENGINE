import socket

def test_connection(host, port):
    try:
        with socket.create_connection((host, port), timeout=5):
            print(f"Successfully connected to {host}:{port}")
    except Exception as e:
        print(f"Failed to connect to {host}:{port}: {e}")

if __name__ == "__main__":
    test_connection("192.168.1.56", 6011)
