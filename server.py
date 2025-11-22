import socket
import struct
import os
from fpdf import FPDF

SUPPORTED = {
    ("txt", "pdf")
}

def txt_to_pdf(input_path, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Lê o .txt linha a linha e escreve no PDF
    # encoding='utf-8' funciona bem para textos com acentos
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # rstrip() tira quebras de linha pra não ficar linha em branco dupla
            pdf.multi_cell(0, 8, line.rstrip("\n"))

    pdf.output(output_path)

def convert_file(input_path, output_path, src, dst):
    # Aqui você pode checar explicitamente o tipo, se quiser
    if (src, dst) == ("txt", "pdf"):
        txt_to_pdf(input_path, output_path)
    else:
        # Em teoria não deveria cair aqui porque o SUPPORTED já filtra
        raise ValueError(f"Conversão não suportada: {src} -> {dst}")

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
