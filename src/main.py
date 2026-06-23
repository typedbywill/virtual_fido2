import base64
import os
import secrets
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import ec, rsa, ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

from src.virtual_authenticator.core import VirtualAuthenticator

app = FastAPI(title="Virtual FIDO2 Authenticator API")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print("Validation error detail:", exc.errors())
    print("Validation error body:", exc.body)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )


# Enable CORS for Chrome Extension context
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits extension queries from any origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard store file location
STORE_FILE = os.path.expanduser("~/Projetos/pessoal/virtual_fido2/config.json")
authenticator = VirtualAuthenticator(STORE_FILE)
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "index.html")

# Pydantic schemas
class AllowedCredential(BaseModel):
    type: str
    id: str  # Base64url representation of the credential ID

class AssertionRequest(BaseModel):
    challenge: str  # Base64url representation
    rpId: str
    origin: str
    userVerification: Optional[str] = "preferred"
    allowedCredentials: Optional[List[AllowedCredential]] = []

class CredentialImport(BaseModel):
    credentialId: str
    rpId: str
    userHandle: str
    username: str
    privateKeyPem: str
    algorithm: Optional[str] = "ES256"
    signCount: Optional[int] = 0
    backupEligible: Optional[bool] = True
    backupState: Optional[bool] = True
    isSynced: Optional[bool] = True

class CredentialGenerate(BaseModel):
    rpId: str
    userHandle: str
    username: str
    algorithm: Optional[str] = "ES256"
    signCount: Optional[int] = 0
    backupEligible: Optional[bool] = True
    backupState: Optional[bool] = True
    isSynced: Optional[bool] = True

class CredentialUpdate(BaseModel):
    rpId: str
    username: str
    userHandle: str
    signCount: int
    backupEligible: bool
    backupState: bool
    isSynced: bool

def normalize_id(id_str: str) -> bytes:
    """
    Attempts to parse a string ID into bytes.
    Handles base64url, hex, and fallback raw UTF-8.
    """
    # Remove whitespace
    id_str = id_str.strip()
    
    # Try base64url decoding
    try:
        # Add padding
        padding = '=' * (4 - len(id_str) % 4)
        return base64.urlsafe_b64decode(id_str + padding)
    except Exception:
        pass

    # Try hex decoding
    try:
        return bytes.fromhex(id_str)
    except Exception:
        pass

    # Fallback to raw bytes
    return id_str.encode('utf-8')

@app.get("/", response_class=HTMLResponse)
def read_root():
    if os.path.exists(UI_FILE):
        with open(UI_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Virtual FIDO2 Authenticator API</h1><p>Static UI file not found.</p>")

@app.get("/status")
def get_status():
    return {
        "status": "online",
        "authenticator": "Virtual FIDO2/WebAuthn Authenticator",
        "store_path": STORE_FILE,
        "credentials_loaded": len(authenticator.store.credentials)
    }

@app.get("/credentials")
def list_credentials():
    # Return list of credentials with privateKeyPem masked
    result = []
    for cred in authenticator.store.credentials.values():
        masked = cred.copy()
        masked["privateKeyPem"] = "-----BEGIN PRIVATE KEY----- ...MASKED... ----END PRIVATE KEY-----"
        result.append(masked)
    return result

@app.post("/credentials")
def import_credential(cred: CredentialImport):
    try:
        authenticator.import_credential(
            credential_id=cred.credentialId,
            rp_id=cred.rpId,
            user_handle=cred.userHandle,
            username=cred.username,
            private_key_pem=cred.privateKeyPem,
            algorithm=cred.algorithm or "ES256",
            sign_count=cred.signCount or 0,
            backup_eligible=cred.backupEligible if cred.backupEligible is not None else True,
            backup_state=cred.backupState if cred.backupState is not None else True,
            is_synced=cred.isSynced if cred.isSynced is not None else True
        )
        return {"status": "success", "message": f"Credential {cred.credentialId} imported successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/credentials/generate")
def generate_credential(req: CredentialGenerate):
    try:
        alg = (req.algorithm or "ES256").upper()
        if alg == "ES256":
            private_key = ec.generate_private_key(ec.SECP256R1())
        elif alg == "RS256":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        elif alg == "EDDSA":
            private_key = ed25519.Ed25519PrivateKey.generate()
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported algorithm: {alg}")

        # Serialize private key to PEM
        private_key_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption()
        ).decode('utf-8')

        # Generate a random 32-byte credential ID encoded in base64url (without padding)
        rand_bytes = secrets.token_bytes(32)
        credential_id = base64.urlsafe_b64encode(rand_bytes).decode('utf-8').rstrip('=')

        authenticator.import_credential(
            credential_id=credential_id,
            rp_id=req.rpId,
            user_handle=req.userHandle,
            username=req.username,
            private_key_pem=private_key_pem,
            algorithm=alg,
            sign_count=req.signCount or 0,
            backup_eligible=req.backupEligible if req.backupEligible is not None else True,
            backup_state=req.backupState if req.backupState is not None else True,
            is_synced=req.isSynced if req.isSynced is not None else True
        )

        return {
            "status": "success",
            "credentialId": credential_id,
            "privateKeyPem": private_key_pem,
            "message": f"Credential {credential_id} generated and saved successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/credentials/{credential_id}")
def update_credential(credential_id: str, req: CredentialUpdate):
    # Retrieve existing
    existing = authenticator.store.get_credential(credential_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Credential not found")
    
    # Update properties
    updated_data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    success = authenticator.store.update_credential(credential_id, updated_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update credential")
    return {"status": "success", "message": "Credential updated successfully"}

@app.delete("/credentials/{credential_id}")
def delete_credential(credential_id: str):
    success = authenticator.store.delete_credential(credential_id)
    if not success:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"status": "success", "message": "Credential deleted successfully"}

@app.post("/assertion")
def get_assertion(request: AssertionRequest):
    print(f"Received assertion request for RP ID: {request.rpId}")
    
    # 1. Search for matching credential in the store
    target_credential_id = None

    # If the webpage restricts to specific credential IDs
    if request.allowedCredentials:
        # Convert all allowed credentials to normalized bytes
        allowed_bytes = [normalize_id(c.id) for c in request.allowedCredentials]
        
        # Search our store for a credential whose normalized ID matches one of the allowed bytes
        for store_id, cred_data in authenticator.store.credentials.items():
            if cred_data.get("rpId") == request.rpId:
                store_bytes = normalize_id(store_id)
                if store_bytes in allowed_bytes:
                    target_credential_id = store_id
                    break
    else:
        # If allowCredentials list is empty (passwordless), find the first credential matching the RP ID
        for store_id, cred_data in authenticator.store.credentials.items():
            if cred_data.get("rpId") == request.rpId:
                target_credential_id = store_id
                break

    if not target_credential_id:
        raise HTTPException(
            status_code=404,
            detail=f"No matching credential found in store for RP ID {request.rpId}."
        )

    # 2. Generate signature
    try:
        assertion = authenticator.authenticate(
            credential_id=target_credential_id,
            challenge=request.challenge,
            origin=request.origin,
            rp_id=request.rpId,
            user_verification=request.userVerification or "preferred"
        )
        return assertion
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
