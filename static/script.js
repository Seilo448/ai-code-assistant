let currentChatId = null;
let isSending = false;

document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const newChatBtn = document.getElementById('new-chat-btn');

    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const message = messageInput.value.trim();
            if (message && currentChatId && !isSending) {
                sendMessage(message);
            }
        });

        messageInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        });

        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', createNewChat);
    }
});

function createNewChat() {
    fetch('/api/chat/new', { method: 'POST' })
        .then(r => { if (!r.ok) throw new Error('Erreur serveur'); return r.json(); })
        .then(data => {
            currentChatId = data.id;
            window.location.href = `/chat?chat=${data.id}`;
        })
        .catch(err => {
            alert('Impossible de créer une conversation. Reconnecte-toi si le problème persiste.');
        });
}

function loadChat(chatId) {
    currentChatId = chatId;
    const messagesContainer = document.getElementById('chat-messages');
    const welcomeMsg = document.getElementById('welcome-message');

    if (welcomeMsg) welcomeMsg.style.display = 'none';

    if (messagesContainer) {
        messagesContainer.innerHTML = '<div class="loading">Chargement...</div>';
    }

    fetch(`/api/chat/${chatId}/messages`)
        .then(r => r.json())
        .then(messages => {
            if (messagesContainer) {
                messagesContainer.innerHTML = '';
                if (messages.length === 0) {
                    messagesContainer.innerHTML = `
                        <div class="welcome-message">
                            <div class="welcome-icon">AI</div>
                            <h2>Nouvelle conversation</h2>
                            <p>Pose une question sur le code, un langage ou un framework !</p>
                        </div>`;
                } else {
                    messages.forEach(m => addMessageToUI(m.role, m.formatted || m.content, false));
                }
                scrollToBottom();
            }

            document.querySelectorAll('.chat-item').forEach(item => {
                item.classList.toggle('active', item.dataset.chatId == chatId);
            });
        });
}

function sendMessage(message) {
    if (isSending) return;
    isSending = true;

    const input = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');

    if (input) input.disabled = true;
    if (sendBtn) sendBtn.disabled = true;

    addMessageToUI('user', escapeHtml(message));

    const messagesContainer = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>`;
    if (messagesContainer) messagesContainer.appendChild(typingDiv);
    scrollToBottom();

    fetch(`/api/chat/${currentChatId}/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    })
    .then(r => { if (!r.ok) { return r.json().then(d => { throw new Error(d.error || 'Erreur serveur'); }); } return r.json(); })
    .then(data => {
        document.getElementById('typing-indicator')?.remove();
        if (data.error) {
            addMessageToUI('assistant', `Erreur : ${escapeHtml(data.error)}`);
            if (data.error.includes('Credits') || data.error.includes('crédit')) {
                addMessageToUI('assistant', 'Contacte l\'administrateur pour obtenir plus de credits.');
            }
        } else {
            addMessageToUI('assistant', data.formatted || data.response);
            if (data.credits_remaining !== undefined) {
                const el = document.getElementById('credit-display');
                if (el) el.textContent = data.credits_remaining;
            }
        }
        scrollToBottom();

        const chatItem = document.querySelector(`.chat-item[data-chat-id="${currentChatId}"]`);
        if (chatItem) {
            const titleEl = chatItem.querySelector('.chat-item-title');
            const firstMsg = document.querySelector('.message.user .message-content');
            if (firstMsg && titleEl) {
                const text = firstMsg.textContent.trim();
                if (text.length > 60) {
                    titleEl.textContent = text.substring(0, 60) + '...';
                } else {
                    titleEl.textContent = text;
                }
            }
        }
    })
    .catch(err => {
        document.getElementById('typing-indicator')?.remove();
        addMessageToUI('assistant', `Erreur : ${escapeHtml(err.message)}`);
    })
    .finally(() => {
        isSending = false;
        if (input) { input.value = ''; input.disabled = false; input.style.height = 'auto'; input.focus(); }
        if (sendBtn) sendBtn.disabled = false;
    });
}

function addMessageToUI(role, content, scroll = true) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const welcomeMsg = document.getElementById('welcome-message');
    if (welcomeMsg) welcomeMsg.style.display = 'none';

    const div = document.createElement('div');
    div.className = `message ${role}`;
    div.innerHTML = `
        <div class="message-avatar">${role === 'user' ? 'U' : 'AI'}</div>
        <div class="message-content">${content}</div>`;
    container.appendChild(div);

    if (scroll) scrollToBottom();
}

function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    if (container) {
        setTimeout(() => { container.scrollTop = container.scrollHeight; }, 50);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
