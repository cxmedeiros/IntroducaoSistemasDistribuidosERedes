# 📝 Sistema Distribuído de Conversão de Arquivos (.txt → .pdf)

Este projeto implementa um sistema cliente-servidor utilizando **TCP Sockets**, capaz de converter arquivos **.txt** em **.pdf** de forma remota.  
O cliente envia o arquivo original, o servidor realiza a conversão usando a biblioteca **FPDF** e retorna o PDF gerado.

---

## 📌 Funcionalidades

- Comunicação via **TCP**, garantindo a entrega confiável dos arquivos.
- Protocolo simples baseado em comandos:
  ```text
  CONVERT txt pdf <nome_arquivo>
  ```
- Envio estruturado de arquivos usando:
  - 8 bytes → tamanho do arquivo
  - N bytes → conteúdo do arquivo
- Conversão real de `.txt` para `.pdf` usando **FPDF**.
- Armazenamento temporário e remoção automática dos arquivos no servidor.

---

## 📁 Estrutura do Projeto

```text
.
├── client.py
├── server.py
├── arquivo.txt        # arquivo de teste
└── README.md
```

---

## 🛠️ Pré-requisitos

- Python 3.8+
- Biblioteca `fpdf2` instalada no **servidor**:

```bash
pip install fpdf2
```

---

## 🚀 Como Executar

### 1. Rodar o Servidor

No terminal:

```bash
python server.py
```

Saída esperada:

```text
Servidor aguardando conexões na porta 5050...
```

O servidor ficará escutando na porta **5050** até que um cliente se conecte.

---

### 2. Rodar o Cliente

Em outro terminal, na mesma pasta:

```bash
python client.py
```

O cliente irá:

1. Enviar o comando `CONVERT txt pdf arquivo.txt`
2. Enviar o arquivo `.txt` para o servidor
3. Receber o PDF convertido
4. Salvar o resultado como **resultado.pdf**

---

## 🧪 Teste Rápido

Crie um arquivo `arquivo.txt` com o conteúdo, por exemplo:

```text
Este é um teste de conversão.
Linha 2.
```

Após rodar o cliente, verifique se o arquivo:

```text
resultado.pdf
```

foi criado com sucesso e abre normalmente.

---

## 🔄 Protocolo de Comunicação

### Cliente → Servidor

```text
CONVERT txt pdf <nome_arquivo>
[tamanho (8 bytes)]
[conteúdo do arquivo]
```

### Servidor → Cliente

```text
OK / ERROR <motivo>
[tamanho (8 bytes)]
[conteúdo do PDF]
```

---

## 🧹 Limpeza Automática

O servidor:

- salva o arquivo recebido como `temp_<arquivo>.txt`
- gera `converted_<arquivo>.pdf`
- envia o PDF ao cliente
- apaga ambos logo após o envio

Nenhum arquivo temporário permanece armazenado.