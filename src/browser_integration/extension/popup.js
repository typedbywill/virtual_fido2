document.addEventListener('DOMContentLoaded', () => {
    checkDaemonStatus();

    document.getElementById('open-btn').addEventListener('click', () => {
        chrome.tabs.create({ url: 'http://localhost:8000/' });
    });
});

async function checkDaemonStatus() {
    const statusText = document.getElementById('status-text');
    const statusDot = document.getElementById('status-dot');
    const keysCount = document.getElementById('keys-count');

    try {
        const res = await fetch('http://localhost:8000/credentials');
        if (!res.ok) {
            throw new Error();
        }
        const data = await res.json();
        
        // Connected successfully
        statusText.innerText = 'Connected';
        statusText.style.color = '#10b981';
        statusDot.className = 'status-dot connected';
        keysCount.innerText = data.length;
    } catch (e) {
        // Disconnected
        statusText.innerText = 'Disconnected';
        statusText.style.color = '#ef4444';
        statusDot.className = 'status-dot disconnected';
        keysCount.innerText = 'Offline';
    }
}
