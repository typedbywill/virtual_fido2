import json
import os
from typing import Optional, Dict, Any

class CredentialStore:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.credentials: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.filepath):
            self.credentials = {}
            self.save()
            return
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.credentials = {item['credentialId']: item for item in data}
        except (json.JSONDecodeError, KeyError, IOError):
            self.credentials = {}

    def save(self) -> None:
        try:
            parent_dir = os.path.dirname(os.path.abspath(self.filepath))
            os.makedirs(parent_dir, exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(list(self.credentials.values()), f, indent=2)
        except IOError as e:
            print(f"Error saving credential store: {e}")

    def get_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
        return self.credentials.get(credential_id)

    def update_sign_count(self, credential_id: str, new_count: int) -> bool:
        if credential_id in self.credentials:
            self.credentials[credential_id]['signCount'] = new_count
            self.save()
            return True
        return False

    def add_credential(self, cred: Dict[str, Any]) -> None:
        self.credentials[cred['credentialId']] = cred
        self.save()
