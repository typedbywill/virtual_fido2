# Virtual FIDO2 / WebAuthn Authenticator

A software-based virtual FIDO2 authenticator for personal passkey recovery and virtual debugging. It overrides the browser's `navigator.credentials.get` API to intercept authentication requests and uses an offline private key to sign WebAuthn challenges.

## Key Features
- **Interception-based Integration**: Injects a Manifest V3 chrome extension content script that overrides `navigator.credentials.get` to bypass operating-system prompt dependencies.
- **Multiple Algorithm Support**: Generates assertions using ES256, RS256, and EdDSA.
- **Spec-Compliant Flags**: Emulates User Presence (UP), User Verification (UV), Backup Eligibility (BE), and Backup State (BS).
- **Persistent Signature Counter**: Keeps track of `signCount` in a local JSON file to protect against clone-detection rejections.

---

## 1. Setup & Installation

### Prerequsites
Make sure you have Python 3.10+ installed.

### Step 1: Initialize Virtual Environment & Install Dependencies
Run the setup from the root directory:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Run the Unit Tests
Verify the cryptographic signature engines and WebAuthn generator functions:
```bash
.venv/bin/python src/test_authenticator.py
```

---

## 2. Usage Guide

### Step 1: Start the Local FastAPI Daemon
Expose the local signing server (listens on `localhost:8000`):
```bash
.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### Step 2: Import Your Credential
Use the CLI tool to import your existing credentials. For example, to import a `github.com` passkey:
```bash
.venv/bin/python src/import_credential_cli.py \
    --id "YOUR_CREDENTIAL_ID_BASE64URL_OR_HEX" \
    --rp-id "github.com" \
    --user-handle "YOUR_USER_HANDLE" \
    --username "YOUR_USERNAME" \
    --key-file "/path/to/your/private_key.pem" \
    --alg "ES256" \
    --counter 0
```
This stores the credentials securely in `config.json` inside the project root.

### Step 3: Install the Browser Extension
1. Open Google Chrome (or any Chromium browser like Brave, Edge, etc.) and navigate to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked** in the top-left corner.
4. Select the directory: `/home/nexus/Projetos/pessoal/virtual_fido2/src/browser_integration/extension/`.

---

## 3. How It Works

1. **API Interception**: When a website invokes `navigator.credentials.get`, the extension's injected script catches the request details.
2. **Local Relay**: The browser extension relays the request payload (including challenge and `rpId`) to the FastAPI daemon running locally on your computer.
3. **Assertion Generation**: The FastAPI daemon:
   - Matches the website's `rpId` and allowed credential IDs to your stored credential.
   - Updates the `signCount` counter (if applicable).
   - Generates a `clientDataJSON` and `authenticatorData` block with appropriate flags (UP, UV, BE, BS).
   - Signs `authenticatorData || SHA256(clientDataJSON)` using the stored PEM private key.
4. **Resolution**: The browser extension maps the response back to binary buffers, satisfies the prototype checks, and resolves the webpage's original promise, completing the passkey authentication seamlessly.
