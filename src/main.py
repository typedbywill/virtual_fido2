import base64
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

@app.get("/")
def read_root():
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
            algorithm=cred.algorithm,
            sign_count=cred.signCount,
            backup_eligible=cred.backupEligible,
            backup_state=cred.backupState,
            is_synced=cred.isSynced
        )
        return {"status": "success", "message": f"Credential {cred.credentialId} imported successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
