// Listen for requests from content.js (in MAIN world)
window.addEventListener("virtual-fido2-request", (e) => {
    let data = e.detail;
    if (typeof data === "string") {
        try {
            data = JSON.parse(data);
        } catch (err) {
            console.error("[Virtual FIDO2 Bridge] Failed to parse request:", err);
            return;
        }
    }
    if (!data) return;

    const { requestId, payload } = data;

    // Send the message to the background service worker
    chrome.runtime.sendMessage(payload, (response) => {
        // Prepare the response event back to the page context
        let detail = { requestId };
        
        if (chrome.runtime.lastError) {
            detail.error = chrome.runtime.lastError.message;
        } else if (response && response.error) {
            detail.error = response.error;
        } else {
            detail.response = response;
        }

        // Dispatch response event back to content.js.
        // Serializing to a JSON string avoids Firefox "Permission denied to access property"
        // caused by cross-compartment object Xray wrappers.
        const responseEvent = new CustomEvent("virtual-fido2-response", {
            detail: JSON.stringify(detail)
        });
        window.dispatchEvent(responseEvent);
    });
});
