"""
Servidor UDP para conversão de arquivos.
Implementa transferência confiável sobre UDP com:
- Fragmentação de arquivos em pacotes
- ACK para cada pacote
- Timeout e retransmissão
- Verificação de integridade com SHA256
"""

import socket
import struct
import os
import threading
import uuid
import hashlib
import time
from fpdf import FPDF
from PIL import Image

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

# Porta do servidor
SERVER_PORT = 5051

# Formatos de conversão suportados
SUPPORTED = {
    ("txt", "pdf"),
    ("jpeg", "png"),
    ("jpg", "png")
}

# Diretório para armazenar os arquivos convertidos
OUTPUT_DIR = "conversoes_servidor"

PKT_COMMAND = 0x01      # Comando inicial (CONVERT ...)
PKT_METADATA = 0x02     # Metadados do arquivo (nome, tamanho, total_pacotes)
PKT_DATA = 0x03         # Dados do arquivo
PKT_HASH = 0x04         # Hash SHA256 do arquivo
PKT_ACK = 0x05          # Confirmação de recebimento
PKT_NACK = 0x06         # Erro / Negação
PKT_OK = 0x07           # Confirmação de comando válido
PKT_ERROR = 0x08        # Mensagem de erro
PKT_COMPLETE = 0x09     # Transferência completa


file_lock = threading.Lock()
client_counter = 0
counter_lock = threading.Lock()

