# Autenticador FIDO2 / WebAuthn Virtual

Um autenticador FIDO2 virtual baseado em software para recuperação de chaves de acesso (passkeys) pessoais e depuração virtual. Ele intercepta as chamadas à API `navigator.credentials.get` do navegador para capturar as solicitações de autenticação e usa uma chave privada offline para assinar os desafios do WebAuthn.

## Principais Recursos
- **Integração baseada em Interceptação**: Injeta um script de conteúdo de uma extensão do Chrome (Manifest V3) que substitui o `navigator.credentials.get` para contornar a dependência de prompts do sistema operacional.
- **Suporte a Múltiplos Algoritmos**: Gera asserções utilizando ES256, RS256 e EdDSA.
- **Flags em Conformidade com a Especificação**: Emula presença do usuário (User Presence - UP), verificação do usuário (User Verification - UV), elegibilidade de backup (Backup Eligibility - BE) e estado de backup (Backup State - BS).
- **Contador de Assinaturas Persistente**: Acompanha o contador `signCount` em um arquivo JSON local para proteger contra rejeições por detecção de clone.

---

## 1. Configuração e Instalação

### Pré-requisitos
Certifique-se de ter o Python 3.10+ instalado.

### Passo 1: Inicializar o Ambiente Virtual e Instalar Dependências
Execute a configuração a partir do diretório raiz:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Passo 2: Executar os Testes Unitários
Verifique os motores de assinatura criptográfica e as funções geradoras do WebAuthn:
```bash
.venv/bin/python src/test_authenticator.py
```

---

## 2. Guia de Uso

### Passo 1: Iniciar o Daemon FastAPI Local
Disponibilize o servidor de assinatura local (escuta em `localhost:8000`):
```bash
.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### Passo 2: Importar sua Credencial
Use a ferramenta CLI para importar suas credenciais existentes. Por exemplo, para importar uma passkey do `github.com`:
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
Isso armazena as credenciais de forma segura no arquivo `config.json` dentro da raiz do projeto.

### Passo 3: Instalar a Extensão do Navegador
1. Abra o Google Chrome (ou qualquer navegador baseado no Chromium como Brave, Edge, etc.) e acesse `chrome://extensions/`.
2. Habilite o **Modo do desenvolvedor** (chave seletora no canto superior direito).
3. Clique em **Carregar sem compactação** (Load unpacked) no canto superior esquerdo.
4. Selecione o diretório: `/home/nexus/Projetos/pessoal/virtual_fido2/src/browser_integration/extension/`.

---

## 3. Como Funciona

1. **Interceptação da API**: Quando um site chama `navigator.credentials.get`, o script injetado pela extensão intercepta os detalhes da solicitação.
2. **Retransmissão Local**: A extensão do navegador retransmite o payload da solicitação (incluindo o desafio e o `rpId`) para o daemon do FastAPI em execução local no seu computador.
3. **Geração da Asserção**: O daemon FastAPI:
   - Associa o `rpId` do site e os IDs de credenciais permitidos com a sua credencial armazenada.
   - Atualiza o contador de assinaturas `signCount` (se aplicável).
   - Gera um bloco contendo `clientDataJSON` e `authenticatorData` com as flags adequadas (UP, UV, BE, BS).
   - Assina `authenticatorData || SHA256(clientDataJSON)` utilizando a chave privada PEM armazenada.
4. **Resolução**: A extensão do navegador converte a resposta de volta em buffers binários, atende às verificações de protótipo e resolve a promise original da página web, concluindo a autenticação por passkey de forma transparente e fluida.
