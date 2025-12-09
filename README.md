# 📝 Sistema Distribuído de Conversão de Arquivos

Projeto desenvolvido para a disciplina de **Introdução a Sistemas Distribuídos e Redes de Computadores**.

## 📋 Descrição

Sistema cliente-servidor que permite a conversão remota de arquivos. O cliente envia um arquivo ao servidor, que realiza a conversão e retorna o resultado.

**Conversões suportadas:**
- `.txt` → `.pdf`
- `.jpeg/.jpg` → `.png`

---

## 🗂️ Estrutura do Projeto

```
.
├── entrega1_TCP_v1/    # Primeira versão TCP (básica)
├── TCP_v2/             # Segunda versão TCP (melhorada)
├── entrega2_UDP/       # Versão UDP com confiabilidade manual
├── requirements.txt    # Dependências Python
└── README.md
```

---

## Entregas

### Entrega 1 - TCP v1 (`entrega1_TCP_v1/`)

Implementação básica usando **TCP Sockets**.

- Comunicação cliente-servidor simples
- Conversão de `.txt` para `.pdf`
- Servidor single-threaded

📄 [Ver detalhes](./entrega1_TCP_v1/README.md)

---

### TCP v2 (`TCP_v2/`)

Versão melhorada do sistema TCP.

- **Multi-threading**: múltiplos clientes simultâneos
- **Cliente interativo**: loop de comandos
- Conversões: `.txt` → `.pdf` e `.jpeg/.jpg` → `.png`
- Pastas dedicadas para resultados

📄 [Ver detalhes](./TCP_v2/README.md)

---

### Entrega 2 - UDP (`entrega2_UDP/`)

Migração para **UDP** com confiabilidade implementada manualmente.

- Fragmentação de arquivos em pacotes
- ACK para cada pacote
- Timeout + retransmissão
- Verificação de integridade com **SHA256**
- Reordenação de pacotes

📄 [Ver detalhes](./entrega2_UDP/README.md)

---

## 🛠️ Instalação

```bash
# Criar ambiente virtual (opcional)
python -m venv env
source env/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 🚀 Execução Rápida

### TCP (v2)

```bash
cd TCP_v2
python server.py   # Terminal 1
python client.py   # Terminal 2
```

### UDP

```bash
cd entrega2_UDP
python server_udp.py   # Terminal 1
python client_udp.py   # Terminal 2
```

---

## 🔀 Comparação TCP vs UDP

| Aspecto | TCP | UDP |
|---------|-----|-----|
| Confiabilidade | Nativa | Implementada manualmente |
| Conexão | Orientado a conexão | Sem conexão |
| Overhead | Maior (handshake, controle) | Menor |
| Implementação | Simples | Complexa |
| Porta servidor | 5050 | 5051 |

---

## 👥 Equipe

**Equipe 05**

---

## 📚 Tecnologias

- Python 3.8+
- Sockets TCP/UDP
- FPDF (geração de PDF)
- Pillow (manipulação de imagens)
- Threading (concorrência)
