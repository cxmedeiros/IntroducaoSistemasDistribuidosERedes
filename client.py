import socket
import struct
import os

def send_file_and_receive(server, src, dst, filename):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(server)

    req = f"CONVERT {src} {dst} {filename}"
    s.sendall(req.encode())

    resp = s.recv(1024).decode()
    if not resp.startswith("OK"):
        print("Erro do servidor:", resp)
        return

    data = open(filename, "rb").read()

    s.sendall(struct.pack("!Q", len(data)))
    s.sendall(data)

    raw_size = s.recv(8)
    (size,) = struct.unpack("!Q", raw_size)

    result = b""
    while len(result) < size:
        result += s.recv(4096)

    output_name = f"resultado.{dst}"
    with open(output_name, "wb") as f:
        f.write(result)

    print("Arquivo salvo como:", output_name)

    s.close()

if __name__ == "__main__":
    send_file_and_receive(("127.0.0.1", 5050), "txt", "pdf", "arquivo.txt")
