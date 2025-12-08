# 📝 Sistema Distribuído de Conversão de Arquivos

Este projeto implementa um sistema cliente-servidor utilizando **TCP Sockets**, capaz de converter arquivos de forma remota.  
O cliente envia o arquivo original, o servidor realiza a conversão e retorna o arquivo convertido.

---

## 📌 Funcionalidades

- Comunicação via **TCP**, garantindo a entrega confiável dos arquivos.
- **Multi-threading**: servidor suporta múltiplos clientes simultaneamente.
- **Conexão persistente**: múltiplas conversões na mesma sessão.
- **Cliente interativo**: interface de linha de comando para o usuário.
- Conversões suportadas:
  - `.txt` → `.pdf` (usando **FPDF**)
  - `.jpeg/.jpg` → `.png` (usando **Pillow**)
- Protocolo simples baseado em comandos:
  ```text
  CONVERT <formato_origem> <formato_destino> <nome_arquivo>
  ```
- Envio estruturado de arquivos usando:
  - 8 bytes → tamanho do arquivo
  - N bytes → conteúdo do arquivo
- Armazenamento dos arquivos convertidos em pastas dedicadas:
  - Servidor: `conversoes_servidor/`
  - Cliente: `resultados_client/`

---

## 📁 Estrutura do Projeto

```text
.
├── client.py              # Cliente interativo
├── server.py              # Servidor multi-threaded
├── requirements.txt       # Dependências Python
├── arquivo.txt            # Arquivo de teste (texto)
├── .gitignore             # Arquivos ignorados pelo Git
└── README.md
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
