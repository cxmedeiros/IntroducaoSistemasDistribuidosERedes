import os
import uuid
from concurrent import futures

import grpc
from fpdf import FPDF
from PIL import Image

import file_converter_pb2 as pb2
import file_converter_pb2_grpc as pb2_grpc

OUTPUT_DIR = "conversoes_servidor_grpc"

CHUNK_SIZE = 1024 * 32

SUPPORTED = {
    ("txt", "pdf"),
    ("jpeg", "png"),
    ("jpg", "png"),
}


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def txt_to_pdf(input_path: str, output_path: str) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            pdf.multi_cell(0, 8, line.rstrip("\n"))

    pdf.output(output_path)


def jpeg_to_png(input_path: str, output_path: str) -> None:
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "PNG")


def convert_file(input_path: str, output_path: str, src: str, dst: str) -> None:
    if (src, dst) == ("txt", "pdf"):
        txt_to_pdf(input_path, output_path)
    elif (src, dst) in (("jpeg", "png"), ("jpg", "png")):
        jpeg_to_png(input_path, output_path)
    else:
        raise ValueError(f"Conversão não suportada: {src} -> {dst}")


class FileConverterServicer(pb2_grpc.FileConverterServicer):
    def Convert(self, request_iterator, context):
        ensure_output_dir()

        try:
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

        unique_id = uuid.uuid4().hex[:8]
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        input_path = os.path.join(OUTPUT_DIR, f"temp_{unique_id}_{base_name}.{src}")
        output_filename = f"{base_name}_{unique_id}.{dst}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        try:
            with open(input_path, "wb") as f_in:
                for part in request_iterator:
                    if part.WhichOneof("payload") == "chunk":
                        f_in.write(part.chunk.data)

            convert_file(input_path, output_path, src, dst)

            info = pb2.ResponseInfo(output_filename=output_filename)
            yield pb2.ConvertResponse(info=info)

            with open(output_path, "rb") as f_out:
                for data in iter(lambda: f_out.read(CHUNK_SIZE), b""):
                    yield pb2.ConvertResponse(chunk=pb2.FileChunk(data=data))

        except Exception as e:
            yield pb2.ConvertResponse(error=pb2.Error(message=f"Erro na conversão: {e}"))
        finally:
            if os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError:
                    pass


def serve(port: int = 50051):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )
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
