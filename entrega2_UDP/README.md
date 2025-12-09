# 📝 Sistema Distribuído de Conversão de Arquivos

Este projeto implementa um sistema cliente-servidor capaz de converter arquivos de forma remota.  
O cliente envia o arquivo original, o servidor realiza a conversão e retorna o arquivo convertido.

O projeto possui duas implementações:
- **Entrega 1 (TCP)**: Comunicação confiável via TCP Sockets
- **Entrega 2 (UDP)**: Comunicação via UDP com confiabilidade implementada manualmente

---

## 📌 Funcionalidades

- **Multi-threading**: servidor suporta múltiplos clientes simultaneamente.
- **Cliente interativo**: interface de linha de comando para o usuário.
- Conversões suportadas:
  - `.txt` → `.pdf` (usando **FPDF**)
  - `.jpeg/.jpg` → `.png` (usando **Pillow**)
- Protocolo simples baseado em comandos:

  ```text
  CONVERT <formato_origem> <formato_destino> <nome_arquivo>
  ```

- Armazenamento dos arquivos convertidos em pastas dedicadas:
  - Servidor: `conversoes_servidor/`
  - Cliente: `resultados_client/`

---

## 📁 Estrutura do Projeto

```text
.
├── client.py              # Cliente TCP interativo
├── server.py              # Servidor TCP multi-threaded
├── client_udp.py          # Cliente UDP com confiabilidade
├── server_udp.py          # Servidor UDP com confiabilidade
├── requirements.txt       # Dependências Python
├── arquivo.txt            # Arquivo de teste (texto)
├── .gitignore             # Arquivos ignorados pelo Git
├── README.md
└── entrega1_TCP/          # Cópia da entrega 1 (TCP)
```

---

## 🛠️ Pré-requisitos

- Python 3.8+
- Dependências instaladas:

```bash
pip install -r requirements.txt
```

Ou instale manualmente:

```bash
pip install fpdf Pillow
```

---

## 🚀 Como Executar

### 1. Ativar o ambiente virtual (opcional)

```bash
source env/bin/activate
```

### 2. Rodar o Servidor

No terminal:

```bash
python server.py
```

Saída esperada:

```text
==================================================
SERVIDOR DE CONVERSÃO DE ARQUIVOS
==================================================
Aguardando conexões na porta 5050...
Conversões suportadas: {('txt', 'pdf'), ('jpeg', 'png'), ('jpg', 'png')}
Arquivos convertidos serão salvos em: ./conversoes_servidor/
==================================================
```

O servidor ficará escutando na porta **5050** e pode atender múltiplos clientes simultaneamente.

---

### 3. Rodar o Cliente

Em outro terminal, na mesma pasta:

```bash
python client.py
```

O cliente se conectará ao servidor e exibirá um prompt interativo:

```text
==================================================
CLIENTE DE CONVERSÃO DE ARQUIVOS
==================================================
Conectando ao servidor 127.0.0.1:5050...
[INFO] Conectado ao servidor!

==================================================
COMANDOS DISPONÍVEIS:
==================================================
  CONVERT <formato_origem> <formato_destino> <arquivo>

  Conversões suportadas:
    - txt  -> pdf  (texto para PDF)
    - jpeg -> png  (imagem JPEG para PNG)
    - jpg  -> png  (imagem JPG para PNG)

  Exemplos:
    CONVERT .txt .pdf meuarquivo.txt
    CONVERT txt pdf meuarquivo.txt
    CONVERT .jpeg .png imagem.jpeg
    CONVERT jpg png foto.jpg

  HELP - Exibe esta mensagem de ajuda
  EXIT - Encerra a conexão com o servidor
==================================================

>
```

### Comandos disponíveis:

| Comando | Descrição |
|---------|-----------|
| `CONVERT .txt .pdf arquivo.txt` | Converte texto para PDF |
| `CONVERT .jpeg .png imagem.jpeg` | Converte JPEG para PNG |
| `CONVERT jpg png foto.jpg` | Converte JPG para PNG |
| `HELP` | Exibe ajuda |
| `EXIT` | Encerra a conexão |

---

## 🧪 Teste Rápido

### Conversão de texto para PDF

Crie um arquivo `arquivo.txt` com o conteúdo:

```text
Este é um teste de conversão.
Linha 2.
```

No cliente, execute:

```text
> CONVERT .txt .pdf arquivo.txt
```

O arquivo convertido será salvo em `resultados_client/`.

### Conversão de imagem JPEG para PNG

Tenha uma imagem `foto.jpg` na pasta do projeto e execute:

```text
> CONVERT .jpg .png foto.jpg
```

---

## 🔄 Protocolo de Comunicação

### Cliente → Servidor

```text
CONVERT <src> <dst> <nome_arquivo>
[tamanho (8 bytes)]
[conteúdo do arquivo]
```

### Servidor → Cliente

