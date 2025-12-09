import socket
import struct
import os

def send_file_and_receive(server, src, dst, filename):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(server) #abre a conexao com o servidor no endereco e porta especificados

    req = f"CONVERT {src} {dst} {filename}" #Monta a string de comando no protocolo combinado
    s.sendall(req.encode()) #envia o comando para o servidor

    resp = s.recv(1024).decode() #lê até 1024 bytes que o servidor mandar de resposta
    if not resp.startswith("OK"): #verifica se a resposta é OK
        print("Erro do servidor:", resp)
        return

    data = open(filename, "rb").read() #Abre filename (ex.: arquivo.txt) em modo binário ("rb") e lê tudo pra memória.

    s.sendall(struct.pack("!Q", len(data))) #envia o tamanho do arquivo como um inteiro sem sinal de 8 bytes em ordem de rede
    s.sendall(data)

    raw_size = s.recv(8) #lê os próximos 8 bytes que indicam o tamanho do arquivo convertido
    (size,) = struct.unpack("!Q", raw_size)

    result = b""
    while len(result) < size: #lê o arquivo convertido em pedaços de até 4096 bytes
        result += s.recv(4096)

    output_name = f"resultado.{dst}" #Salva o arquivo convertido com o nome resultado.pdf (se dst for pdf)
    with open(output_name, "wb") as f:
        f.write(result)

    print("Arquivo salvo como:", output_name)

    s.close()

if __name__ == "__main__":
    send_file_and_receive(("127.0.0.1", 5050), "txt", "pdf", "arquivo.txt") 