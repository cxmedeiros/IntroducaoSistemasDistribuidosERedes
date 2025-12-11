# server_grpc.py

import os
import uuid
from concurrent import futures

import grpc
from fpdf import FPDF
from PIL import Image

import file_converter_pb2 as pb2
import file_converter_pb2_grpc as pb2_grpc

# Diretório para armazenar arquivos convertidos
OUTPUT_DIR = "conversoes_servidor_grpc"

# Tamanho do chunk de leitura/escrita em bytes
CHUNK_SIZE = 1024 * 32  # pode ser maior que o usado no UDP se quiser

# Conversões suportadas
SUPPORTED = {
    ("txt", "pdf"),
    ("jpeg", "png"),
    ("jpg", "png"),
}


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def txt_to_pdf(input_path: str, output_path: str) -> None:
    """Converte arquivo TXT para PDF."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            pdf.multi_cell(0, 8, line.rstrip("\n"))

    pdf.output(output_path)


def jpeg_to_png(input_path: str, output_path: str) -> None:
    """Converte imagem JPEG/JPG para PNG."""
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "PNG")


def convert_file(input_path: str, output_path: str, src: str, dst: str) -> None:
    """Chama a conversão adequada conforme formatos."""
    if (src, dst) == ("txt", "pdf"):
        txt_to_pdf(input_path, output_path)
    elif (src, dst) in (("jpeg", "png"), ("jpg", "png")):
        jpeg_to_png(input_path, output_path)
    else:
        raise ValueError(f"Conversão não suportada: {src} -> {dst}")


class FileConverterServicer(pb2_grpc.FileConverterServicer):
    def Convert(self, request_iterator, context):
        """
        Implementação do RPC Convert.

        Protocolo:
        - Primeiro request deve ser Command (src, dst, filename).
        - Demais requests: FileChunk com dados do arquivo de entrada.
        - Servidor acumula em arquivo temporário, converte, e então:
          * envia 1 ResponseInfo com o nome do arquivo convertido;
          * envia vários FileChunk com os bytes do arquivo convertido.
        """
        ensure_output_dir()

        try:
            # ----- 1) Lê primeiro request: deve ser Command -----
            first_request = next(request_iterator)
        except StopIteration:
            yield pb2.ConvertResponse(
                error=pb2.Error(message="Fluxo de requisição vazio.")
            )
            return

        if first_request.WhichOneof("payload") != "command":
            yield pb2.ConvertResponse(
                error=pb2.Error(
                    message="Primeira mensagem deve ser Command (src_ext, dst_ext, original_filename)."
                )
            )
            return

        cmd = first_request.command
        src = cmd.src_ext.lstrip(".").lower()
        dst = cmd.dst_ext.lstrip(".").lower()
        original_filename = cmd.original_filename or "arquivo"

        if (src, dst) not in SUPPORTED:
            yield pb2.ConvertResponse(
                error=pb2.Error(
                    message=f"Conversão não suportada: {src} -> {dst}. "
                            f"Suportadas: txt->pdf, jpeg->png, jpg->png."
                )
            )
            return

        # ----- 2) Recebe o arquivo de entrada em chunks -----
        unique_id = uuid.uuid4().hex[:8]
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        input_path = os.path.join(OUTPUT_DIR, f"temp_{unique_id}_{base_name}.{src}")
        output_filename = f"{base_name}_{unique_id}.{dst}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        try:
            # Grava o arquivo de entrada em disco enquanto lê o stream
            with open(input_path, "wb") as f_in:
                # Primeiro chunk pode ter vindo junto com o Command? Não, pelo nosso .proto.
                for req in request_iterator:
                    if req.WhichOneof("payload") == "chunk":
                        f_in.write(req.chunk.data)

            # ----- 3) Converte o arquivo -----
            convert_file(input_path, output_path, src, dst)

            # ----- 4) Envia metadados do arquivo convertido -----
            info = pb2.ResponseInfo(output_filename=output_filename)
            yield pb2.ConvertResponse(info=info)

            # ----- 5) Envia arquivo convertido em chunks -----
            with open(output_path, "rb") as f_out:
                while True:
                    data = f_out.read(CHUNK_SIZE)
                    if not data:
                        break
                    chunk_msg = pb2.FileChunk(data=data)
                    yield pb2.ConvertResponse(chunk=chunk_msg)

        except Exception as e:
            # Em caso de erro, envia uma mensagem de erro
            yield pb2.ConvertResponse(error=pb2.Error(message=f"Erro na conversão: {e}"))
        finally:
            # Limpeza opcional de arquivos temporários
            if os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError:
                    pass
            # Você pode decidir manter ou remover os convertidos; aqui estou mantendo.


def serve(port: int = 50051):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )  # 10 clientes simultâneos (ajustável)
    pb2_grpc.add_FileConverterServicer_to_server(FileConverterServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    print(f"Servidor gRPC de conversão ouvindo na porta {port}...")
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")


if __name__ == "__main__":
    serve()
