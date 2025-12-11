# Entrega 3 — gRPC

Este diretório contém a implementação gRPC do projeto. Abaixo estão instruções para instalar dependências, gerar código a partir do `.proto` e executar o servidor e cliente no Windows (PowerShell). As instruções funcionam também em Linux/macOS com pequenas adaptações (usar `python3` em vez de `python`, por exemplo).

## Pré-requisitos

- Python 3.8+ instalado
- Recomenda-se criar um ambiente virtual (`venv`) para isolar dependências

## Passos rápidos (PowerShell)

1. Abra o PowerShell e navegue até este diretório:

```powershell
cd path\to\IntroducaoSistemasDistribuidosERedes\entrega3_gRPC
```

2. (Opcional, recomendado) Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Instale as dependências necessárias:

```powershell
python -m pip install --upgrade pip
python -m pip install grpcio grpcio-tools fpdf2 pillow
```

> Nota: se preferir criar um `requirements.txt`, gere-o com `pip freeze > requirements.txt`.

4. Gerar os arquivos Python a partir do `file_converter.proto` (caso ainda não existam ou você altere o proto):

```powershell
python -m grpc_tools.protoc -I . --python_out=. --grpc_python_out=. file_converter.proto
```

Isso vai gerar (ou atualizar) `file_converter_pb2.py` e `file_converter_pb2_grpc.py` neste diretório.

## Estrutura relevante

- `file_converter.proto` — definição das mensagens/serviços gRPC
- `server_grpc.py` — servidor gRPC
- `client_grpc.py` — cliente gRPC (exemplos de chamadas)
- `file_converter_pb2.py`, `file_converter_pb2_grpc.py` — arquivos gerados pelo protoc
- `conversoes_servidor_grpc/` — pasta usada pelo servidor para salvar conversões (se existente)
- `resultados_client_grpc/` — pasta onde o cliente salva arquivos recebidos (se existente)

## Como executar

1. Inicie o servidor (em uma janela do PowerShell):

```powershell
python server_grpc.py
```

2. Em outra janela (ou após o servidor estar rodando), execute o cliente:

```powershell
python client_grpc.py
```

O cliente deve se conectar ao servidor e realizar as operações descritas na implementação.

## Dicas de depuração

- Se receber erros relacionados a imports dos arquivos gerados, verifique se `file_converter_pb2.py` e `file_converter_pb2_grpc.py` estão no mesmo diretório que `client_grpc.py`/`server_grpc.py` ou ajuste o `PYTHONPATH`.
- Se a porta já estiver em uso, verifique/alterar a porta usada no `server_grpc.py`.
- Se o comando `grpc_tools.protoc` falhar, confirme que `grpcio-tools` está instalado no ambiente ativo.

## Observações finais

- Estas instruções cobrem a execução local de desenvolvimento no Windows. Para deploy em produção considere: usar um gerenciador de processos (systemd, pm2, etc.), certificados TLS para gRPC e variáveis de ambiente para configuração de portas/endpoints.

Se quiser, eu posso também adicionar um `requirements.txt`, scripts de execução (`run_server.ps1`, `run_client.ps1`) ou um exemplo de virtualenv automatizado. Diga o que prefere.
