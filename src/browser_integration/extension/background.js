// Listen for messages from bridge.js
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("[Virtual FIDO2 Background] Relaying request to local FastAPI daemon:", request);

    // Call the local FastAPI authenticator service
    fetch("http://localhost:8000/assertion", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "Virtual-FIDO2"
        },
        body: JSON.stringify({
            challenge: request.challenge,
            rpId: request.rpId,
            origin: request.origin,
            userVerification: request.userVerification,
            allowedCredentials: request.allowedCredentials
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.detail || `Server returned status ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("[Virtual FIDO2 Background] Received assertion response:", data);
        sendResponse(data);
    })
    .catch(error => {
        console.error("[Virtual FIDO2 Background] Error communicating with FastAPI daemon:", error);
        sendResponse({ error: error.message });
    });

    // Return true to indicate asynchronous response handler
    return true;
});
