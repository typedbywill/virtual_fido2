from typing import Dict, Any, Optional
from src.credential_store.store import CredentialStore
from src.webauthn.authenticator import WebAuthnAuthenticator

class VirtualAuthenticator:
    def __init__(self, store_filepath: str):
        self.store = CredentialStore(store_filepath)
        self.authenticator = WebAuthnAuthenticator(self.store)

    def authenticate(
        self,
        credential_id: str,
        challenge: str,
        origin: str,
        rp_id: str,
        user_verification: str = "preferred",
        client_data_json_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point to perform a WebAuthn assertion response signature.
        """
        # Call the WebAuthn generator
        return self.authenticator.generate_assertion(
            credential_id=credential_id,
            challenge=challenge,
            origin=origin,
            rp_id=rp_id,
            user_verification=user_verification,
            client_data_json_override=client_data_json_override
        )

    def import_credential(
        self,
        credential_id: str,
        rp_id: str,
        user_handle: str,
        username: str,
        private_key_pem: str,
        algorithm: str = "ES256",
        sign_count: int = 0,
        backup_eligible: bool = True,
        backup_state: bool = True,
        is_synced: bool = True
    ) -> None:
        """
        Imports an existing FIDO2/WebAuthn credential into the store.
        """
        credential_data = {
            "credentialId": credential_id,
            "rpId": rp_id,
            "userHandle": user_handle,
            "username": username,
            "privateKeyPem": private_key_pem,
            "algorithm": algorithm,
            "signCount": sign_count,
            "backupEligible": backup_eligible,
            "backupState": backup_state,
            "isSynced": is_synced
        }
        self.store.add_credential(credential_data)
