// TicketMinds Support Engineer Dashboard Controller

let activeTicketId = null;
let pollingInterval = null;
let allTickets = [];

// Page Load Setup
window.addEventListener('DOMContentLoaded', async () => {
    // 1. Session verification
    const session = await checkSession();
    if (!session.logged_in) {
        window.location.href = '/login?role=engineer';
        return;
    }
    
    if (session.user.role !== 'engineer') {
        window.location.href = '/dashboard/user';
        return;
    }
    
    // Set Profile UI
    document.getElementById('eng-profile-name').textContent = session.user.name;
    document.getElementById('eng-avatar').textContent = session.user.name.charAt(0).toUpperCase();
    
    // 2. Load Tickets queue and Glossary
    await loadTicketQueue();
    await loadGlossaryList();
    
    // 3. Register reply message form listener
    const sendForm = document.getElementById('eng-send-form');
    sendForm.addEventListener('submit', handleSendReply);
});

// Load the engineer's ticket queue
async function loadTicketQueue() {
    try {
        const res = await apiFetch('/api/tickets');
        allTickets = res.tickets || [];
        filterTickets(); // Render based on current filter value
    } catch (err) {
        console.error('Error loading ticket queue:', err);
    }
}

// Filter tickets by status dropdown
function filterTickets() {
    const filter = document.getElementById('status-filter').value;
    const listContainer = document.getElementById('engineer-ticket-list');
    listContainer.innerHTML = '';
    
    const filtered = allTickets.filter(ticket => {
        if (filter === 'ALL') return true;
        return ticket.status === filter;
    });
    
    if (filtered.length === 0) {
        listContainer.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); margin-top: 40px; font-size: 0.85rem; padding: 0 10px;">
                No tickets found for status: "${filter}".
            </div>`;
        return;
    }
    
    filtered.forEach(ticket => {
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
            <div class="ticket-item-email" title="${ticket.user_email}">${ticket.user_email}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                <span class="ticket-item-meta">Original Lang: ${ticket.original_language.toUpperCase()}</span>
                <span class="ticket-item-meta">${dateStr}</span>
            </div>
        `;
        
        item.addEventListener('click', () => selectTicket(ticket.ticket_id));
        listContainer.appendChild(item);
    });
}

// Select a ticket to triage
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
    document.getElementById('eng-welcome-placeholder').style.display = 'none';
    document.getElementById('eng-ticket-header').style.display = 'flex';
    document.getElementById('eng-input-area').style.display = 'block';
    
    await refreshConversation();
    
    // Start Polling every 5 seconds for new messages and AI suggestions
    pollingInterval = setInterval(refreshConversation, 5000);
}

