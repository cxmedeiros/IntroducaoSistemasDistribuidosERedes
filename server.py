import socket
import struct
import os

SUPPORTED = {
    ("txt", "pdf"),
    ("png", "jpg"),
    ("wav", "mp3")
}

def convert_file(input_path, output_path, src, dst):
    # Coloque aqui a lógica real usando bibliotecas (Pillow, FPDF, pydub, etc.)
    # O exemplo abaixo só copia o arquivo pra simular a conversão.
    with open(input_path, "rb") as src_f:
        data = src_f.read()

    with open(output_path, "wb") as dst_f:
        dst_f.write(data)

def handle_client(conn):
    req = conn.recv(1024).decode().strip()
    print("Recebido:", req)

    if not req.startswith("CONVERT"):
        conn.sendall(b"ERROR invalid_command")
        return

    _, src, dst, filename = req.split()

    if (src, dst) not in SUPPORTED:
        conn.sendall(b"ERROR unsupported_format")
        return

    conn.sendall(b"OK")

    # Recebe tamanho do arquivo
    raw_size = conn.recv(8)
    (size,) = struct.unpack("!Q", raw_size)

    content = b""
    while len(content) < size:
        content += conn.recv(4096)

    input_path = f"temp_{filename}"
    with open(input_path, "wb") as f:
        f.write(content)

    output_path = f"converted_{filename}.{dst}"

    convert_file(input_path, output_path, src, dst)

    result_data = open(output_path, "rb").read()
    conn.sendall(struct.pack("!Q", len(result_data)))
    conn.sendall(result_data)

    os.remove(input_path)
    os.remove(output_path)

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5050))
    server.listen()

    print("Servidor aguardando conexões na porta 5050...")

    while True:
        conn, addr = server.accept()
        print("Cliente conectado:", addr)
        handle_client(conn)
        conn.close()

if __name__ == "__main__":
    main()
