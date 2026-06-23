import json
import os
import sys
import argparse

# Add src directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.credential_store.store import CredentialStore

def main():
    parser = argparse.ArgumentParser(description="Import an existing FIDO2/WebAuthn credential into the Virtual Authenticator store.")
    parser.add_argument("--id", required=True, help="Credential ID (Base64url or Hex encoded)")
    parser.add_argument("--rp-id", required=True, help="Relying Party ID (e.g., github.com, google.com)")
    parser.add_argument("--user-handle", required=True, help="User Handle / User ID (e.g., username or database ID)")
    parser.add_argument("--username", required=True, help="Username associated with the credential")
    parser.add_argument("--key-file", required=True, help="Path to PEM file containing the private key")
    parser.add_argument("--alg", default="ES256", choices=["ES256", "RS256", "EdDSA"], help="Signature algorithm (default: ES256)")
    parser.add_argument("--counter", type=int, default=0, help="Initial sign counter value (default: 0)")
    parser.add_argument("--no-backup-eligible", action="store_true", help="Set if credential is NOT backup eligible")
    parser.add_argument("--no-backup-state", action="store_true", help="Set if credential is NOT currently backed up")
    parser.add_argument("--not-synced", action="store_true", help="Disable synced credential mode (forces signCount increments)")
    parser.add_argument("--store-path", default=os.path.expanduser("~/Projetos/pessoal/virtual_fido2/config.json"), help="Path to config.json store file")

    args = parser.parse_args()

    # Verify key file exists
    if not os.path.exists(args.key_file):
        print(f"Error: Private key file not found: {args.key_file}")
        sys.exit(1)

    try:
        with open(args.key_file, "r") as f:
            private_key_pem = f.read()
    except Exception as e:
        print(f"Error reading private key file: {e}")
        sys.exit(1)

    # Load store
    store = CredentialStore(args.store_path)

    # Prepare credential data
    credential_data = {
        "credentialId": args.id,
        "rpId": args.rp_id,
        "userHandle": args.user_handle,
        "username": args.username,
        "privateKeyPem": private_key_pem,
        "algorithm": args.alg,
        "signCount": args.counter,
        "backupEligible": not args.no_backup_eligible,
        "backupState": not args.no_backup_state,
        "isSynced": not args.not_synced
    }

    # Add to store
    store.add_credential(credential_data)
    print(f"Success: Credential imported and saved to {args.store_path}")
    print(f"RP ID: {args.rp_id}")
    print(f"Username: {args.username}")
    print(f"Credential ID: {args.id}")
    print(f"Algorithm: {args.alg}")

if __name__ == "__main__":
    main()
