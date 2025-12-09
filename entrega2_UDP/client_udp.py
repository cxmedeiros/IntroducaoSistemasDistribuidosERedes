"""
Cliente UDP para conversão de arquivos.
Implementa transferência confiável sobre UDP com:
- Fragmentação de arquivos em pacotes
- ACK para cada pacote
- Timeout e retransmissão
- Verificação de integridade com SHA256
"""

import socket
import struct
import os
import sys
import hashlib
import time

# Tamanho máximo de dados por pacote (excluindo header)
CHUNK_SIZE = 1024

# Tamanho do header: tipo(1) + packet_id(4) + total_packets(4) = 9 bytes
HEADER_SIZE = 9

# Tamanho máximo do pacote completo
MAX_PACKET_SIZE = HEADER_SIZE + CHUNK_SIZE

# Timeout para receber ACK (segundos)
ACK_TIMEOUT = 2.0

# Número máximo de retransmissões
MAX_RETRIES = 5

# Configuração do servidor
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5051

# Diretório local para salvar os arquivos convertidos
OUTPUT_DIR = "resultados_client"

PKT_COMMAND = 0x01      # Comando inicial (CONVERT ...)
PKT_METADATA = 0x02     # Metadados do arquivo (nome, tamanho, total_pacotes)
PKT_DATA = 0x03         # Dados do arquivo
PKT_HASH = 0x04         # Hash SHA256 do arquivo
PKT_ACK = 0x05          # Confirmação de recebimento
PKT_NACK = 0x06         # Erro / Negação
PKT_OK = 0x07           # Confirmação de comando válido
PKT_ERROR = 0x08        # Mensagem de erro
PKT_COMPLETE = 0x09     # Transferência completa

