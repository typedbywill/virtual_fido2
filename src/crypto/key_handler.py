from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa, ed25519, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from typing import Union

class KeyHandler:
    def __init__(self, private_key_pem: str, algorithm: str = "ES256"):
        self.algorithm = algorithm.upper()
        # Clean/load key
        key_bytes = private_key_pem.encode('utf-8') if isinstance(private_key_pem, str) else private_key_pem
        self.private_key = load_pem_private_key(key_bytes, password=None)

    def sign(self, data: bytes) -> bytes:
        """
        Signs the input data using the loaded private key and specified algorithm.
        Returns the signature bytes.
        """
        if self.algorithm == "ES256":
            if not isinstance(self.private_key, ec.EllipticCurvePrivateKey):
                raise ValueError("Key type mismatch: expected EllipticCurvePrivateKey for ES256")
            # ECDSA signatures returned by cryptography are DER-encoded, which is standard for WebAuthn/FIDO2 ES256
            return self.private_key.sign(data, ec.ECDSA(hashes.SHA256()))

        elif self.algorithm == "RS256":
            if not isinstance(self.private_key, rsa.RSAPrivateKey):
                raise ValueError("Key type mismatch: expected RSAPrivateKey for RS256")
            return self.private_key.sign(
                data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

        elif self.algorithm == "EDDSA":
            if not isinstance(self.private_key, ed25519.Ed25519PrivateKey):
                raise ValueError("Key type mismatch: expected Ed25519PrivateKey for EdDSA")
            # Ed25519 signs the message directly; no hash algorithm parameter is passed to .sign()
            return self.private_key.sign(data)

        else:
            raise NotImplementedError(f"Algorithm {self.algorithm} is not supported")
