# Autenticador FIDO2 / WebAuthn Virtual

Um autenticador FIDO2 virtual baseado em software para recuperação de chaves de acesso (passkeys) pessoais e depuração virtual. Ele intercepta as chamadas à API `navigator.credentials.get` do navegador para capturar as solicitações de autenticação e usa uma chave privada offline para assinar os desafios do WebAuthn.

## Início rápido

**Um único comando** — sem clonar repositório, sem git, sem configurar nada manualmente:

```bash
curl -fsSL https://raw.githubusercontent.com/typedbywill/virtual_fido2/main/setup.sh | bash
```

O script baixa o projeto para `~/.local/share/virtual-fido2`, instala as dependências, registra o comando `virtual-fido2` em `~/.local/bin` e abre o gerenciador no terminal.

Para abrir o gerenciador depois:

```bash
virtual-fido2
```

> Se `virtual-fido2` não for encontrado, adicione `~/.local/bin` ao seu `PATH` ou rode o comando `curl` acima novamente.

O **Gerenciador TUI** centraliza:

- Instalação do serviço systemd
- Gerenciamento do daemon (status, start, stop, logs)
- Instalação da extensão no navegador (Chrome, Chromium, Brave, Edge, Firefox)
- Abertura do painel web
- Gestão de chaves FIDO2 (listar, importar, gerar, editar, excluir)

---

## Principais Recursos

- **Gerenciador TUI interativo**: menu no terminal para configurar tudo sem memorizar comandos
- **Integração baseada em Interceptação**: extensão MV3 que substitui `navigator.credentials.get`
- **Suporte a Múltiplos Algoritmos**: ES256, RS256 e EdDSA
- **Flags em Conformidade com a Especificação**: UP, UV, BE e BS
- **Contador de Assinaturas Persistente**: `signCount` em `config.json` local
- **Painel web**: dashboard em `http://localhost:8000` para gestão visual de credenciais

---

## Configuração manual (desenvolvedores)

Se você clonou o repositório para contribuir ou desenvolver:

```bash
git clone https://github.com/typedbywill/virtual_fido2.git
cd virtual_fido2
./virtual-fido2
```

### Pré-requisitos

- Python 3.10+
- Linux com systemd (para serviço em background)

### Ambiente virtual e dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Testes unitários

```bash
.venv/bin/python src/test_authenticator.py
```

### Instalar serviço systemd

```bash
./install.sh
# ou
.venv/bin/python src/daemon_manager.py install
```

### Importar credencial via CLI

```bash
.venv/bin/python src/import_credential_cli.py \
    --id "ID_DA_SUA_CREDENCIAL_BASE64URL_OU_HEX" \
    --rp-id "github.com" \
    --user-handle "SEU_USER_HANDLE" \
    --username "SEU_NOME_DE_USUARIO" \
    --key-file "/caminho/para/sua/chave_privada.pem" \
    --alg "ES256" \
    --counter 0
```

As credenciais são salvas em `config.json` na raiz do projeto.

### Extensão do navegador (manual)

1. Abra Chrome/Chromium/Brave/Edge → `chrome://extensions/`
2. Ative **Modo do desenvolvedor**
3. **Carregar sem compactação** → selecione `src/browser_integration/extension/`

Para Firefox: `about:debugging#/runtime/this-firefox` → **Carregar extensão temporária** → selecione o `manifest.json` da pasta da extensão.

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VIRTUAL_FIDO2_STORE` | `{projeto}/config.json` | Caminho do arquivo de credenciais |
| `VIRTUAL_FIDO2_HOST` | `127.0.0.1` | Host do daemon |
| `VIRTUAL_FIDO2_PORT` | `8000` | Porta do daemon |
| `VIRTUAL_FIDO2_HOME` | `~/.local/share/virtual-fido2` | Diretório onde o instalador baixa e mantém o projeto |

---

## Como funciona

1. **Interceptação da API**: a extensão intercepta `navigator.credentials.get`
2. **Retransmissão local**: a extensão envia o payload para o daemon FastAPI em `localhost:8000`
3. **Geração da asserção**: o daemon associa `rpId` e credential IDs, atualiza `signCount`, monta `authenticatorData` e assina com a chave PEM
4. **Resolução**: a extensão devolve a asserção à página e a autenticação conclui

---

## API REST (referência)

| Método | Path | Descrição |
|--------|------|-----------|
| `GET` | `/` | Painel web |
| `GET` | `/status` | Status do daemon |
| `GET` | `/credentials` | Listar credenciais |
| `POST` | `/credentials` | Importar credencial |
| `POST` | `/credentials/generate` | Gerar nova chave |
| `PUT` | `/credentials/{id}` | Atualizar metadados |
| `DELETE` | `/credentials/{id}` | Excluir credencial |
| `POST` | `/assertion` | Assinar asserção WebAuthn |

Endpoints protegidos exigem o header `X-Requested-With: Virtual-FIDO2`.