```text
OK / ERROR <motivo>
[tamanho (8 bytes)]
[conteúdo do arquivo convertido]
[tamanho do nome (2 bytes)]
[nome do arquivo salvo]
```

---

## 📡 Versão UDP (Entrega 2)

A versão UDP implementa transferência confiável sobre um protocolo não-confiável, superando os desafios inerentes ao UDP:

### Desafios Superados

| Desafio | Solução Implementada |
|---------|---------------------|
| Perda de pacotes | ACK para cada pacote + retransmissão |
| Ordem dos pacotes | Numeração de pacotes (packet_id) + reordenação |
| Integridade | Hash SHA256 enviado e verificado |
| Fragmentação | Divisão em chunks de 1024 bytes |
| Timeout | Timeout configurável + múltiplas tentativas |

### Formato do Pacote UDP

```text
+--------+------------+---------------+------------------+
| Tipo   | Packet ID  | Total Packets | Dados            |
| 1 byte | 4 bytes    | 4 bytes       | até 1024 bytes   |
+--------+------------+---------------+------------------+
```

### Tipos de Pacotes

| Código | Nome | Descrição |
|--------|------|-----------|
| 0x01 | COMMAND | Comando inicial (CONVERT ...) |
| 0x02 | METADATA | Metadados do arquivo |
| 0x03 | DATA | Dados do arquivo |
| 0x04 | HASH | Hash SHA256 |
| 0x05 | ACK | Confirmação de recebimento |
| 0x06 | NACK | Negação |
| 0x07 | OK | Comando aceito |
| 0x08 | ERROR | Mensagem de erro |
| 0x09 | COMPLETE | Transferência concluída |

### Fluxo de Comunicação UDP

```text
Cliente                              Servidor
   |                                    |
   |------- COMMAND (CONVERT) --------->|
   |<---------- OK (nova porta) --------|
   |<-------------- OK -----------------|
   |                                    |
   |------- METADATA (nome|tam|n) ----->|
   |<------------- ACK -----------------|
   |                                    |
   |------- DATA (pacote 0) ----------->|
   |<------------- ACK -----------------|
   |------- DATA (pacote 1) ----------->|
   |<------------- ACK -----------------|
   |           ...                      |
   |------- DATA (pacote N) ----------->|
   |<------------- ACK -----------------|
   |                                    |
   |------- HASH (SHA256) ------------->|
   |<------------- ACK -----------------|
   |                                    |
   |       [Servidor converte]          |
   |                                    |
   |<------ METADATA (resultado) -------|
   |------------- ACK ----------------->|
   |<------ DATA (pacote 0) ------------|
   |------------- ACK ----------------->|
   |           ...                      |
   |<------ HASH (SHA256) --------------|
   |------------- ACK ----------------->|
   |<-------- COMPLETE -----------------|
   |                                    |
```

### Como Executar (UDP)

**Terminal 1 - Servidor:**

```bash
python server_udp.py
```

**Terminal 2 - Cliente:**

```bash
python client_udp.py
```

### Configurações UDP

| Parâmetro | Valor | Descrição |
|-----------|-------|-----------|
| CHUNK_SIZE | 1024 bytes | Tamanho máximo de dados por pacote |
| ACK_TIMEOUT | 2.0 segundos | Tempo de espera por ACK |
| MAX_RETRIES | 5 | Número máximo de retransmissões |
| SERVER_PORT | 5051 | Porta do servidor UDP |

---

## ↔️ Concorrência

O servidor utiliza **threads** para atender múltiplos clientes simultaneamente:

- Cada cliente é atendido em uma thread separada
- Uso de **locks** para sincronização de acesso a recursos compartilhados
- Identificadores únicos (UUID) para evitar conflitos de nomes de arquivos

---

## 📂 Armazenamento

| Local | Pasta | Descrição |
|-------|-------|-----------|
| Servidor | `conversoes_servidor/` | Arquivos convertidos (mantidos) |
| Cliente | `resultados_client/` | Arquivos recebidos do servidor |

---

## 🧹 Arquivos Temporários

O servidor:

- Salva o arquivo recebido como `temp_<uuid>_<arquivo>`
- Gera o arquivo convertido em `conversoes_servidor/`
- Envia o arquivo ao cliente
- Remove apenas o arquivo temporário de entrada

Os arquivos convertidos permanecem no servidor para histórico.

---

## 🔀 Comparação TCP vs UDP

| Aspecto | TCP | UDP |
|---------|-----|-----|
| Confiabilidade | Nativa | Implementada manualmente |
| Conexão | Orientado a conexão | Sem conexão |
| Overhead | Maior (handshake, controle) | Menor |
| Implementação | Simples | Complexa |
| Porta servidor | 5050 | 5051 |
| ACK | Automático | Manual por pacote |
| Ordem | Garantida | Reordenação manual |
| Integridade | Checksum TCP | SHA256 explícito |
