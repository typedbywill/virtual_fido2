// Save the original navigator.credentials.get method
const originalGet = navigator.credentials.get.bind(navigator.credentials);

// Helper function to convert ArrayBuffer to Base64URL
function bufferToBase64URL(buffer) {
    if (!buffer) return '';
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

// Helper to convert Base64URL to ArrayBuffer
function base64URLToBuffer(base64url) {
    if (!base64url) return new ArrayBuffer(0);
    const padding = '='.repeat((4 - base64url.length % 4) % 4);
    const base64 = (base64url + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');
    const rawData = atob(base64);
    const outputBuffer = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
        outputBuffer[i] = rawData.charCodeAt(i);
    }
    return outputBuffer.buffer;
}

// Override navigator.credentials.get
navigator.credentials.get = async function (options) {
    if (!options || !options.publicKey) {
        // Delegate to original if it's not a WebAuthn public-key request
        return originalGet(options);
    }

    console.log("[Virtual FIDO2] Intercepted get request with options:", options);

    const pk = options.publicKey;

    // 1. Serialize input options
    const challenge = bufferToBase64URL(pk.challenge);
    const rpId = pk.rpId || window.location.hostname;
    const userVerification = pk.userVerification || 'preferred';
    
    // We get the list of allowed credentials
    const allowedCredentials = [];
    if (pk.allowCredentials) {
        for (const cred of pk.allowCredentials) {
            allowedCredentials.push({
                type: cred.type || 'public-key',
                id: bufferToBase64URL(cred.id)
            });
        }
    }

    // 2. Relay request via custom events to the isolated world content script (bridge)
    const requestPayload = {
        challenge,
        rpId,
        userVerification,
        allowedCredentials,
        origin: window.location.origin
    };

    return new Promise((resolve, reject) => {
        const requestId = Math.random().toString(36).substring(2);

        // Listen for the response from the bridge
        const responseListener = function (e) {
            if (e.detail && e.detail.requestId === requestId) {
                window.removeEventListener("virtual-fido2-response", responseListener);
                
                if (e.detail.error) {
                    reject(new Error(e.detail.error));
                    return;
                }

                const res = e.detail.response;
                console.log("[Virtual FIDO2] Assertion response received:", res);

                // 3. Construct assertion response matching the WebAuthn API spec
                const credentialIdBuffer = base64URLToBuffer(res.credentialId);
                const authenticatorDataBuffer = base64URLToBuffer(res.authenticatorData);
                const clientDataJSONBuffer = base64URLToBuffer(res.clientDataJSON);
                const signatureBuffer = base64URLToBuffer(res.signature);
                const userHandleBuffer = res.userHandle ? base64URLToBuffer(res.userHandle) : null;

                const assertionResult = {
                    id: res.credentialId,
                    rawId: credentialIdBuffer,
                    type: 'public-key',
                    response: {
                        authenticatorData: authenticatorDataBuffer,
                        clientDataJSON: clientDataJSONBuffer,
                        signature: signatureBuffer,
                        userHandle: userHandleBuffer
                    },
                    getClientExtensionResults: () => ({})
                };

                // Add standard prototype methods if checked by client application
                Object.setPrototypeOf(assertionResult, PublicKeyCredential.prototype);
                Object.setPrototypeOf(assertionResult.response, AuthenticatorAssertionResponse.prototype);

                resolve(assertionResult);
            }
        };

        window.addEventListener("virtual-fido2-response", responseListener);

        // Dispatch request to the isolated bridge
        const event = new CustomEvent("virtual-fido2-request", {
            detail: {
                requestId,
                payload: requestPayload
            }
        });
        window.dispatchEvent(event);
    });
};

console.log("[Virtual FIDO2] Hooked navigator.credentials.get successfully.");