def txt_to_pdf(input_path, output_path):
    """Converte arquivo TXT para PDF."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            pdf.multi_cell(0, 8, line.rstrip("\n"))
    
    pdf.output(output_path)


def jpeg_to_png(input_path, output_path):
    """Converte imagem JPEG para PNG."""
    with Image.open(input_path) as img:
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(output_path, 'PNG')


def convert_file(input_path, output_path, src, dst):
    """Realiza a conversão de arquivo conforme os formatos especificados."""
    if (src, dst) == ("txt", "pdf"):
        txt_to_pdf(input_path, output_path)
    elif (src, dst) in [("jpeg", "png"), ("jpg", "png")]:
        jpeg_to_png(input_path, output_path)
    else:
        raise ValueError(f"Conversão não suportada: {src} -> {dst}")


def ensure_output_dir():
    """Garante que o diretório de saída existe."""
    with file_lock:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)


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
                    # Se recebeu pacote de outro tipo, ignora e continua esperando
                except socket.timeout:
                    break
                    
        except socket.timeout:
            print(f"    [Timeout] Tentativa {attempt + 1}/{max_retries} para pacote {expected_ack_id}")
    
    return False


def receive_with_ack(sock, client_addr, expected_type=None):
    """
    Recebe um pacote e envia ACK.
    Retorna: (tipo, packet_id, total_packets, dados) ou None se falhou.
    """
    try:
        packet, addr = sock.recvfrom(MAX_PACKET_SIZE)
        pkt_type, packet_id, total_packets, data = parse_packet(packet)
        
        if packet is None:
            return None, None, None, None
        
        # Verifica tipo esperado
        if expected_type is not None and pkt_type != expected_type:
            return pkt_type, packet_id, total_packets, data
        
        # Envia ACK
        ack_packet = create_packet(PKT_ACK, packet_id, 0)
        sock.sendto(ack_packet, addr)
        
        return pkt_type, packet_id, total_packets, data
        
    except socket.timeout:
        return None, None, None, None


def calculate_sha256(data):
    """Calcula o hash SHA256 dos dados."""
    return hashlib.sha256(data).hexdigest()

def handle_client(sock, initial_packet, client_addr, client_id):
    """
    Trata a comunicação com um cliente.
    """
    print(f"[Cliente {client_id}] Conectado: {client_addr}")
    
    try:
        # Processa o comando inicial
        pkt_type, packet_id, total_packets, data = parse_packet(initial_packet)
        
        if pkt_type != PKT_COMMAND:
            error_pkt = create_packet(PKT_ERROR, 0, 0, b"comando_invalido")
            sock.sendto(error_pkt, client_addr)
            return
        
        # Envia ACK do comando
        ack_packet = create_packet(PKT_ACK, packet_id, 0)
        sock.sendto(ack_packet, client_addr)
        
        command = data.decode().strip()
        print(f"[Cliente {client_id}] Comando: {command}")
        
        if not command.startswith("CONVERT"):
            error_pkt = create_packet(PKT_ERROR, 0, 0, b"comando_invalido")
            sock.sendto(error_pkt, client_addr)
            return
        
        parts = command.split()
        if len(parts) != 4:
            error_pkt = create_packet(PKT_ERROR, 0, 0, b"formato_comando_invalido")
            sock.sendto(error_pkt, client_addr)
            return
        
        _, src, dst, filename = parts
        src = src.lstrip(".")
        dst = dst.lstrip(".")
        
        if (src, dst) not in SUPPORTED:
            error_pkt = create_packet(PKT_ERROR, 0, 0, b"formato_nao_suportado")
            sock.sendto(error_pkt, client_addr)
            return
        
        # Envia OK
        ok_pkt = create_packet(PKT_OK, 0, 0, b"OK")
        sock.sendto(ok_pkt, client_addr)
        
        #  RECEBE METADADOS 
        sock.settimeout(30.0)
        
        pkt_type, packet_id, total_packets, data = receive_with_ack(sock, client_addr)
        
        if pkt_type != PKT_METADATA:
            print(f"[Cliente {client_id}] Esperava METADATA, recebeu tipo {pkt_type}")
            return
        
        # Metadados: nome_arquivo | tamanho | total_pacotes
        meta_parts = data.decode().split("|")
        if len(meta_parts) != 3:
            print(f"[Cliente {client_id}] Metadados inválidos")
            return
        
        original_filename, file_size, total_data_packets = meta_parts
        file_size = int(file_size)
        total_data_packets = int(total_data_packets)
        
        print(f"[Cliente {client_id}] Recebendo arquivo: {original_filename}")
        print(f"[Cliente {client_id}] Tamanho: {file_size} bytes, Pacotes: {total_data_packets}")
        
        #  RECEBE PACOTES DE DADOS 
        received_packets = {}
        expected_packets = set(range(total_data_packets))
        
        sock.settimeout(ACK_TIMEOUT * 2)
        
        while len(received_packets) < total_data_packets:
            try:
                packet, addr = sock.recvfrom(MAX_PACKET_SIZE)
                pkt_type, packet_id, total_pkts, data = parse_packet(packet)
                
                if pkt_type == PKT_DATA:
                    received_packets[packet_id] = data
                    # Envia ACK
                    ack_packet = create_packet(PKT_ACK, packet_id, 0)
                    sock.sendto(ack_packet, addr)
                    print(f"    [Recebido] Pacote {packet_id + 1}/{total_data_packets}")
                    
            except socket.timeout:
                # Se não recebemos todos os pacotes, cliente vai retransmitir
                if len(received_packets) >= total_data_packets:
                    break
                continue
        
        #  RECEBE HASH 
        sock.settimeout(10.0)
        pkt_type, packet_id, _, hash_data = receive_with_ack(sock, client_addr)
        
        if pkt_type != PKT_HASH:
            print(f"[Cliente {client_id}] Esperava HASH, recebeu tipo {pkt_type}")
            return
        
        received_hash = hash_data.decode()
        print(f"[Cliente {client_id}] Hash recebido: {received_hash[:16]}...")
        
        #  RECONSTRÓI ARQUIVO 
        file_content = b""
        for i in range(total_data_packets):
            if i in received_packets:
                file_content += received_packets[i]
        
        # Trunca para o tamanho exato (último pacote pode ter padding)
        file_content = file_content[:file_size]
        
        # Verifica hash
        calculated_hash = calculate_sha256(file_content)
        
        if calculated_hash != received_hash:
            print(f"[Cliente {client_id}] ERRO: Hash não confere!")
            print(f"    Esperado:  {received_hash}")
            print(f"    Calculado: {calculated_hash}")
            error_pkt = create_packet(PKT_ERROR, 0, 0, b"hash_invalido")
            sock.sendto(error_pkt, client_addr)
            return
        
        print(f"[Cliente {client_id}] Hash verificado com sucesso!")
        
        #  CONVERTE ARQUIVO 
        unique_id = uuid.uuid4().hex[:8]
        input_path = f"temp_{unique_id}_{original_filename}"
        base_name = os.path.splitext(original_filename)[0]
        output_filename = f"{base_name}_{unique_id}.{dst}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        try:
            ensure_output_dir()
            
            with open(input_path, "wb") as f:
                f.write(file_content)
            
            convert_file(input_path, output_path, src, dst)
            
            with open(output_path, "rb") as f:
                result_data = f.read()
            
            print(f"[Cliente {client_id}] Conversão concluída: {output_filename}")
            
        except Exception as e:
            print(f"[Cliente {client_id}] Erro na conversão: {e}")
            error_pkt = create_packet(PKT_ERROR, 0, 0, b"erro_conversao")
            sock.sendto(error_pkt, client_addr)
            return
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
        
        #  ENVIA ARQUIVO CONVERTIDO 
        
        # Calcula hash do arquivo convertido
        result_hash = calculate_sha256(result_data)
        
        # Calcula total de pacotes
        result_total_packets = (len(result_data) + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        # Envia metadados do resultado
        result_meta = f"{output_filename}|{len(result_data)}|{result_total_packets}"
        meta_pkt = create_packet(PKT_METADATA, 0, result_total_packets, result_meta.encode())
        
        if not send_with_ack(sock, client_addr, meta_pkt, 0):
            print(f"[Cliente {client_id}] Falha ao enviar metadados do resultado")
            return
        
        print(f"[Cliente {client_id}] Enviando resultado: {len(result_data)} bytes, {result_total_packets} pacotes")
        
        # Envia pacotes de dados
        for i in range(result_total_packets):
            start = i * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, len(result_data))
            chunk = result_data[start:end]
            
            data_pkt = create_packet(PKT_DATA, i, result_total_packets, chunk)
            
            if not send_with_ack(sock, client_addr, data_pkt, i):
                print(f"[Cliente {client_id}] Falha ao enviar pacote {i}")
                return
            
            print(f"    [Enviado] Pacote {i + 1}/{result_total_packets}")
        
        # Envia hash
        hash_pkt = create_packet(PKT_HASH, 0, 0, result_hash.encode())
        if not send_with_ack(sock, client_addr, hash_pkt, 0):
            print(f"[Cliente {client_id}] Falha ao enviar hash")
            return
        
        # Envia sinal de conclusão
        complete_pkt = create_packet(PKT_COMPLETE, 0, 0, output_filename.encode())
        sock.sendto(complete_pkt, client_addr)
        
        print(f"[Cliente {client_id}] Transferência concluída com sucesso!")
        
    except Exception as e:
        print(f"[Cliente {client_id}] Erro: {e}")
        import traceback
        traceback.print_exc()

# MAIN

def main():
    global client_counter
    
    ensure_output_dir()
    
    # Cria socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", SERVER_PORT))
    
    print("\n\n")
    print("SERVIDOR DE CONVERSÃO DE ARQUIVOS (UDP)")
    print("=" * 60)
    print(f"Aguardando conexões na porta {SERVER_PORT}...")
    print(f"Conversões suportadas: {SUPPORTED}")
    print(f"Arquivos convertidos serão salvos em: ./{OUTPUT_DIR}/")
    print(f"Tamanho do chunk: {CHUNK_SIZE} bytes")
    print("\n\n")
    
    try:
        while True:
            # Aguarda pacote inicial de um cliente
            sock.settimeout(None)  # Bloqueante
            packet, client_addr = sock.recvfrom(MAX_PACKET_SIZE)
            
            # Incrementa contador de forma thread-safe
            with counter_lock:
                client_counter += 1
                current_id = client_counter
            
            # Cria thread para atender o cliente
            # Nota: cada thread precisa do seu próprio socket para não conflitar
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_sock.bind(("0.0.0.0", 0))  # Porta efêmera
            
            # Informa ao cliente a nova porta
            new_port = client_sock.getsockname()[1]
            redirect_pkt = create_packet(PKT_OK, 0, 0, struct.pack("!H", new_port))
            sock.sendto(redirect_pkt, client_addr)
            
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_sock, packet, client_addr, current_id),
                daemon=True
            )
            client_thread.start()
            print(f"[Servidor] Thread iniciada para cliente {current_id}. Threads ativas: {threading.active_count() - 1}")
            
    except KeyboardInterrupt:
        print("\n[Servidor] Encerrando...")
    finally:
        sock.close()
        print("[Servidor] Servidor encerrado.")


if __name__ == "__main__":
    main()
