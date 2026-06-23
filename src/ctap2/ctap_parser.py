import struct
from typing import Tuple, Dict, Any, Optional
# python-fido2 package includes cbor mapping
try:
    from fido2 import cbor
except ImportError:
    # Fallback or stub if python-fido2 is not in environment yet
    cbor = None

# CTAP2 Command Codes
class CTAP2Command:
    MAKE_CREDENTIAL = 0x01
    GET_ASSERTION = 0x02
    GET_INFO = 0x04
    CLIENT_PIN = 0x06
    RESET = 0x07

class CTAP2Parser:
    def __init__(self):
        if cbor is None:
            print("Warning: fido2 library not imported. CTAP2 parsing will be limited.")

    def parse_command(self, raw_data: bytes) -> Tuple[int, Optional[Dict[Any, Any]]]:
        """
        Parses a raw CTAP2 command byte string.
        Format: [1-byte Command Code] [CBOR Payload]
        """
        if not raw_data:
            raise ValueError("Empty CTAP2 message")

        cmd_code = raw_data[0]
        cbor_payload = raw_data[1:]

        if not cbor_payload:
            return cmd_code, None

        if cbor is None:
            return cmd_code, {"raw_payload": cbor_payload}

        try:
            decoded = cbor.decode(cbor_payload)
            return cmd_code, decoded
        except Exception as e:
            raise ValueError(f"Failed to decode CBOR payload for command {cmd_code}: {e}")

    def serialize_response(self, status_code: int, response_data: Optional[Dict[Any, Any]] = None) -> bytes:
        """
        Serializes a CTAP2 response.
        Format: [1-byte Status Code] [CBOR Payload]
        """
        status_byte = bytes([status_code])
        if response_data is None or cbor is None:
            return status_byte
        
        try:
            return status_byte + cbor.encode(response_data)
        except Exception as e:
            raise ValueError(f"Failed to encode CBOR response: {e}")