// Refresh conversation history and AI panels
async function refreshConversation() {
    if (!activeTicketId) return;
    
    try {
        const res = await apiFetch(`/api/tickets/${activeTicketId}`);
        const ticket = res.ticket;
        const messages = res.messages;
        const ai = res.ai_suggestions || {};
        
        // Update Header UI
        document.getElementById('eng-active-id').textContent = ticket.ticket_id;
        document.getElementById('eng-active-lang').textContent = `Orig Lang: ${ticket.original_language.toUpperCase()}`;
        
        const dateStr = new Date(ticket.created_at).toLocaleString([], {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        document.getElementById('eng-active-meta').textContent = `User: ${ticket.user_email} | Created: ${dateStr}`;
        
        // Update Status Dropdown value
        document.getElementById('eng-status-dropdown').value = ticket.status;
        
        // Handle input area state based on ticket status
        const replyInput = document.getElementById('eng-message-input');
        const replyBtn = document.getElementById('eng-send-btn');
        if (ticket.status === 'Resolved' || ticket.status === 'Closed') {
            replyInput.disabled = true;
            replyInput.placeholder = `Ticket is currently marked as ${ticket.status}. Reopen or select Open status to reply.`;
            replyBtn.disabled = true;
        } else {
            replyInput.disabled = false;
            replyInput.placeholder = "Type reply in English... (system auto-translates back to user's language)";
            replyBtn.disabled = false;
        }
        
        // Load messages stream (English view for engineers)
        const msgContainer = document.getElementById('eng-messages-container');
        
        // Save scroll state
        const isAtBottom = msgContainer.scrollHeight - msgContainer.clientHeight <= msgContainer.scrollTop + 50;
        
        msgContainer.innerHTML = '';
        
        messages.forEach(msg => {
            const wrapper = document.createElement('div');
            wrapper.className = `message-wrapper ${msg.sender_type}`;
            
            const timeStr = new Date(msg.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
            });
            
            let senderLabel = 'Customer';
            let messageContentHtml = `<p>${escapeHTML(msg.translated_text)}</p>`; // English text for engineers
            
            if (msg.sender_type === 'engineer') {
                senderLabel = 'You (Support Engineer)';
                // Append original native language version as subtitle if desired (translated reply)
                messageContentHtml += `
                    <div class="message-translation-tag" title="Translated output sent to customer">
                        🌐 Sent as: ${escapeHTML(msg.original_text)}
                    </div>`;
            } else if (msg.sender_type === 'system') {
                senderLabel = 'System Auto-Acknowledgement';
                messageContentHtml += `
                    <div class="message-translation-tag">
                        🌐 Sent as: ${escapeHTML(msg.original_text)}
                    </div>`;
            } else {
                // User message: Show English translation, but allow engineer to view original native text
                if (ticket.original_language !== 'en') {
                    messageContentHtml += `
                        <div class="message-translation-tag" title="User's original typed message">
                            👤 Original (${ticket.original_language.toUpperCase()}): ${escapeHTML(msg.original_text)}
                        </div>`;
                }
            }
            
            wrapper.innerHTML = `
                <div class="message-bubble">
                    ${messageContentHtml}
                </div>
                <div class="message-meta">
                    <span class="message-label">${senderLabel}</span>
                    <span>${timeStr}</span>
                </div>
            `;
            msgContainer.appendChild(wrapper);
        });
        
        // Auto scroll
        if (isAtBottom) {
            msgContainer.scrollTop = msgContainer.scrollHeight;
        }
        
        // Update AI Suggestions Sidebar
        const aiArea = document.getElementById('ai-content-area');
        if (ai.summary && ai.suggested_reply) {
            aiArea.innerHTML = `
                <div class="ai-card">
                    <div class="ai-card-title">💡 Issue Summary</div>
                    <p style="margin-bottom: 15px;">${escapeHTML(ai.summary)}</p>
                    
                    <div class="ai-card-title">✨ AI Suggested Reply (English)</div>
                    <p>Click the suggestion below to auto-fill the response box:</p>
                    <div class="suggested-reply-text" onclick="fillSuggestedReply(this.textContent)">${escapeHTML(ai.suggested_reply)}</div>
                </div>
            `;
        } else {
            aiArea.innerHTML = `
                <div style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 20px 0;">
                    No AI suggestions generated yet.
                </div>`;
        }
        
    } catch (err) {
        console.error('Error refreshing conversation:', err);
    }
}

// Copy suggested reply to input form
function fillSuggestedReply(text) {
    const input = document.getElementById('eng-message-input');
    input.value = text;
    input.focus();
    showToast('Suggested reply pasted into composer!');
}

// Handle sending engineer reply
async function handleSendReply(e) {
    e.preventDefault();
    if (!activeTicketId) return;
    
    const input = document.getElementById('eng-message-input');
    const text = input.value.trim();
    if (!text) return;
    
    input.value = '';
    
    document.getElementById('eng-typing-indicator').style.display = 'inline-flex';
    
    try {
        await apiFetch('/api/messages', {
            method: 'POST',
            body: {
                ticket_id: activeTicketId,
                text: text
            }
        });
        
        // Reload queues in background to reflect status transition to In Progress if it was Open
        await loadTicketQueue();
        await refreshConversation();
    } catch (err) {
        console.error('Send reply error:', err);
    } finally {
        document.getElementById('eng-typing-indicator').style.display = 'none';
    }
}

// Handle updating ticket status manually
async function updateTicketStatus() {
    if (!activeTicketId) return;
    
    const dropdown = document.getElementById('eng-status-dropdown');
    const newStatus = dropdown.value;
    
    try {
        await apiFetch(`/api/tickets/${activeTicketId}/status`, {
            method: 'PUT',
            body: { status: newStatus }
        });
        
        showToast(`Ticket status updated to ${newStatus}`);
        
        // Reload lists and refresh view
        await loadTicketQueue();
        await refreshConversation();
    } catch (err) {
        console.error('Error updating status:', err);
    }
}

// Load protected glossary terms list
async function loadGlossaryList() {
    try {
        const glossary = await apiFetch('/api/tickets/glossary');
        const listContainer = document.getElementById('glossary-tag-list');
        listContainer.innerHTML = '';
        
        const keys = Object.keys(glossary);
        if (keys.length === 0) {
            listContainer.innerHTML = '<span style="font-size: 0.8rem; color: var(--text-muted);">Glossary is empty.</span>';
            return;
        }
        
        keys.forEach(key => {
            const tag = document.createElement('div');
            tag.className = 'glossary-tag';
            tag.innerHTML = `<span>🔑</span> <strong>${key}</strong>`;
            tag.title = `Click to insert "${key}" into reply`;
            tag.addEventListener('click', () => {
                const input = document.getElementById('eng-message-input');
                if (!input.disabled) {
                    const cursorPos = input.selectionStart;
                    const textBefore = input.value.substring(0, cursorPos);
                    const textAfter = input.value.substring(input.selectionEnd);
                    input.value = textBefore + key + textAfter;
                    input.focus();
                    const newPos = cursorPos + key.length;
                    input.setSelectionRange(newPos, newPos);
                }
            });
            listContainer.appendChild(tag);
        });
    } catch (err) {
        console.error('Error loading glossary list:', err);
    }
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
