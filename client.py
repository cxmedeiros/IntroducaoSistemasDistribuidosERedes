import socket
import struct
import os
import sys

# Diretório local para salvar os arquivos convertidos
OUTPUT_DIR = "resultados_client"

# Configuração do servidor
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5050


def ensure_output_dir():
    """Garante que o diretório de saída existe."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def print_help():
    """Exibe ajuda sobre os comandos disponíveis."""
    print("\n" + "=" * 50)
    print("COMANDOS DISPONÍVEIS:")
    print("=" * 50)
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
    print("  EXIT - Encerra a conexão com o servidor")
    print("=" * 50 + "\n")


def convert_file(sock, src, dst, filename):
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
    
    # Monta e envia o comando
    req = f"CONVERT {src} {dst} {os.path.basename(filename)}"
    sock.sendall(req.encode())
    
    # Aguarda resposta do servidor
    resp = sock.recv(1024).decode()
    
    if resp.startswith("ERROR"):
        error_type = resp.split()[1] if len(resp.split()) > 1 else "desconhecido"
        error_messages = {
            "comando_invalido": "Comando inválido",
            "formato_comando_invalido": "Formato do comando inválido",
            "formato_nao_suportado": "Formato de conversão não suportado"
        }
        print(f"[ERRO] {error_messages.get(error_type, error_type)}")
        return False
    
    if not resp.startswith("OK"):
        print(f"[ERRO] Resposta inesperada do servidor: {resp}")
        return False
    
    # Lê o arquivo e envia
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"[INFO] Enviando arquivo ({len(data)} bytes)...")
    sock.sendall(struct.pack("!Q", len(data)))
    sock.sendall(data)
    
    # Recebe o tamanho do arquivo convertido
    raw_size = sock.recv(8)
    if len(raw_size) < 8:
        print("[ERRO] Erro ao receber resposta do servidor.")
        return False
    
    (size,) = struct.unpack("!Q", raw_size)
    
    if size == 0:
        print("[ERRO] Erro durante a conversão no servidor.")
        return False
    
    # Recebe o arquivo convertido
    print(f"[INFO] Recebendo arquivo convertido ({size} bytes)...")
    result = b""
    while len(result) < size:
        chunk = sock.recv(min(4096, size - len(result)))
        if not chunk:
            break
        result += chunk
    
    if len(result) != size:
        print("[ERRO] Arquivo recebido incompleto.")
        return False
    
    # Recebe o nome do arquivo salvo no servidor
    name_size_raw = sock.recv(2)
    (name_size,) = struct.unpack("!H", name_size_raw)
    server_filename = sock.recv(name_size).decode()
    
    # Garante que o diretório de saída existe
    ensure_output_dir()
    
    # Salva o arquivo convertido localmente
    output_path = os.path.join(OUTPUT_DIR, server_filename)
    with open(output_path, "wb") as f:
        f.write(result)
    
    print(f"[SUCESSO] Arquivo convertido salvo em: {output_path}")
    return True


def main():
    ensure_output_dir()
    
    print("=" * 50)
    print("CLIENTE DE CONVERSÃO DE ARQUIVOS")
    print("=" * 50)
    print(f"Conectando ao servidor {SERVER_HOST}:{SERVER_PORT}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        print("[INFO] Conectado ao servidor!")
        print_help()
    except ConnectionRefusedError:
        print("[ERRO] Não foi possível conectar ao servidor.")
        print("       Verifique se o servidor está rodando.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERRO] Erro ao conectar: {e}")
        sys.exit(1)
    
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
                print("[INFO] Encerrando conexão...")
                sock.sendall(b"EXIT")
                try:
                    resp = sock.recv(1024).decode()
                    if resp == "BYE":
                        print("[INFO] Servidor confirmou encerramento.")
                except:
                    pass
                break
            
            # Comando de conversão
            if user_input.upper().startswith("CONVERT"):
                parts = user_input.split()
                if len(parts) != 4:
                    print("[ERRO] Formato incorreto. Use: CONVERT <origem> <destino> <arquivo>")
                    print("       Exemplo: CONVERT .txt .pdf meuarquivo.txt")
                    continue
                
                _, src, dst, filename = parts
                convert_file(sock, src, dst, filename)
            else:
                print(f"[ERRO] Comando desconhecido: '{user_input}'")
                print("       Digite HELP para ver os comandos disponíveis.")
                
    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuário.")
    except BrokenPipeError:
        print("[ERRO] Conexão com o servidor foi perdida.")
    except ConnectionResetError:
        print("[ERRO] Conexão resetada pelo servidor.")
    except Exception as e:
        print(f"[ERRO] Erro inesperado: {e}")
    finally:
        sock.close()
        print("[INFO] Conexão encerrada.")


if __name__ == "__main__":
    main()