def ensure_output_dir():
    """Garante que o diretório de saída existe."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def calculate_sha256(data):
    """Calcula o hash SHA256 dos dados."""
    return hashlib.sha256(data).hexdigest()


def print_help():
    """Exibe ajuda sobre os comandos disponíveis."""
    print("\n\n")
    print("COMANDOS DISPONÍVEIS:")
    print("\n\n")
    print("  CONVERT <formato_origem> <formato_destino> <arquivo>")
    print("")
    print("  Conversões suportadas:")
    print("    - txt  -> pdf  (texto para PDF)")
    print("    - jpeg -> png  (imagem JPEG para PNG)")
    print("    - jpg  -> png  (imagem JPG para PNG)")
    print("")
    print("  Exemplos:")
    print("    CONVERT .txt .pdf meuarquivo.txt")
    print("    CONVERT txt pdf meuarquivo.txt")
    print("    CONVERT .jpeg .png imagem.jpeg")
    print("    CONVERT jpg png foto.jpg")
    print("")
    print("  HELP - Exibe esta mensagem de ajuda")
    print("  EXIT - Encerra o cliente")

def create_packet(pkt_type, packet_id, total_packets, data=b""):
    """
    Cria um pacote com header + dados.
    Header: tipo(1 byte) + packet_id(4 bytes) + total_packets(4 bytes)
    """
    header = struct.pack("!BII", pkt_type, packet_id, total_packets)
    return header + data


def parse_packet(packet):
    """
    Parseia um pacote recebido.
    Retorna: (tipo, packet_id, total_packets, dados)
    """
    if len(packet) < HEADER_SIZE:
        return None, None, None, None
    
    header = packet[:HEADER_SIZE]
    data = packet[HEADER_SIZE:]
    pkt_type, packet_id, total_packets = struct.unpack("!BII", header)
    
    return pkt_type, packet_id, total_packets, data


def send_with_ack(sock, addr, packet, expected_ack_id, timeout=ACK_TIMEOUT, max_retries=MAX_RETRIES):
    """
    Envia um pacote e aguarda ACK. Retransmite se necessário.
    Retorna True se recebeu ACK, False caso contrário.
    """
    sock.settimeout(timeout)
    
    for attempt in range(max_retries):
        try:
            sock.sendto(packet, addr)
            
            # Aguarda ACK
            while True:
                try:
                    response, resp_addr = sock.recvfrom(MAX_PACKET_SIZE)
                    pkt_type, ack_id, _, _ = parse_packet(response)
                    
                    if pkt_type == PKT_ACK and ack_id == expected_ack_id:
                        return True
                    elif pkt_type == PKT_ERROR:
                        return False
                except socket.timeout:
                    break
                    
        except socket.timeout:
            print(f"    [Timeout] Tentativa {attempt + 1}/{max_retries} para pacote {expected_ack_id}")
    
    return False


def receive_with_ack(sock, server_addr, expected_type=None, timeout=10.0):
    """
    Recebe um pacote e envia ACK.
    Retorna: (tipo, packet_id, total_packets, dados) ou None se falhou.
    """
    sock.settimeout(timeout)
    
    try:
        packet, addr = sock.recvfrom(MAX_PACKET_SIZE)
        pkt_type, packet_id, total_packets, data = parse_packet(packet)
        
        if packet is None:
            return None, None, None, None
        
        # Envia ACK
        ack_packet = create_packet(PKT_ACK, packet_id, 0)
        sock.sendto(ack_packet, addr)
        
        return pkt_type, packet_id, total_packets, data
        
    except socket.timeout:
        return None, None, None, None

def convert_file(sock, server_addr, src, dst, filename):
    """
    Envia um arquivo para conversão e recebe o resultado.
    Retorna True se a conversão foi bem-sucedida, False caso contrário.
    """
    # Remove o ponto se o usuário digitou .txt .pdf
    src = src.lstrip(".")
    dst = dst.lstrip(".")
    
    # Verifica se o arquivo existe
    if not os.path.exists(filename):
        print(f"[ERRO] Arquivo '{filename}' não encontrado.")
        return False
    
    # Lê o arquivo
    with open(filename, "rb") as f:
        file_data = f.read()
    
    file_size = len(file_data)
    base_filename = os.path.basename(filename)
    
    # Calcula hash do arquivo
    file_hash = calculate_sha256(file_data)
    
    # Calcula total de pacotes
    total_packets = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    
    print(f"[INFO] Arquivo: {base_filename}")
    print(f"[INFO] Tamanho: {file_size} bytes")
    print(f"[INFO] Pacotes: {total_packets}")
    print(f"[INFO] Hash: {file_hash[:16]}...")
    
    #  ENVIA COMANDO 
    command = f"CONVERT {src} {dst} {base_filename}"
    cmd_pkt = create_packet(PKT_COMMAND, 0, 0, command.encode())
    
    sock.sendto(cmd_pkt, server_addr)
    
    # Aguarda resposta (OK com nova porta ou ERROR)
    sock.settimeout(5.0)
    try:
        response, resp_addr = sock.recvfrom(MAX_PACKET_SIZE)
        pkt_type, _, _, data = parse_packet(response)
        
        if pkt_type == PKT_ERROR:
            error_msg = data.decode()
            error_messages = {
                "comando_invalido": "Comando inválido",
                "formato_comando_invalido": "Formato do comando inválido",
                "formato_nao_suportado": "Formato de conversão não suportado"
            }
            print(f"[ERRO] {error_messages.get(error_msg, error_msg)}")
            return False
        
        if pkt_type == PKT_OK:
            # Extrai nova porta do servidor
            if len(data) >= 2:
                new_port = struct.unpack("!H", data[:2])[0]
                server_addr = (server_addr[0], new_port)
                print(f"[INFO] Redirecionado para porta {new_port}")
        
    except socket.timeout:
        print("[ERRO] Timeout aguardando resposta do servidor")
        return False
    
    # Aguarda segundo OK (confirmação do comando)
    try:
        response, resp_addr = sock.recvfrom(MAX_PACKET_SIZE)
        pkt_type, _, _, data = parse_packet(response)
        
        if pkt_type == PKT_ERROR:
            error_msg = data.decode()
            print(f"[ERRO] {error_msg}")
            return False
            
    except socket.timeout:
        print("[ERRO] Timeout aguardando confirmação")
        return False
    
    #  ENVIA METADADOS 
    metadata = f"{base_filename}|{file_size}|{total_packets}"
    meta_pkt = create_packet(PKT_METADATA, 0, total_packets, metadata.encode())
    
    if not send_with_ack(sock, server_addr, meta_pkt, 0):
        print("[ERRO] Falha ao enviar metadados")
        return False
    
    print("[INFO] Metadados enviados")
    
    #  ENVIA PACOTES DE DADOS 
    print(f"[INFO] Enviando arquivo...")
    
    for i in range(total_packets):
        start = i * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, file_size)
        chunk = file_data[start:end]
        
        data_pkt = create_packet(PKT_DATA, i, total_packets, chunk)
        
        if not send_with_ack(sock, server_addr, data_pkt, i):
            print(f"[ERRO] Falha ao enviar pacote {i}")
            return False
        
        # Progresso
        progress = (i + 1) / total_packets * 100
        print(f"    [Enviado] Pacote {i + 1}/{total_packets} ({progress:.1f}%)")
    
    #  ENVIA HASH 
    hash_pkt = create_packet(PKT_HASH, 0, 0, file_hash.encode())
    
    if not send_with_ack(sock, server_addr, hash_pkt, 0):
        print("[ERRO] Falha ao enviar hash")
        return False
    
    print("[INFO] Hash enviado. Aguardando conversão...")
    
    #  RECEBE RESULTADO 
    
    # Recebe metadados do resultado
    pkt_type, packet_id, total_result_packets, data = receive_with_ack(sock, server_addr, timeout=30.0)
    
    if pkt_type == PKT_ERROR:
        error_msg = data.decode()
        print(f"[ERRO] Erro no servidor: {error_msg}")
        return False
    
    if pkt_type != PKT_METADATA:
        print(f"[ERRO] Esperava metadados, recebeu tipo {pkt_type}")
        return False
    
    meta_parts = data.decode().split("|")
    if len(meta_parts) != 3:
        print("[ERRO] Metadados inválidos")
        return False
    
    result_filename, result_size, result_total_packets = meta_parts
    result_size = int(result_size)
    result_total_packets = int(result_total_packets)
    
    print(f"[INFO] Recebendo resultado: {result_filename}")
    print(f"[INFO] Tamanho: {result_size} bytes, Pacotes: {result_total_packets}")
    
    # Recebe pacotes de dados
    received_packets = {}
    
    while len(received_packets) < result_total_packets:
        pkt_type, packet_id, total_pkts, data = receive_with_ack(sock, server_addr, timeout=ACK_TIMEOUT * 2)
        
        if pkt_type == PKT_DATA:
            received_packets[packet_id] = data
            progress = len(received_packets) / result_total_packets * 100
            print(f"    [Recebido] Pacote {packet_id + 1}/{result_total_packets} ({progress:.1f}%)")
        elif pkt_type is None:
            # Timeout - alguns pacotes podem ter sido perdidos
            continue
    
    # Recebe hash
    pkt_type, _, _, hash_data = receive_with_ack(sock, server_addr, timeout=10.0)
    
    if pkt_type != PKT_HASH:
        print("[ERRO] Esperava hash do resultado")
        return False
    
    expected_hash = hash_data.decode()
    print(f"[INFO] Hash esperado: {expected_hash[:16]}...")
    
    # Reconstrói arquivo
    result_content = b""
    for i in range(result_total_packets):
        if i in received_packets:
            result_content += received_packets[i]
    
    result_content = result_content[:result_size]
    
    # Verifica hash
    calculated_hash = calculate_sha256(result_content)
    
    if calculated_hash != expected_hash:
        print("[ERRO] Hash do arquivo recebido não confere!")
        print(f"    Esperado:  {expected_hash}")
        print(f"    Calculado: {calculated_hash}")
        return False
    
    print("[INFO] Hash verificado com sucesso!")
    
    # Aguarda sinal de conclusão (opcional)
    sock.settimeout(2.0)
    try:
        response, _ = sock.recvfrom(MAX_PACKET_SIZE)
        pkt_type, _, _, _ = parse_packet(response)
        if pkt_type == PKT_COMPLETE:
            pass  # Conclusão confirmada
    except socket.timeout:
        pass  # Não é crítico
    
    # Salva arquivo
    ensure_output_dir()
    output_path = os.path.join(OUTPUT_DIR, result_filename)
    
    with open(output_path, "wb") as f:
        f.write(result_content)
    
    print(f"[SUCESSO] Arquivo convertido salvo em: {output_path}")
    return True

# MAIN

def main():
    ensure_output_dir()
    
    print("=" * 60)
    print("CLIENTE DE CONVERSÃO DE ARQUIVOS (UDP)")
    print("=" * 60)
    print(f"Servidor: {SERVER_HOST}:{SERVER_PORT}")
    print(f"Tamanho do chunk: {CHUNK_SIZE} bytes")
    print(f"Resultados serão salvos em: ./{OUTPUT_DIR}/")
    print_help()
    
    try:
        while True:
            try:
                user_input = input("\n> ").strip()
            except EOFError:
                break
            
            if not user_input:
                continue
            
            # Comando de ajuda
            if user_input.upper() == "HELP":
                print_help()
                continue
            
            # Comando de saída
            if user_input.upper() == "EXIT":
                print("[INFO] Encerrando cliente...")
                break
            
            # Comando de conversão
            if user_input.upper().startswith("CONVERT"):
                parts = user_input.split()
                if len(parts) != 4:
                    print("[ERRO] Formato incorreto. Use: CONVERT <origem> <destino> <arquivo>")
                    print("       Exemplo: CONVERT .txt .pdf meuarquivo.txt")
                    continue
                
                _, src, dst, filename = parts
                
                # Cria novo socket para cada conversão
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                server_addr = (SERVER_HOST, SERVER_PORT)
                
                try:
                    convert_file(sock, server_addr, src, dst, filename)
                except Exception as e:
                    print(f"[ERRO] Erro durante conversão: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    sock.close()
            else:
                print(f"[ERRO] Comando desconhecido: '{user_input}'")
                print("       Digite HELP para ver os comandos disponíveis.")
                
    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuário.")
    
    print("[INFO] Cliente encerrado.")


if __name__ == "__main__":
    main()
