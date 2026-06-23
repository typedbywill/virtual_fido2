import hashlib
import json
import base64
from typing import Dict, Any, Optional
from src.credential_store.store import CredentialStore
from src.crypto.key_handler import KeyHandler

class WebAuthnAuthenticator:
    def __init__(self, store: CredentialStore):
        self.store = store

    def _base64url_encode(self, data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

    def _base64url_decode(self, data: str) -> bytes:
        # Add padding back if necessary
        padding = '=' * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    def generate_assertion(
        self,
        credential_id: str,
        challenge: str,  # base64url encoded challenge from the client
        origin: str,
        rp_id: str,
        user_verification: str = "preferred",  # "required", "preferred", "discouraged"
        client_data_json_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a WebAuthn assertion response for a given credential.
        """
        # 1. Retrieve the credential from the store
        cred = self.store.get_credential(credential_id)
        if not cred:
            raise ValueError(f"Credential not found for ID: {credential_id}")

        if cred.get("rpId") != rp_id:
            raise ValueError(f"RP ID mismatch: credential belongs to {cred.get('rpId')}, requested {rp_id}")

        # 2. Reconstruct or use overridden clientDataJSON
        if client_data_json_override:
            client_data_json = client_data_json_override
            client_data_json_bytes = client_data_json.encode('utf-8')
        else:
            # Build clientDataJSON dict according to specification
            # Challenge must be base64url string
            client_data = {
                "type": "webauthn.get",
                "challenge": challenge,
                "origin": origin,
                "crossOrigin": False
            }
            # Ensure keys are serialized standardly, with no extra whitespace
            client_data_json = json.dumps(client_data, separators=(',', ':'))
            client_data_json_bytes = client_data_json.encode('utf-8')

        client_data_hash = hashlib.sha256(client_data_json_bytes).digest()

        # 3. Assemble authenticatorData
        # rpIdHash (32 bytes)
        rp_id_hash = hashlib.sha256(rp_id.encode('utf-8')).digest()

        # flags (1 byte)
        # Bit 0: UP (User Presence) - always 1 for assertion
        # Bit 2: UV (User Verification) - based on request and credential
        # Bit 3: BE (Backup Eligible) - from credential
        # Bit 4: BS (Backup State) - from credential
        flags = 0x01  # UP is always 1

        # Check user verification request
        # If required, we must set UV=1. If preferred, we choose to set UV=1.
        if user_verification in ["required", "preferred"]:
            flags |= 0x04

        if cred.get("backupEligible", False):
            flags |= 0x08
        if cred.get("backupState", False):
            flags |= 0x10

        # signCount (4 bytes)
        sign_count = cred.get("signCount", 0)
        # If we use incrementing counter, update the store
        # Synced passkeys (signCount=0) might not increment, but we'll increment if it's set > 0
        if sign_count > 0 or not cred.get("isSynced", False):
            sign_count += 1
            self.store.update_sign_count(credential_id, sign_count)

        flags_byte = flags.to_bytes(1, byteorder='big')
        sign_count_bytes = sign_count.to_bytes(4, byteorder='big')

        authenticator_data = rp_id_hash + flags_byte + sign_count_bytes

        # 4. Generate the Signature
        # signature = Sign(authenticatorData || SHA256(clientDataJSON))
        signature_base = authenticator_data + client_data_hash
        
        key_handler = KeyHandler(cred["privateKeyPem"], cred.get("algorithm", "ES256"))
        signature_bytes = key_handler.sign(signature_base)

        # 5. Format response to be sent back to the browser / extension API
        user_handle = cred.get("userHandle", "")
        user_handle_b64url = ""
        if user_handle:
            try:
                # Test if user_handle is already valid base64url
                self._base64url_decode(user_handle)
                user_handle_b64url = user_handle
            except Exception:
                user_handle_b64url = self._base64url_encode(user_handle.encode('utf-8'))

        return {
            "credentialId": credential_id,
            "authenticatorData": self._base64url_encode(authenticator_data),
            "clientDataJSON": self._base64url_encode(client_data_json_bytes),
            "signature": self._base64url_encode(signature_bytes),
            "userHandle": user_handle_b64url
        }
