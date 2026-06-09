// TicketMinds Customer Dashboard Controller

let activeTicketId = null;
let pollingInterval = null;

// Page Load Setup
window.addEventListener('DOMContentLoaded', async () => {
    // 1. Session verification
    const session = await checkSession();
    if (!session.logged_in) {
        window.location.href = '/login?role=user';
        return;
    }
    
    if (session.user.role !== 'user') {
        window.location.href = '/dashboard/engineer';
        return;
    }
    
    // Set Profile UI
    document.getElementById('user-profile-name').textContent = session.user.name;
    document.getElementById('user-avatar').textContent = session.user.name.charAt(0).toUpperCase();
    
    // 2. Load Tickets list
    await loadTicketHistory();
    
    // 3. Register send message form listener
    const sendForm = document.getElementById('chat-send-form');
    sendForm.addEventListener('submit', handleSendMessage);
    
    // Register ticket submission form listener
    const ticketForm = document.getElementById('new-ticket-form');
    ticketForm.addEventListener('submit', handleCreateTicket);
});

// Load user's ticket list
async function loadTicketHistory() {
    try {
        const res = await apiFetch('/api/tickets');
        const listContainer = document.getElementById('ticket-history-list');
        listContainer.innerHTML = '';
        
        if (!res.tickets || res.tickets.length === 0) {
            listContainer.innerHTML = `
                <div style="text-align: center; color: var(--text-muted); margin-top: 40px; font-size: 0.85rem; padding: 0 10px;">
                    No support tickets raised yet. Click above to start.
                </div>`;
            return;
        }
        
        res.tickets.forEach(ticket => {
            const item = document.createElement('div');
            item.className = `ticket-item ${activeTicketId === ticket.ticket_id ? 'active' : ''}`;
            item.setAttribute('data-id', ticket.ticket_id);
            
            // Format Created time
            const dateStr = new Date(ticket.created_at).toLocaleString([], {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            
            // Status badge classes
            let badgeClass = 'badge-open';
            if (ticket.status === 'In Progress') badgeClass = 'badge-progress';
            else if (ticket.status === 'Resolved') badgeClass = 'badge-resolved';
            else if (ticket.status === 'Closed') badgeClass = 'badge-closed';
            
            item.innerHTML = `
                <div class="ticket-item-header">
                    <div class="ticket-item-id">${ticket.ticket_id}</div>
                    <span class="badge ${badgeClass}">${ticket.status}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                    <span class="ticket-item-meta">Lang: ${ticket.original_language.toUpperCase()}</span>
                    <span class="ticket-item-meta">${dateStr}</span>
                </div>
            `;
            
            item.addEventListener('click', () => selectTicket(ticket.ticket_id));
            listContainer.appendChild(item);
        });
    } catch (err) {
        console.error('Error loading ticket history:', err);
    }
}

// Select a ticket to display in chat panel
async function selectTicket(ticketId) {
    // Stop existing polling
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    activeTicketId = ticketId;
    
    // Highlight selected in sidebar
    document.querySelectorAll('.ticket-item').forEach(item => {
        if (item.getAttribute('data-id') === ticketId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // Hide welcome screen
    document.getElementById('chat-welcome-placeholder').style.display = 'none';
    document.getElementById('active-ticket-header').style.display = 'flex';
    document.getElementById('active-ticket-input-area').style.display = 'block';
    
    await refreshConversation();
    
    // Start Polling every 5 seconds for new messages
    pollingInterval = setInterval(refreshConversation, 5000);
}

// Refresh conversation history
async function refreshConversation() {
    if (!activeTicketId) return;
    
    try {
        const res = await apiFetch(`/api/tickets/${activeTicketId}`);
        const ticket = res.ticket;
        const messages = res.messages;
        
        // Update Header UI
        document.getElementById('active-ticket-id').textContent = ticket.ticket_id;
        document.getElementById('active-ticket-lang').textContent = `Language: ${ticket.original_language.toUpperCase()}`;
        
        const statusBadge = document.getElementById('active-ticket-status');
        statusBadge.textContent = ticket.status;
        statusBadge.className = 'badge'; // Reset
        
        let sendInput = document.getElementById('chat-message-input');
        let sendBtn = document.getElementById('send-btn');
        
        if (ticket.status === 'Open') {
            statusBadge.classList.add('badge-open');
            sendInput.disabled = false;
            sendInput.placeholder = "Type your message in any language...";
            sendBtn.disabled = false;
        } else if (ticket.status === 'In Progress') {
            statusBadge.classList.add('badge-progress');
            sendInput.disabled = false;
            sendInput.placeholder = "Type your message in any language...";
            sendBtn.disabled = false;
        } else if (ticket.status === 'Resolved') {
            statusBadge.classList.add('badge-resolved');
            sendInput.disabled = true;
            sendInput.placeholder = "This ticket has been marked as Resolved.";
            sendBtn.disabled = true;
        } else if (ticket.status === 'Closed') {
            statusBadge.classList.add('badge-closed');
            sendInput.disabled = true;
            sendInput.placeholder = "This ticket is Closed.";
            sendBtn.disabled = true;
        }
        
        const dateStr = new Date(ticket.created_at).toLocaleString([], {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        document.getElementById('active-ticket-created').textContent = `Created: ${dateStr}`;
        
        // Load messages stream
        const msgContainer = document.getElementById('chat-messages-container');
        
        // Save current scroll position
        const isAtBottom = msgContainer.scrollHeight - msgContainer.clientHeight <= msgContainer.scrollTop + 50;
        
        // Clean out and render
        msgContainer.innerHTML = '';
        
        messages.forEach(msg => {
            const wrapper = document.createElement('div');
            wrapper.className = `message-wrapper ${msg.sender_type}`;
            
            const timeStr = new Date(msg.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            let senderLabel = 'You';
            let translationFlag = '';
            
            if (msg.sender_type === 'engineer') {
                senderLabel = 'Support Engineer';
                translationFlag = `<span class="message-translation-tag">🛡️ AI Translated response</span>`;
            } else if (msg.sender_type === 'system') {
                senderLabel = 'System Notification';
                translationFlag = `<span class="message-translation-tag">🛡️ AI Translated acknowledgement</span>`;
            }
            
            wrapper.innerHTML = `
                <div class="message-bubble">
                    <p>${escapeHTML(msg.original_text)}</p>
                    ${translationFlag}
                </div>
                <div class="message-meta">
                    <span class="message-label">${senderLabel}</span>
                    <span>${timeStr}</span>
                </div>
            `;
            msgContainer.appendChild(wrapper);
        });
        
        // Auto scroll to bottom
        if (isAtBottom) {
            msgContainer.scrollTop = msgContainer.scrollHeight;
        }
        
    } catch (err) {
        console.error('Error refreshing conversation:', err);
    }
}

// Handle sending message
async function handleSendMessage(e) {
    e.preventDefault();
    if (!activeTicketId) return;
    
    const input = document.getElementById('chat-message-input');
    const text = input.value.trim();
    if (!text) return;
    
    input.value = '';
    
    // Show typing/translating indicator
    document.getElementById('chat-typing-indicator').style.display = 'inline-flex';
    
    try {
        await apiFetch('/api/messages', {
            method: 'POST',
            body: {
                ticket_id: activeTicketId,
                text: text
            }
        });
        
        await refreshConversation();
    } catch (err) {
        console.error('Send message error:', err);
    } finally {
        document.getElementById('chat-typing-indicator').style.display = 'none';
    }
}

// Handle raising a new ticket
async function handleCreateTicket(e) {
    e.preventDefault();
    
    const queryInput = document.getElementById('initial-query-input');
    const query = queryInput.value.trim();
    if (!query) return;
    
    // Close modal immediately and clear input
    closeNewTicketModal();
    queryInput.value = '';
    
    // Show translating indicator
    document.getElementById('chat-typing-indicator').style.display = 'inline-flex';
    
    try {
        const res = await apiFetch('/api/tickets', {
            method: 'POST',
            body: { message: query }
        });
        
        showToast('Ticket raised successfully!');
        
        // Reload list and select
        await loadTicketHistory();
        await selectTicket(res.ticket.ticket_id);
    } catch (err) {
        console.error('Error creating ticket:', err);
    } finally {
        document.getElementById('chat-typing-indicator').style.display = 'none';
    }
}

// Modal Toggle Utilities
function openNewTicketModal() {
    document.getElementById('new-ticket-modal').classList.add('active');
    document.getElementById('initial-query-input').focus();
}

function closeNewTicketModal() {
    document.getElementById('new-ticket-modal').classList.remove('active');
}

// HTML escaping helper
function escapeHTML(str) {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
