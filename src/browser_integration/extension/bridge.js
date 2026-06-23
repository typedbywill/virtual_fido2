// Listen for requests from content.js (in MAIN world)
window.addEventListener("virtual-fido2-request", (e) => {
    const { requestId, payload } = e.detail;

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

        // Dispatch response event back to content.js
        const responseEvent = new CustomEvent("virtual-fido2-response", { detail });
        window.dispatchEvent(responseEvent);
    });
});
