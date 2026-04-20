function goToChat() {
    const select = document.getElementById('char-select');
    const charId = select.value;
    if (charId) {
        window.location.href = `/chat/${charId}`;
    } else {
        alert("Please select a character first!");
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value;
    if (!message) return;

    // clear input immediately
    input.value = '';
    const response = await fetch (`/chat/${CHAR_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    })
    const data = await response.json();

    const chatWindow = document.getElementById('chat-window');
    chatWindow.innerHTML += `
        <div class="message user"><strong>You:</strong> <p>${message}</p></div>
        <div class="message assistant"><strong>${data.name}:</strong> <p>${data.reply}</p></div>
    `;
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function handleKey(e) {
    if (e.key === 'Enter') sendMessage();
}