import os
import sys

import grpc

import file_converter_pb2 as pb2
import file_converter_pb2_grpc as pb2_grpc

SERVER_HOST = "localhost"
SERVER_PORT = 50051

OUTPUT_DIR = "resultados_client_grpc"

CHUNK_SIZE = 1024 * 32


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def print_help():
    print("\nCOMANDOS DISPONÍVEIS:\n")
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
    print("  EXIT - Encerra o cliente\n")


def generate_requests(src: str, dst: str, filename: str):
    """
    Gera o stream de ConvertRequest:
    - primeiro: Command
    - depois: vários FileChunk com os bytes do arquivo.
    """
    src = src.lstrip(".").lower()
    dst = dst.lstrip(".").lower()
    base_name = os.path.basename(filename)

    cmd = pb2.Command(
        src_ext=src,
        dst_ext=dst,
        original_filename=base_name,
    )
    yield pb2.ConvertRequest(command=cmd)

    with open(filename, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            chunk_msg = pb2.FileChunk(data=data)
            yield pb2.ConvertRequest(chunk=chunk_msg)


def convert_file(stub: pb2_grpc.FileConverterStub, src: str, dst: str, filename: str):
    if not os.path.exists(filename):
        print(f"[ERRO] Arquivo '{filename}' não encontrado.")
        return

    ensure_output_dir()

    request_iterator = generate_requests(src, dst, filename)

    try:
        responses = stub.Convert(request_iterator)
    except grpc.RpcError as e:
        print(f"[ERRO] Falha na chamada gRPC: {e.code()} - {e.details()}")
        return

    output_filename = None
    output_path = None
    file_open = False

    try:
        for resp in responses:
            which = resp.WhichOneof("payload")

            if which == "error":
                print(f"[ERRO DO SERVIDOR] {resp.error.message}")
                return

            if which == "info":
                output_filename = resp.info.output_filename or "arquivo_convertido"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                f_out = open(output_path, "wb")
                file_open = True
                print(f"[INFO] Recebendo arquivo convertido: {output_filename}")
                continue

            if which == "chunk":
                if not file_open:
                    output_filename = "arquivo_convertido_desconhecido"
                    output_path = os.path.join(OUTPUT_DIR, output_filename)
                    f_out = open(output_path, "wb")
                    file_open = True

                f_out.write(resp.chunk.data)

        if file_open:
            f_out.close()
            print(f"[SUCESSO] Arquivo convertido salvo em: {output_path}")
        else:
            print("[INFO] Nenhum dado de arquivo recebido.")

    except grpc.RpcError as e:
        print(f"[ERRO] Erro durante streaming: {e.code()} - {e.details()}")
        if file_open:
            f_out.close()


def main():
    ensure_output_dir()

    print("CLIENTE DE CONVERSÃO DE ARQUIVOS (gRPC)")
    print(f"Conectando em {SERVER_HOST}:{SERVER_PORT}")
    print(f"Resultados serão salvos em: ./{OUTPUT_DIR}/")
    print_help()

    channel = grpc.insecure_channel(f"{SERVER_HOST}:{SERVER_PORT}")
    stub = pb2_grpc.FileConverterStub(channel)

    try:
        while True:
            try:
                user_input = input("\n> ").strip()
            except EOFError:
                break

            if not user_input:
                continue

            cmd_upper = user_input.upper()

            if cmd_upper == "HELP":
                print_help()
                continue

            if cmd_upper == "EXIT":
                print("[INFO] Encerrando cliente...")
                break

            if cmd_upper.startswith("CONVERT"):
                parts = user_input.split()
                if len(parts) != 4:
                    print("[ERRO] Formato incorreto. Use: CONVERT <origem> <destino> <arquivo>")
                    print("       Exemplo: CONVERT .txt .pdf meuarquivo.txt")
                    continue

                _, src, dst, filename = parts
                try:
                    convert_file(stub, src, dst, filename)
                except Exception as e:
                    print(f"[ERRO] Erro durante conversão: {e}")
            else:
                print(f"[ERRO] Comando desconhecido: '{user_input}'")
                print("       Digite HELP para ver os comandos disponíveis.")

    except KeyboardInterrupt:
        print("\n[INFO] Interrompido pelo usuário.")

    print("[INFO] Cliente encerrado.")


if __name__ == "__main__":
    main()
