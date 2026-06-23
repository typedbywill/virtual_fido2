import os
import sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa, ed25519, padding
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

# Add src to python path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crypto.key_handler import KeyHandler
from src.credential_store.store import CredentialStore
from src.webauthn.authenticator import WebAuthnAuthenticator

def generate_test_keys():
    print("Generating temporary test keys for verification...")
    # ES256
    ec_key = ec.generate_private_key(ec.SECP256R1())
    ec_pem = ec_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode('utf-8')
    
    # RS256
    rsa_key = rsa.generate_private_key(65537, 2048)
    rsa_pem = rsa_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode('utf-8')

    # EdDSA
    ed_key = ed25519.Ed25519PrivateKey.generate()
    ed_pem = ed_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode('utf-8')

    return ec_pem, rsa_pem, ed_pem

def test_cryptography():
    ec_pem, rsa_pem, ed_pem = generate_test_keys()
    test_data = b"WebAuthn assertion verification test payload"

    # Test ES256
    print("Testing ES256...")
    handler_ec = KeyHandler(ec_pem, "ES256")
    sig_ec = handler_ec.sign(test_data)
    # Verify EC signature
    pub_key_ec = handler_ec.private_key.public_key()
    pub_key_ec.verify(sig_ec, test_data, ec.ECDSA(hashes.SHA256()))
    print("ES256 signature verification successful!")

    # Test RS256
    print("Testing RS256...")
    handler_rsa = KeyHandler(rsa_pem, "RS256")
    sig_rsa = handler_rsa.sign(test_data)
    # Verify RSA signature
    pub_key_rsa = handler_rsa.private_key.public_key()
    pub_key_rsa.verify(sig_rsa, test_data, padding.PKCS1v15(), hashes.SHA256())
    print("RS256 signature verification successful!")

    # Test EdDSA
    print("Testing EdDSA...")
    handler_ed = KeyHandler(ed_pem, "EDDSA")
    sig_ed = handler_ed.sign(test_data)
    # Verify Ed25519 signature
    pub_key_ed = handler_ed.private_key.public_key()
    pub_key_ed.verify(sig_ed, test_data)
    print("EdDSA signature verification successful!")

def test_webauthn_assertion():
    print("Testing WebAuthn assertion generation...")
    ec_pem, _, _ = generate_test_keys()
    
    # Store filepath
    temp_store_path = "test_store.json"
    if os.path.exists(temp_store_path):
        os.remove(temp_store_path)

    store = CredentialStore(temp_store_path)
    
    # Add a mock credential
    cred_id = "mock_credential_id_123"
    store.add_credential({
        "credentialId": cred_id,
        "rpId": "localhost",
        "userHandle": "user_id_xyz",
        "username": "testuser",
        "privateKeyPem": ec_pem,
        "algorithm": "ES256",
        "signCount": 10,
        "backupEligible": True,
        "backupState": True
    })

    authenticator = WebAuthnAuthenticator(store)
    
    # Challenge must be base64url encoded
    test_challenge_b64url = "Q2hhbGxlbmdlRGF0YTEyMzQ1Njc4OTA="
    test_origin = "http://localhost:8000"
    test_rp_id = "localhost"

    assertion = authenticator.generate_assertion(
        credential_id=cred_id,
        challenge=test_challenge_b64url,
        origin=test_origin,
        rp_id=test_rp_id,
        user_verification="required"
    )

    print("Generated assertion response payload:")
    print(assertion)

    # Check updated signCount
    updated_cred = store.get_credential(cred_id)
    print(f"Updated signCount: {updated_cred['signCount']}")
    assert updated_cred['signCount'] == 11, "Sign count should be incremented to 11"

    # Cleanup
    if os.path.exists(temp_store_path):
        os.remove(temp_store_path)
    print("WebAuthn assertion tests passed successfully!")

if __name__ == "__main__":
    try:
        test_cryptography()
        test_webauthn_assertion()
        print("\nAll unit tests passed successfully!")
    except Exception as e:
        print(f"\nUnit tests failed: {e}")
        sys.exit(1)
