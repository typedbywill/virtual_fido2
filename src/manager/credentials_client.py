import os
import secrets
import base64
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from src.config import STORE_FILE
from src.credential_store.store import CredentialStore
from src.manager import daemon_client


class CredentialsError(Exception):
    pass


def _store() -> CredentialStore:
    return CredentialStore(STORE_FILE)


def is_online() -> bool:
    return daemon_client.is_daemon_online()


def list_credentials() -> List[dict]:
    if is_online():
        return daemon_client.list_credentials_api()
    return list(_store().credentials.values())


def import_credential(
    credential_id: str,
    rp_id: str,
    user_handle: str,
    username: str,
    private_key_pem: str,
    algorithm: str = "ES256",
    sign_count: int = 0,
    backup_eligible: bool = True,
    backup_state: bool = True,
    is_synced: bool = True,
) -> dict:
    payload = {
        "credentialId": credential_id,
        "rpId": rp_id,
        "userHandle": user_handle,
        "username": username,
        "privateKeyPem": private_key_pem,
        "algorithm": algorithm,
        "signCount": sign_count,
        "backupEligible": backup_eligible,
        "backupState": backup_state,
        "isSynced": is_synced,
    }

    if is_online():
        return daemon_client.import_credential_api(payload)

    _store().add_credential(payload)
    return {"status": "success", "message": "Credential imported (offline — restart daemon to apply)."}


def generate_credential(
    rp_id: str,
    user_handle: str,
    username: str,
    algorithm: str = "ES256",
    sign_count: int = 0,
    backup_eligible: bool = True,
    backup_state: bool = True,
    is_synced: bool = True,
) -> dict:
    payload = {
        "rpId": rp_id,
        "userHandle": user_handle,
        "username": username,
        "algorithm": algorithm,
        "signCount": sign_count,
        "backupEligible": backup_eligible,
        "backupState": backup_state,
        "isSynced": is_synced,
    }

    if is_online():
        return daemon_client.generate_credential_api(payload)

    alg = algorithm.upper()
    if alg == "ES256":
        private_key = ec.generate_private_key(ec.SECP256R1())
    elif alg == "RS256":
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    elif alg == "EDDSA":
        private_key = ed25519.Ed25519PrivateKey.generate()
    else:
        raise CredentialsError(f"Unsupported algorithm: {alg}")

    private_key_pem = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption(),
    ).decode("utf-8")

    rand_bytes = secrets.token_bytes(32)
    credential_id = base64.urlsafe_b64encode(rand_bytes).decode("utf-8").rstrip("=")

    cred = {**payload, "credentialId": credential_id, "privateKeyPem": private_key_pem}
    _store().add_credential(cred)
    return {
        "status": "success",
        "credentialId": credential_id,
        "privateKeyPem": private_key_pem,
        "message": "Credential generated (offline — restart daemon to apply).",
    }


def update_credential(credential_id: str, updates: Dict[str, Any]) -> dict:
    if is_online():
        return daemon_client.update_credential_api(credential_id, updates)

    store = _store()
    if not store.get_credential(credential_id):
        raise CredentialsError("Credential not found")
    store.update_credential(credential_id, updates)
    return {"status": "success", "message": "Credential updated (offline — restart daemon to apply)."}


def delete_credential(credential_id: str) -> dict:
    if is_online():
        return daemon_client.delete_credential_api(credential_id)

    if not _store().delete_credential(credential_id):
        raise CredentialsError("Credential not found")
    return {"status": "success", "message": "Credential deleted (offline — restart daemon to apply)."}


def read_pem_file(path: str) -> str:
    if not os.path.isfile(path):
        raise CredentialsError(f"Private key file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
