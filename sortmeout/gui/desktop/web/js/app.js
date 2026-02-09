/**
 * SortMeOut Desktop — Main Application
 *
 * Handles navigation, page logic, AI chat, command palette,
 * modals, toasts, and all UI interactions.
 */

(function () {
    'use strict';

    // ═══════════════════════════════════════════════════════════════════════
    // STATE
    // ═══════════════════════════════════════════════════════════════════════

    const state = {
        currentPage: 'dashboard',
        chatMessages: [],
        chatLoading: false,
        sidebarCollapsed: false,
    };

    // ═══════════════════════════════════════════════════════════════════════
    // NAVIGATION
    // ═══════════════════════════════════════════════════════════════════════

    function navigate(page) {
        if (page === state.currentPage) return;

        // Update sidebar
        document.querySelectorAll('.nav-item').forEach((item) => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        // Update pages
        document.querySelectorAll('.page').forEach((p) => {
            p.classList.toggle('active', p.id === `page-${page}`);
        });

        state.currentPage = page;

        // Load page data
        loadPageData(page);
    }

    function loadPageData(page) {
        switch (page) {
            case 'dashboard': loadDashboard(); break;
            case 'email': loadEmails(); break;
            case 'calendar': loadCalendar(); break;
            case 'notes': loadNotes(); break;
            case 'contacts': loadContacts(); break;
            case 'rules': loadRules(); break;
            case 'settings': loadSettings(); break;
            case 'messages': loadMessages(); break;
            case 'files': loadFileManager(); break;
            case 'images': loadImageGallery(); break;
            case 'presentations': loadPresentations(); break;
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // DASHBOARD
    // ═══════════════════════════════════════════════════════════════════════

    async function loadDashboard() {
        // Apply widget visibility from localStorage
        const hidden = JSON.parse(localStorage.getItem('dashboard_hidden_widgets') || '[]');
        document.querySelectorAll('#page-dashboard [data-widget]').forEach(card => {
            card.style.display = hidden.includes(card.dataset.widget) ? 'none' : '';
        });

        // Update greeting
        const hour = new Date().getHours();
        let greeting = 'Good morning';
        if (hour >= 12 && hour < 17) greeting = 'Good afternoon';
        else if (hour >= 17) greeting = 'Good evening';
        document.querySelector('#page-dashboard .page-title').textContent = `${greeting} 👋`;

        // Load events
        try {
            const cal = await Bridge.calendar.getEvents(3);
            const eventsEl = document.getElementById('dashboardEvents');
            if (cal.events && cal.events.length) {
                eventsEl.innerHTML = cal.events.slice(0, 3).map((e) => `
                    <div class="event-item" style="border:none;background:none;padding:8px 0;">
                        <span class="event-time">${formatTime(e.startDate)}</span>
                        <div>
                            <div class="event-title">${esc(e.summary)}</div>
                            ${e.location ? `<div class="event-location">📍 ${esc(e.location)}</div>` : ''}
                        </div>
                    </div>
                `).join('');
            } else {
                eventsEl.innerHTML = '<p class="text-muted text-sm">No upcoming events</p>';
            }
        } catch (e) {
            document.getElementById('dashboardEvents').innerHTML =
                '<p class="text-muted text-sm">Could not load events</p>';
        }

        // Load emails (using saved account preference)
        try {
            const savedAccount = localStorage.getItem('email_account') || null;
            const mail = await Bridge.email.list('inbox', savedAccount, 3);
            const emailsEl = document.getElementById('dashboardEmails');
            if (mail.emails && mail.emails.length) {
                emailsEl.innerHTML = mail.emails.map((e) => `
                    <div class="list-item" style="border:none;padding:8px 0;">
                        <div class="list-item-content">
                            <div class="list-item-title">${esc(e.subject)}</div>
                            <div class="list-item-subtitle">${esc(e.from || e.sender || '')}</div>
                        </div>
                        <div class="list-item-meta">
                            <span class="list-item-time">${formatDate(e.date)}</span>
                        </div>
                    </div>
                `).join('');
            } else {
                emailsEl.innerHTML = '<p class="text-muted text-sm">No recent emails</p>';
            }
        } catch (e) {
            document.getElementById('dashboardEmails').innerHTML =
                '<p class="text-muted text-sm">Could not load emails</p>';
        }

        // Load rules
        try {
            const rulesData = await Bridge.rules.list();
            const rulesEl = document.getElementById('dashboardRules');
            if (rulesData.rules && rulesData.rules.length) {
                rulesEl.innerHTML = rulesData.rules.slice(0, 3).map((r) => `
                    <div class="list-item" style="border:none;padding:6px 0;">
                        <span class="status-dot ${r.enabled ? 'green' : 'red'}"></span>
                        <div class="list-item-content">
                            <div class="list-item-title">${esc(r.name)}</div>
                            <div class="list-item-subtitle">${r.type} · ${r.folder || r.schedule || ''}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                rulesEl.innerHTML = '<p class="text-muted text-sm">No automation rules</p>';
            }
        } catch (e) {
            document.getElementById('dashboardRules').innerHTML =
                '<p class="text-muted text-sm">Could not load rules</p>';
        }
    }

    function configureDashboard() {
        const widgets = [
            { id: 'quick-actions', label: 'Quick Actions' },
            { id: 'events', label: 'Upcoming Events' },
            { id: 'emails', label: 'Recent Emails' },
            { id: 'rules', label: 'Active Automations' },
            { id: 'status', label: 'System Status' },
        ];
        const hidden = JSON.parse(localStorage.getItem('dashboard_hidden_widgets') || '[]');

        const rows = widgets.map(w => {
            const checked = !hidden.includes(w.id) ? 'checked' : '';
            return `<label style="display:flex;align-items:center;gap:10px;padding:8px 0;cursor:pointer;">
                <input type="checkbox" ${checked} data-wid="${w.id}"
                       style="width:18px;height:18px;accent-color:var(--accent);"/>
                <span>${w.label}</span>
            </label>`;
        }).join('');

        showModal('Configure Dashboard', `
            <p style="margin-bottom:12px;color:var(--text-secondary);">Choose which widgets to show on your dashboard.</p>
            ${rows}
            <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end;">
                <button class="btn btn-secondary" onclick="SortMeOut.closeModal()">Cancel</button>
                <button class="btn btn-primary" onclick="SortMeOut.saveDashboardConfig()">Save</button>
            </div>
        `);
    }

    function saveDashboardConfig() {
        const checkboxes = document.querySelectorAll('.modal [data-wid]');
        const hidden = [];
        checkboxes.forEach(cb => {
            if (!cb.checked) hidden.push(cb.dataset.wid);
        });
        localStorage.setItem('dashboard_hidden_widgets', JSON.stringify(hidden));
        closeModal();
        loadDashboard();
        showToast('Dashboard updated', 'success');
    }


    // ═══════════════════════════════════════════════════════════════════════
    // AI CHAT
    // ═══════════════════════════════════════════════════════════════════════

    async function sendMessage(text) {
        const input = document.getElementById('chatInput');
        const message = text || input.value.trim();
        if (!message || state.chatLoading) return;

        input.value = '';
        autoResizeInput(input);

        // Remove welcome screen
        const welcome = document.querySelector('.chat-welcome');
        if (welcome) welcome.remove();

        // Add user message
        addChatMessage('user', message);

        // Show typing indicator
        state.chatLoading = true;
        const typingEl = addTypingIndicator();

        try {
            const result = await Bridge.chat.send(message);
            typingEl.remove();

            // Extract the actual text — handle every possible error shape
            let reply = '';
            if (result.error) {
                // Convert API-key / technical errors to friendly messages
                const err = result.error;
                if (err.includes('API key') || err.includes('ANTHROPIC')) {
                    reply = '⚠️ AI assistant is not configured yet.\n\nGo to **Settings → AI & API** and paste your Anthropic API key, then click Save.';
                } else {
                    reply = `⚠️ ${err}`;
                }
            } else if (typeof result.response === 'string') {
                reply = result.response;
            } else if (typeof result.response === 'object' && result.response) {
                // Guard against a dict being returned as the response
                reply = result.response.error
                    ? `⚠️ ${result.response.error}`
                    : JSON.stringify(result.response);
            } else {
                reply = result.message || 'No response received.';
            }

            addChatMessage('assistant', reply);
        } catch (err) {
            typingEl.remove();
            addChatMessage('assistant', `Sorry, an error occurred: ${err.message}`);
        } finally {
            state.chatLoading = false;
        }
    }

    function addChatMessage(role, content) {
        const container = document.getElementById('chatMessages');
        const initials = role === 'user' ? 'Y' : 'S';

        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role}`;
        msgDiv.innerHTML = `
            <div class="msg-avatar">${initials}</div>
            <div class="msg-content">${formatMessage(content)}</div>
        `;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;

        state.chatMessages.push({ role, content });
    }

    function addTypingIndicator() {
        const container = document.getElementById('chatMessages');
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="msg-avatar">S</div>
            <div class="msg-content">
                <div class="msg-typing"><span></span><span></span><span></span></div>
            </div>
        `;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div;
    }

    function clearChat() {
        state.chatMessages = [];
        const container = document.getElementById('chatMessages');
        container.innerHTML = `
            <div class="chat-welcome">
                <div class="welcome-icon"><div class="logo-icon large">S</div></div>
                <h2>What can I help you with?</h2>
                <p>I can organize files, send emails, manage your calendar, create images, write notes, and much more.</p>
                <div class="chat-suggestions">
                    <button class="suggestion" onclick="SortMeOut.sendSuggestion('Organize my Downloads folder')">📁 Organize my Downloads</button>
                    <button class="suggestion" onclick="SortMeOut.sendSuggestion('What meetings do I have today?')">📅 Today's meetings</button>
                    <button class="suggestion" onclick="SortMeOut.sendSuggestion('Check my recent emails')">✉️ Recent emails</button>
                    <button class="suggestion" onclick="SortMeOut.sendSuggestion('Generate a landscape image')">🎨 Generate an image</button>
                </div>
            </div>
        `;
        Bridge.chat.clear().catch(() => { });
    }

    function sendSuggestion(text) {
        navigate('chat');
        setTimeout(() => sendMessage(text), 100);
    }

    function formatMessage(text) {
        if (!text) return '';
        // Basic markdown-like formatting
        return text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }


    // ═══════════════════════════════════════════════════════════════════════
    // EMAIL
    // ═══════════════════════════════════════════════════════════════════════

    async function loadEmails(mailbox = 'inbox') {
        const el = document.getElementById('emailList');
        el.innerHTML = loadingSkeleton(4);

        // Populate account picker if not yet done
        const accountSelect = document.getElementById('emailAccountSelect');
        if (accountSelect && accountSelect.options.length <= 1) {
            try {
                const acctData = await Bridge.email.getAccounts();
                if (acctData.accounts && acctData.accounts.length) {
                    acctData.accounts.forEach(name => {
                        const opt = document.createElement('option');
                        opt.value = name;
                        opt.textContent = name;
                        // Pre-select saved preference
                        if (name === localStorage.getItem('email_account')) opt.selected = true;
                        accountSelect.appendChild(opt);
                    });
                }
            } catch (e) { /* ignore */ }
        }

        // Get selected account
        const account = accountSelect ? accountSelect.value || null : null;
        if (account) localStorage.setItem('email_account', account);

        try {
            const data = await Bridge.email.list(mailbox, account, 20);
            if (data.emails && data.emails.length) {
                el.innerHTML = data.emails.map((e) => `
                    <div class="list-item" onclick="SortMeOut.viewEmail(${JSON.stringify(e).replace(/"/g, '&quot;')})">
                        <div class="list-item-icon">${e.read ? '✉️' : '📩'}</div>
                        <div class="list-item-content">
                            <div class="list-item-title" style="${e.read ? '' : 'font-weight:700;'}">${esc(e.subject || '(No subject)')}</div>
                            <div class="list-item-subtitle">${esc(e.from || e.sender || '')}</div>
                        </div>
                        <div class="list-item-meta">
                            <span class="list-item-time">${formatDate(e.date)}</span>
                        </div>
                    </div>
                `).join('');
            } else if (data.error) {
                el.innerHTML = emptyState('⚠️', 'Could not load emails', esc(data.error));
            } else {
                el.innerHTML = emptyState('✉️', 'No emails', 'Your inbox is empty');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading emails', err.message);
        }
    }

    function composeEmail() {
        openModal('Compose Email', `
            <div class="form-group">
                <label class="form-label">To</label>
                <input class="form-input" id="emailTo" placeholder="recipient@example.com">
            </div>
            <div class="form-group">
                <label class="form-label">Subject</label>
                <input class="form-input" id="emailSubject" placeholder="Subject">
            </div>
            <div class="form-group">
                <label class="form-label">Body</label>
                <textarea class="form-textarea" id="emailBody" rows="6" placeholder="Write your email…"></textarea>
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Send', class: 'btn-primary', action: 'SortMeOut.doComposeEmail()' },
        ]);
    }

    async function doComposeEmail() {
        const to = document.getElementById('emailTo').value;
        const subject = document.getElementById('emailSubject').value;
        const body = document.getElementById('emailBody').value;
        if (!to) return toast('Please enter a recipient', 'warning');

        try {
            await Bridge.email.compose(to, subject, body);
            closeModal();
            toast('Email sent successfully', 'success');
        } catch (err) {
            toast('Failed to send: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // CALENDAR
    // ═══════════════════════════════════════════════════════════════════════

    async function loadCalendar() {
        const el = document.getElementById('calendarView');
        el.innerHTML = loadingSkeleton(3);

        try {
            const data = await Bridge.calendar.getEvents(14);
            if (data.events && data.events.length) {
                // Group by date
                const groups = {};
                data.events.forEach((e) => {
                    const date = (e.startDate || '').split('T')[0] || 'Unknown';
                    if (!groups[date]) groups[date] = [];
                    groups[date].push(e);
                });

                el.innerHTML = Object.entries(groups).map(([date, events]) => `
                    <div class="mb-16">
                        <h3 class="text-sm font-bold mb-8" style="color:var(--text-secondary)">${formatDate(date)}</h3>
                        ${events.map((e) => `
                            <div class="event-item">
                                <span class="event-time">${formatTime(e.startDate)}</span>
                                <div>
                                    <div class="event-title">${esc(e.summary)}</div>
                                    ${e.location ? `<div class="event-location">📍 ${esc(e.location)}</div>` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                `).join('');
            } else {
                el.innerHTML = emptyState('📅', 'No upcoming events', 'Your calendar is clear');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading calendar', err.message);
        }
    }

    function addEvent() {
        openModal('New Event', `
            <div class="form-group">
                <label class="form-label">Title</label>
                <input class="form-input" id="eventTitle" placeholder="Meeting with…">
            </div>
            <div class="form-group">
                <label class="form-label">Date</label>
                <input class="form-input" id="eventDate" type="date">
            </div>
            <div class="form-group">
                <label class="form-label">Start Time</label>
                <input class="form-input" id="eventStart" type="time">
            </div>
            <div class="form-group">
                <label class="form-label">End Time</label>
                <input class="form-input" id="eventEnd" type="time">
            </div>
            <div class="form-group">
                <label class="form-label">Location</label>
                <input class="form-input" id="eventLocation" placeholder="Optional">
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Create', class: 'btn-primary', action: 'SortMeOut.doAddEvent()' },
        ]);
    }

    async function doAddEvent() {
        const title = document.getElementById('eventTitle').value;
        const date = document.getElementById('eventDate').value;
        const start = document.getElementById('eventStart').value;
        const end = document.getElementById('eventEnd').value;
        const location = document.getElementById('eventLocation').value;
        if (!title || !date) return toast('Title and date are required', 'warning');

        try {
            await Bridge.calendar.createEvent({
                title,
                start_date: `${date}T${start || '09:00'}`,
                end_date: `${date}T${end || '10:00'}`,
                location,
            });
            closeModal();
            toast('Event created', 'success');
            loadCalendar();
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // NOTES
    // ═══════════════════════════════════════════════════════════════════════

    async function loadNotes() {
        const el = document.getElementById('notesGrid');
        el.innerHTML = loadingSkeleton(3);

        try {
            const data = await Bridge.notes.list();
            if (data.notes && data.notes.length) {
                el.innerHTML = data.notes.map((n) => `
                    <div class="note-card">
                        <div class="note-title">${esc(n.title || 'Untitled')}</div>
                        <div class="note-preview">${esc(n.preview || n.body || '')}</div>
                        <div class="note-date">${esc(n.date || '')}</div>
                    </div>
                `).join('');
            } else {
                el.innerHTML = emptyState('📝', 'No notes yet', 'Create your first note');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading notes', err.message);
        }
    }

    function createNote() {
        openModal('New Note', `
            <div class="form-group">
                <label class="form-label">Title</label>
                <input class="form-input" id="noteTitle" placeholder="Note title">
            </div>
            <div class="form-group">
                <label class="form-label">Content</label>
                <textarea class="form-textarea" id="noteBody" rows="8" placeholder="Start writing…"></textarea>
            </div>
            <div class="form-group">
                <label class="form-label">Folder (optional)</label>
                <input class="form-input" id="noteFolder" placeholder="Notes">
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Create', class: 'btn-primary', action: 'SortMeOut.doCreateNote()' },
        ]);
    }

    async function doCreateNote() {
        const title = document.getElementById('noteTitle').value;
        const body = document.getElementById('noteBody').value;
        const folder = document.getElementById('noteFolder').value;
        if (!title) return toast('Title is required', 'warning');

        try {
            await Bridge.notes.create(title, body, folder || null);
            closeModal();
            toast('Note created', 'success');
            loadNotes();
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // CONTACTS
    // ═══════════════════════════════════════════════════════════════════════

    async function loadContacts(query) {
        const el = document.getElementById('contactsGrid');
        el.innerHTML = loadingSkeleton(4);

        try {
            const data = query
                ? await Bridge.contacts.search(query)
                : await Bridge.contacts.search('');
            if (data.contacts && data.contacts.length) {
                el.innerHTML = data.contacts.map((c) => {
                    const email = (c.emails && c.emails[0]) || c.email || '';
                    const phone = (c.phones && c.phones[0]) || c.phone || '';
                    const detail = email || phone || c.organization || '';
                    return `
                    <div class="contact-card">
                        <div class="contact-avatar">${(c.name || '?')[0].toUpperCase()}</div>
                        <div style="min-width:0;">
                            <div class="list-item-title">${esc(c.name)}</div>
                            ${detail ? `<div class="list-item-subtitle" style="font-size:11px;">${esc(detail)}</div>` : ''}
                        </div>
                    </div>`;
                }).join('');
            } else {
                el.innerHTML = emptyState('👤', 'No contacts found', query ? 'Try a different search' : 'Add your first contact');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading contacts', err.message);
        }
    }

    function openContactsAccountInfo() {
        showModal('Contacts — Synced Accounts', `
            <p style="margin-bottom:12px;">SortMeOut reads contacts from <strong>Apple Contacts.app</strong>,
            which syncs contacts from all your connected Internet Accounts
            (iCloud, Google, Outlook/Hotmail, Exchange, etc.).</p>

            <p style="margin-bottom:12px;">If you see contacts from old or unwanted accounts:</p>
            <ol style="margin-left:18px;margin-bottom:16px;line-height:1.8;">
                <li>Open <strong>System Settings → Internet Accounts</strong></li>
                <li>Select the account you want to disable</li>
                <li>Turn off <strong>Contacts</strong> sync for that account</li>
            </ol>
            <p style="margin-bottom:16px;color:var(--text-secondary);font-size:13px;">
                This will stop those contacts from appearing here and in Contacts.app.</p>
            <div style="display:flex;gap:8px;justify-content:flex-end;">
                <button class="btn btn-secondary" onclick="SortMeOut.closeModal()">Close</button>
                <button class="btn btn-primary" onclick="SortMeOut.openPrivacySettings()">Open System Settings</button>
            </div>
        `);
    }

    function addContact() {
        openModal('Add Contact', `
            <div class="form-group">
                <label class="form-label">First Name</label>
                <input class="form-input" id="contactFirst" placeholder="First name">
            </div>
            <div class="form-group">
                <label class="form-label">Last Name</label>
                <input class="form-input" id="contactLast" placeholder="Last name">
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input class="form-input" id="contactEmail" placeholder="email@example.com">
            </div>
            <div class="form-group">
                <label class="form-label">Phone</label>
                <input class="form-input" id="contactPhone" placeholder="+46…">
            </div>
            <div class="form-group">
                <label class="form-label">Organization</label>
                <input class="form-input" id="contactOrg" placeholder="Optional">
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Save', class: 'btn-primary', action: 'SortMeOut.doAddContact()' },
        ]);
    }

    async function doAddContact() {
        const first = document.getElementById('contactFirst').value;
        const last = document.getElementById('contactLast').value;
        if (!first) return toast('First name is required', 'warning');

        try {
            await Bridge.contacts.create({
                first_name: first,
                last_name: last,
                email: document.getElementById('contactEmail').value,
                phone: document.getElementById('contactPhone').value,
                organization: document.getElementById('contactOrg').value,
            });
            closeModal();
            toast('Contact added', 'success');
            loadContacts();
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // MESSAGES
    // ═══════════════════════════════════════════════════════════════════════

    async function loadMessages() {
        const el = document.getElementById('messagesContainer');
        el.innerHTML = loadingSkeleton(4);

        try {
            // First check permissions
            let perms = null;
            try {
                perms = await Bridge.messages.checkPermissions();
            } catch (e) { /* ignore */ }

            // Try to load recent chats
            const chatsData = await Bridge.messages.getChats(20);
            if (chatsData.chats && chatsData.chats.length) {
                el.innerHTML = `
                    <div class="messages-header" style="padding:0 0 16px 0;">
                        <h3 style="font-size:14px;color:var(--text-secondary);">Recent Conversations</h3>
                    </div>
                ` + chatsData.chats.map((c) => {
                    const name = c.participants ? c.participants.join(', ') : c.id;
                    const safeName = name.replace(/'/g, "\\'");
                    return `
                    <div class="list-item" onclick="SortMeOut.viewConversation('${safeName}')">
                        <div class="list-item-icon">💬</div>
                        <div class="list-item-content">
                            <div class="list-item-title">${esc(name)}</div>
                            <div class="list-item-subtitle">${esc(c.serviceName || 'iMessage')}</div>
                        </div>
                    </div>
                `}).join('');
            } else if (perms && !perms.database_accessible) {
                el.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🔒</div>
                        <h3>Permissions Needed</h3>
                        <p>SortMeOut needs two macOS permissions to work with Messages:</p>
                        <div style="text-align:left;margin:16px auto;max-width:400px;font-size:13px;line-height:1.8;">
                            <p><strong>1. Automation</strong> — allows sending messages via Messages.app</p>
                            <p><strong>2. Full Disk Access</strong> — allows reading message history</p>
                            <p style="margin-top:12px;">Go to <strong>System Settings → Privacy & Security</strong> and add SortMeOut to both.</p>
                        </div>
                        <button class="btn btn-primary" onclick="SortMeOut.openPrivacySettings()" style="margin-top:8px;">Open Privacy Settings</button>
                    </div>
                `;
            } else {
                el.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">💬</div>
                        <h3>No Conversations</h3>
                        <p>Send your first message using the "New Message" button above, or grant Automation permission for Messages.app.</p>
                        <button class="btn btn-secondary" onclick="SortMeOut.openPrivacySettings()" style="margin-top:12px;">Check Permissions</button>
                    </div>
                `;
            }
        } catch (err) {
            el.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">💬</div>
                    <h3>Messages</h3>
                    <p>Could not connect to Messages.app. Make sure iMessage is signed in and SortMeOut has Automation permission.</p>
                    <div style="display:flex;gap:8px;margin-top:16px;justify-content:center;">
                        <button class="btn btn-primary" onclick="SortMeOut.newMessage()">New Message</button>
                        <button class="btn btn-secondary" onclick="SortMeOut.openPrivacySettings()">Check Permissions</button>
                    </div>
                </div>
            `;
        }
    }

    async function viewConversation(contact) {
        const el = document.getElementById('messagesContainer');
        el.innerHTML = loadingSkeleton(6);

        try {
            const data = await Bridge.messages.read(contact, 30);
            if (data.messages && data.messages.length) {
                el.innerHTML = `
                    <div style="display:flex;align-items:center;gap:8px;padding:0 0 16px 0;">
                        <button class="btn btn-secondary btn-sm" onclick="SortMeOut.loadMessages()">← Back</button>
                        <h3 style="font-size:14px;color:var(--text-secondary);">${esc(contact)}</h3>
                    </div>
                    <div class="message-thread">
                        ${data.messages.map((m) => `
                            <div class="thread-msg ${m.is_from_me ? 'sent' : 'received'}">
                                <div class="thread-bubble">${esc(m.text)}</div>
                                <div class="thread-meta">${esc(m.date)} · ${m.is_from_me ? 'You' : esc(m.sender)}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            } else {
                el.innerHTML = `
                    <button class="btn btn-secondary btn-sm" onclick="SortMeOut.loadMessages()">← Back</button>
                    ` + emptyState('💬', 'No messages', 'No messages found with this contact');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error', err.message);
        }
    }

    function newMessage() {
        openModal('New Message', `
            <div class="form-group">
                <label class="form-label">To (phone or contact name)</label>
                <input class="form-input" id="msgTo" placeholder="+46… or name">
            </div>
            <div class="form-group">
                <label class="form-label">Message</label>
                <textarea class="form-textarea" id="msgBody" rows="4" placeholder="Type your message…"></textarea>
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Send', class: 'btn-primary', action: 'SortMeOut.doNewMessage()' },
        ]);
    }

    async function doNewMessage() {
        const to = document.getElementById('msgTo').value;
        const body = document.getElementById('msgBody').value;
        if (!to || !body) return toast('Recipient and message are required', 'warning');

        try {
            await Bridge.messages.send(to, body);
            closeModal();
            toast('Message sent', 'success');
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // RULES / AUTOMATION
    // ═══════════════════════════════════════════════════════════════════════

    async function loadRules() {
        const el = document.getElementById('rulesList');
        el.innerHTML = loadingSkeleton(3);

        try {
            const data = await Bridge.rules.list();
            if (data.rules && data.rules.length) {
                el.innerHTML = data.rules.map((r) => `
                    <div class="list-item">
                        <div class="list-item-icon">⚡</div>
                        <div class="list-item-content">
                            <div class="list-item-title">${esc(r.name)}</div>
                            <div class="list-item-subtitle">${esc(r.type || 'rule')} · ${esc(r.folder || r.schedule || '')}</div>
                        </div>
                        <label class="toggle">
                            <input type="checkbox" ${r.enabled ? 'checked' : ''} onchange="SortMeOut.toggleRule('${esc(r.name)}', this.checked)">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                `).join('');
            } else {
                el.innerHTML = emptyState('⚡', 'No automation rules', 'Create your first rule to auto-organize files');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading rules', err.message);
        }
    }

    function createRule() {
        navigate('chat');
        setTimeout(() => sendMessage('Help me create a new file organization rule'), 100);
    }

    async function toggleRule(name, enabled) {
        try {
            await Bridge.rules.toggle(name, enabled);
            toast(`Rule ${enabled ? 'enabled' : 'disabled'}`, 'success');
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // IMAGES
    // ═══════════════════════════════════════════════════════════════════════

    function generateImage() {
        openModal('Generate Image', `
            <div class="form-group">
                <label class="form-label">Prompt</label>
                <textarea class="form-textarea" id="imgPrompt" rows="3" placeholder="Describe the image you want…"></textarea>
            </div>
            <div class="form-group">
                <label class="form-label">Size</label>
                <select class="form-select" id="imgSize">
                    <option value="1024x1024">1024 × 1024 (Square)</option>
                    <option value="1792x1024">1792 × 1024 (Landscape)</option>
                    <option value="1024x1792">1024 × 1792 (Portrait)</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Quality</label>
                <select class="form-select" id="imgQuality">
                    <option value="hd">HD</option>
                    <option value="standard">Standard</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Style</label>
                <select class="form-select" id="imgStyle">
                    <option value="vivid">Vivid</option>
                    <option value="natural">Natural</option>
                </select>
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Generate', class: 'btn-primary', action: 'SortMeOut.doGenerateImage()' },
        ]);
    }

    async function doGenerateImage() {
        const prompt = document.getElementById('imgPrompt').value;
        if (!prompt) return toast('Please describe the image', 'warning');

        const size = document.getElementById('imgSize').value;
        const quality = document.getElementById('imgQuality').value;
        const style = document.getElementById('imgStyle').value;

        closeModal();
        toast('Generating image with DALL·E 3…', 'info');

        try {
            const result = await Bridge.images.generate(prompt, size, quality, style);
            toast('Image generated successfully!', 'success');
            // Refresh gallery if on images page
            if (state.currentPage === 'images') {
                loadImageGallery();
            }
        } catch (err) {
            toast('Generation failed: ' + err.message, 'error');
        }
    }

    function editImage() {
        navigate('chat');
        setTimeout(() => sendMessage('I want to edit an image'), 100);
    }


    // ═══════════════════════════════════════════════════════════════════════
    // PRESENTATIONS
    // ═══════════════════════════════════════════════════════════════════════

    function createPresentation() {
        openModal('New Presentation', `
            <p style="font-size:12px;color:var(--text-tertiary);margin-bottom:16px;">Creates a .pptx presentation and opens it in Keynote. Describe your slides below — one per line.</p>
            <div class="form-group">
                <label class="form-label">Presentation Title</label>
                <input class="form-input" id="presTitle" placeholder="Q1 Review, Team Update…">
            </div>
            <div class="form-group">
                <label class="form-label">Subtitle / Author (optional)</label>
                <input class="form-input" id="presSubtitle" placeholder="Your Name or Team">
            </div>
            <div class="form-group">
                <label class="form-label">Slides</label>
                <p style="font-size:11px;color:var(--text-tertiary);margin-bottom:6px;">Format: <code>Slide Title: bullet point 1, bullet point 2</code></p>
                <textarea class="form-textarea" id="presSlides" rows="8" placeholder="Introduction: Welcome to the presentation&#10;Problem: Current challenges we face&#10;Solution: Our proposed approach&#10;Timeline: Key milestones and dates&#10;Next Steps: Action items for the team"></textarea>
            </div>
            <div class="form-group">
                <label class="form-label">Generate with AI (optional)</label>
                <input class="form-input" id="presAiPrompt" placeholder="e.g. Create a 5-slide pitch deck about…">
                <button class="btn btn-sm btn-secondary" onclick="SortMeOut.aiGenerateSlides()" style="margin-top:6px;">✨ Generate Slides with AI</button>
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Create Presentation', class: 'btn-primary', action: 'SortMeOut.doCreatePresentation()' },
        ]);
    }

    async function doCreatePresentation() {
        const title = document.getElementById('presTitle').value;
        const slideText = document.getElementById('presSlides').value;
        if (!title) return toast('Title is required', 'warning');

        const slides = slideText.split('\n').filter(Boolean).map((line) => {
            const [t, ...b] = line.split(':');
            const body = b.join(':').trim();
            // Parse comma-separated bullets into proper content
            const bullets = body ? body.split(',').map(s => s.trim()).filter(Boolean) : [];
            return {
                title: t.trim(),
                body: body,
                content: bullets.join('\n'),
                layout: 'bullets',
            };
        });

        closeModal();
        toast('Creating presentation — will open in Keynote…', 'info');

        try {
            const result = await Bridge.presentations.create(title, slides);
            if (result.error) {
                toast('Failed: ' + result.error, 'error');
            } else {
                toast('Presentation created and opened in Keynote!', 'success');
            }
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }

    async function aiGenerateSlides() {
        const prompt = document.getElementById('presAiPrompt')?.value;
        if (!prompt) return toast('Enter a prompt to generate slides', 'warning');

        toast('Generating slides with AI…', 'info');
        try {
            const result = await Bridge.chat.send(`Create a presentation outline for: ${prompt}. Format each slide as "Title: Content" on separate lines. Only output the slide lines, nothing else.`);
            const reply = result.response || '';
            // Fill the slides textarea with the AI-generated outline
            const slidesEl = document.getElementById('presSlides');
            if (slidesEl && reply) {
                slidesEl.value = reply;
                toast('Slides generated — review and click Create', 'success');
            }
        } catch (err) {
            toast('AI generation failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // FILES
    // ═══════════════════════════════════════════════════════════════════════

    // ── File Manager ──

    async function loadFileManager(path) {
        const dir = path || window._currentFilePath || (typeof require !== 'undefined' ? require('os').homedir() : '/Users');
        window._currentFilePath = dir;
        const el = document.getElementById('fileGrid');
        el.innerHTML = loadingSkeleton(6);

        // Update breadcrumb
        const bc = document.getElementById('fileBreadcrumb');
        const parts = dir.split('/').filter(Boolean);
        bc.innerHTML = parts.map((p, i) => {
            const fullPath = '/' + parts.slice(0, i + 1).join('/');
            return `<span class="crumb ${i === parts.length - 1 ? 'active' : ''}" onclick="SortMeOut.browseFolder('${fullPath}')">${esc(p)}</span>`;
        }).join(' <span class="crumb-sep">/</span> ');

        try {
            const data = await Bridge.files.list(dir);
            if (data.files && data.files.length) {
                el.innerHTML = data.files.map((f) => `
                    <div class="file-card ${f.is_dir ? 'folder' : 'file'}"
                         onclick="${f.is_dir ? `SortMeOut.browseFolder('${f.path.replace(/'/g, "\\'")}')` : `SortMeOut.openFile('${f.path.replace(/'/g, "\\'")}')`}">
                        <div class="file-icon">${f.is_dir ? '📁' : fileIcon(f.name)}</div>
                        <div class="file-name">${esc(f.name)}</div>
                        <div class="file-meta">${f.is_dir ? '' : formatFileSize(f.size)}</div>
                    </div>
                `).join('');
            } else {
                el.innerHTML = emptyState('📁', 'Empty folder', 'This folder has no files');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading files', err.message);
        }
    }

    function browseFolder(path) {
        window._currentFilePath = path;
        loadFileManager(path);
    }

    function openFile(path) {
        Bridge.system.openFile(path).catch(() => { });
    }

    function fileIcon(name) {
        const ext = (name.split('.').pop() || '').toLowerCase();
        const icons = {
            pdf: '📄', doc: '📝', docx: '📝', txt: '📄', md: '📝',
            jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', webp: '🖼️', svg: '🖼️',
            mp3: '🎵', wav: '🎵', mp4: '🎬', mov: '🎬', avi: '🎬',
            zip: '📦', dmg: '📦', tar: '📦', gz: '📦',
            py: '🐍', js: '⚡', html: '🌐', css: '🎨', json: '📋',
            xls: '📊', xlsx: '📊', csv: '📊', pptx: '📊', key: '📊',
        };
        return icons[ext] || '📄';
    }

    function formatFileSize(bytes) {
        if (!bytes) return '';
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        let size = bytes;
        while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
        return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
    }

    function organizeFolder() {
        navigate('chat');
        setTimeout(() => sendMessage('Organize my Downloads folder'), 100);
    }

    // ── Image Gallery ──

    async function loadImageGallery() {
        const el = document.getElementById('imagesGallery');
        el.innerHTML = loadingSkeleton(4);

        try {
            const data = await Bridge.images.listGallery();
            if (data.images && data.images.length) {
                el.innerHTML = '<div class="gallery-grid">' + data.images.map((img) => `
                    <div class="gallery-card" onclick="SortMeOut.openFile('${img.path.replace(/'/g, "\\'")}')">
                        <div class="gallery-thumb" style="background-image:url('file://${img.path}')"></div>
                        <div class="gallery-info">
                            <span class="gallery-name">${esc(img.name)}</span>
                            <span class="gallery-size">${formatFileSize(img.size)}</span>
                        </div>
                    </div>
                `).join('') + '</div>';
            } else {
                el.innerHTML = emptyState('🎨', 'No images yet', 'Generate your first image with DALL·E 3');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading gallery', err.message);
        }
    }

    // ── Presentations ──

    async function loadPresentations() {
        const el = document.getElementById('presentationsGrid');
        // List any existing presentations from ~/Documents/Presentations/
        try {
            const data = await Bridge.files.list(null, '~/Documents/Presentations');
            const pptxFiles = (data.files || []).filter(f => f.name.endsWith('.pptx') || f.name.endsWith('.key'));
            if (pptxFiles.length > 0) {
                el.innerHTML = pptxFiles.map(f => `
                    <div class="file-card" onclick="SortMeOut.openFile('${f.path.replace(/'/g, "\\\'")}')">
                        <div class="file-icon">📊</div>
                        <div class="file-name">${esc(f.name)}</div>
                        <div class="file-meta">${formatFileSize(f.size)}</div>
                    </div>
                `).join('');
            } else {
                el.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">📊</div>
                        <h3>Presentations</h3>
                        <p>Create presentations using the button above. SortMeOut generates <strong>.pptx</strong> files and opens them in <strong>Apple Keynote</strong>.</p>
                        <p style="font-size:12px;color:var(--text-tertiary);margin-top:8px;">You can also use the AI assistant to generate a presentation from a description.</p>
                    </div>
                `;
            }
        } catch (e) {
            el.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <h3>Presentations</h3>
                    <p>Create presentations using the button above. SortMeOut generates <strong>.pptx</strong> files and opens them in <strong>Apple Keynote</strong>.</p>
                </div>
            `;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // SETTINGS
    // ═══════════════════════════════════════════════════════════════════════

    async function loadSettings() {
        try {
            const data = await Bridge.settings.get();
            if (data.darkMode !== undefined) {
                document.getElementById('settingDarkMode').checked = data.darkMode;
            }
            if (data.model) {
                document.getElementById('settingModel').value = data.model;
            }
        } catch (e) {
            // Use defaults
        }

        // Load API key status
        try {
            const keys = await Bridge.settings.getApiKeys();
            const antEl = document.getElementById('settingAnthropicKey');
            const oaiEl = document.getElementById('settingOpenAIKey');
            if (keys.anthropic) antEl.placeholder = '••••••••••••• (configured)';
            if (keys.openai) oaiEl.placeholder = '••••••••••••• (configured)';
        } catch (e) { }

        // Populate email account picker in settings
        try {
            const acctData = await Bridge.email.getAccounts();
            const sel = document.getElementById('settingEmailAccount');
            if (sel && acctData.accounts) {
                // Clear existing options except first
                while (sel.options.length > 1) sel.remove(1);
                const saved = localStorage.getItem('email_account') || '';
                acctData.accounts.forEach(name => {
                    const opt = document.createElement('option');
                    opt.value = name;
                    opt.textContent = name;
                    if (name === saved) opt.selected = true;
                    sel.appendChild(opt);
                });
                // Sync to email page selector too
                sel.onchange = () => {
                    const val = sel.value;
                    localStorage.setItem('email_account', val);
                    const pageSelect = document.getElementById('emailAccountSelect');
                    if (pageSelect) pageSelect.value = val;
                    toast('Default email account updated', 'success');
                };
            }
        } catch (e) { /* ignore */ }

        // Check integration status
        checkIntegrations();
    }

    async function checkIntegrations() {
        try {
            const status = await Bridge.settings.checkIntegrations();
            const map = {
                mail: 'intStatusMail',
                messages: 'intStatusMessages',
                calendar: 'intStatusCalendar',
                contacts: 'intStatusContacts',
                notes: 'intStatusNotes',
                images: 'intStatusImages',
                presentations: 'intStatusPres',
            };
            for (const [key, elId] of Object.entries(map)) {
                const el = document.getElementById(elId);
                if (!el) continue;
                const info = status[key];
                if (info && info.available) {
                    el.textContent = '✅ Ready';
                    el.style.color = 'var(--success)';
                } else {
                    el.textContent = `⚠️ ${(info && info.status) || 'Not available'}`;
                    el.style.color = 'var(--warning)';
                }
            }
        } catch (e) {
            // Leave as "Checking…"
        }
    }

    async function saveApiKey(provider) {
        const inputId = provider === 'anthropic' ? 'settingAnthropicKey' : 'settingOpenAIKey';
        const key = document.getElementById(inputId).value.trim();
        if (!key) return toast('Please enter an API key', 'warning');

        try {
            const result = await Bridge.settings.saveApiKey(provider, key);
            if (result.success) {
                toast(`${provider === 'anthropic' ? 'Anthropic' : 'OpenAI'} API key saved!`, 'success');
                document.getElementById(inputId).value = '';
                document.getElementById(inputId).placeholder = '••••••••••••• (configured)';
                // Recheck integrations
                checkIntegrations();
            } else {
                toast(result.error || 'Failed to save key', 'error');
            }
        } catch (err) {
            toast('Failed to save: ' + err.message, 'error');
        }
    }

    function openPrivacySettings() {
        Bridge.system.openPrivacySettings().catch(() => { });
        toast('Opening System Settings → Privacy & Security…', 'info');
    }

    function toggleTheme() {
        const dark = document.getElementById('settingDarkMode').checked;
        document.documentElement.dataset.theme = dark ? 'dark' : 'light';
        Bridge.settings.update({ darkMode: dark }).catch(() => { });
    }

    function manageWatchFolders() {
        navigate('chat');
        setTimeout(() => sendMessage('Show me my watch folders and help me manage them'), 100);
    }


    // ═══════════════════════════════════════════════════════════════════════
    // QUICK ACTIONS
    // ═══════════════════════════════════════════════════════════════════════

    function quickAction(type) {
        switch (type) {
            case 'organize':
                navigate('chat');
                sendMessage('Organize my Downloads folder');
                break;
            case 'email':
                navigate('email');
                composeEmail();
                break;
            case 'event':
                navigate('calendar');
                addEvent();
                break;
            case 'note':
                navigate('notes');
                createNote();
                break;
            case 'image':
                navigate('images');
                generateImage();
                break;
            case 'presentation':
                navigate('presentations');
                createPresentation();
                break;
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // MODAL SYSTEM
    // ═══════════════════════════════════════════════════════════════════════

    function openModal(title, bodyHtml, buttons = []) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalBody').innerHTML = bodyHtml;
        document.getElementById('modalFooter').innerHTML = buttons.map((b) =>
            `<button class="btn ${b.class}" onclick="${b.action}">${b.label}</button>`
        ).join('');
        document.getElementById('modalOverlay').classList.add('active');

        // Focus first input
        setTimeout(() => {
            const firstInput = document.querySelector('#modalBody input, #modalBody textarea');
            if (firstInput) firstInput.focus();
        }, 100);
    }

    function closeModal() {
        document.getElementById('modalOverlay').classList.remove('active');
    }


    // ═══════════════════════════════════════════════════════════════════════
    // TOASTS
    // ═══════════════════════════════════════════════════════════════════════

    function toast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const el = document.createElement('div');
        el.className = `toast ${type}`;
        el.textContent = message;
        container.appendChild(el);

        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(16px)';
            setTimeout(() => el.remove(), 300);
        }, 4000);
    }


    // ═══════════════════════════════════════════════════════════════════════
    // COMMAND PALETTE (⌘K)
    // ═══════════════════════════════════════════════════════════════════════

    const COMMANDS = [
        { icon: '🏠', label: 'Go to Dashboard', action: () => navigate('dashboard') },
        { icon: '💬', label: 'Open AI Chat', action: () => navigate('chat') },
        { icon: '📁', label: 'File Manager', action: () => navigate('files') },
        { icon: '⚡', label: 'Automation Rules', action: () => navigate('rules') },
        { icon: '✉️', label: 'Email', action: () => navigate('email') },
        { icon: '💬', label: 'Messages', action: () => navigate('messages') },
        { icon: '👤', label: 'Contacts', action: () => navigate('contacts') },
        { icon: '📅', label: 'Calendar', action: () => navigate('calendar') },
        { icon: '📝', label: 'Notes', action: () => navigate('notes') },
        { icon: '📊', label: 'Presentations', action: () => navigate('presentations') },
        { icon: '🎨', label: 'Images', action: () => navigate('images') },
        { icon: '⚙️', label: 'Settings', action: () => navigate('settings') },
        { icon: '✉️', label: 'Compose Email', action: () => { navigate('email'); composeEmail(); } },
        { icon: '📅', label: 'Create Event', action: () => { navigate('calendar'); addEvent(); } },
        { icon: '📝', label: 'Create Note', action: () => { navigate('notes'); createNote(); } },
        { icon: '🎨', label: 'Generate Image', action: () => { navigate('images'); generateImage(); } },
        { icon: '📊', label: 'Create Presentation', action: () => { navigate('presentations'); createPresentation(); } },
        { icon: '👤', label: 'Add Contact', action: () => { navigate('contacts'); addContact(); } },
        { icon: '📁', label: 'Organize Downloads', action: () => sendSuggestion('Organize my Downloads folder') },
        { icon: '🔄', label: 'Clear Chat', action: () => clearChat() },
    ];

    function openCommandPalette() {
        document.getElementById('cmdPaletteOverlay').classList.add('active');
        const input = document.getElementById('cmdInput');
        input.value = '';
        input.focus();
        renderCommands('');
    }

    function closeCommandPalette() {
        document.getElementById('cmdPaletteOverlay').classList.remove('active');
    }

    function renderCommands(query) {
        const filtered = query
            ? COMMANDS.filter((c) => c.label.toLowerCase().includes(query.toLowerCase()))
            : COMMANDS;

        const el = document.getElementById('cmdResults');
        el.innerHTML = filtered.map((c, i) => `
            <div class="cmd-item ${i === 0 ? 'active' : ''}" onclick="SortMeOut._execCommand(${COMMANDS.indexOf(c)})">
                <span class="cmd-item-icon">${c.icon}</span>
                <span class="cmd-item-label">${c.label}</span>
            </div>
        `).join('');
    }

    function execCommand(index) {
        closeCommandPalette();
        COMMANDS[index].action();
    }


    // ═══════════════════════════════════════════════════════════════════════
    // SIDEBAR
    // ═══════════════════════════════════════════════════════════════════════

    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        state.sidebarCollapsed = !state.sidebarCollapsed;
        sidebar.classList.toggle('collapsed', state.sidebarCollapsed);
    }


    // ═══════════════════════════════════════════════════════════════════════
    // UTILITIES
    // ═══════════════════════════════════════════════════════════════════════

    function esc(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function formatTime(dateStr) {
        if (!dateStr) return '';
        try {
            const d = new Date(dateStr);
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return dateStr;
        }
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            // Handle both "2026-02-09" and "2026-02-09T03:31:41.000Z" formats
            const d = new Date(dateStr.includes('T') ? dateStr : dateStr + 'T00:00:00');
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);

            if (d.toDateString() === today.toDateString()) return 'Today';
            if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
            if (d.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

            return d.toLocaleDateString(undefined, {
                weekday: 'short', month: 'short', day: 'numeric',
            });
        } catch {
            return dateStr;
        }
    }

    function loadingSkeleton(count = 3) {
        return '<div class="loading-skeleton">' +
            Array(count).fill('<div class="skeleton-card"></div>').join('') +
            '</div>';
    }

    function emptyState(icon, title, desc) {
        return `<div class="empty-state"><div class="empty-icon">${icon}</div><h3>${title}</h3><p>${desc}</p></div>`;
    }

    function autoResizeInput(el) {
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }


    // ═══════════════════════════════════════════════════════════════════════
    // EVENT LISTENERS
    // ═══════════════════════════════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', () => {
        // Sidebar navigation
        document.querySelectorAll('.nav-item[data-page]').forEach((item) => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                navigate(item.dataset.page);
            });
        });

        // Sidebar toggle
        document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);

        // Chat input
        const chatInput = document.getElementById('chatInput');
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                sendMessage();
            }
            // Shift+Enter for newline (default behavior)
            if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        chatInput.addEventListener('input', () => autoResizeInput(chatInput));

        // Command palette (⌘K)
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                openCommandPalette();
            }
            if (e.key === 'Escape') {
                closeCommandPalette();
                closeModal();
            }
        });

        // Command palette search
        document.getElementById('cmdInput').addEventListener('input', (e) => {
            renderCommands(e.target.value);
        });

        document.getElementById('cmdInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const active = document.querySelector('.cmd-item.active');
                if (active) active.click();
            }
        });

        // Global search
        document.getElementById('globalSearch').addEventListener('focus', () => {
            openCommandPalette();
        });

        // Contact search
        const contactSearch = document.getElementById('contactSearch');
        if (contactSearch) {
            let timer;
            contactSearch.addEventListener('input', (e) => {
                clearTimeout(timer);
                timer = setTimeout(() => loadContacts(e.target.value), 300);
            });
        }

        // Email tabs
        document.querySelectorAll('.email-tabs .tab').forEach((tab) => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.email-tabs .tab').forEach((t) => t.classList.remove('active'));
                tab.classList.add('active');
                loadEmails(tab.dataset.tab);
            });
        });

        // Load dashboard data
        loadDashboard();
    });


    // ═══════════════════════════════════════════════════════════════════════
    // PUBLIC API — window.SortMeOut
    // ═══════════════════════════════════════════════════════════════════════

    window.SortMeOut = {
        // Navigation
        navigate,

        // Chat
        sendMessage,
        clearChat,
        sendSuggestion,
        attachFile: () => toast('Upload coming soon — tell AI what file to use', 'info'),

        // Email
        loadEmails: () => loadEmails(),
        composeEmail,
        doComposeEmail,
        viewEmail: (email) => { navigate('chat'); sendMessage(`Show me the email: "${email.subject}" from ${email.from}`); },

        // Calendar
        addEvent,
        doAddEvent,

        // Notes
        createNote,
        doCreateNote,

        // Contacts
        addContact,
        doAddContact,
        openContactsAccountInfo,

        // Messages
        newMessage,
        doNewMessage,
        viewConversation,
        loadMessages: () => loadMessages(),

        // Images
        generateImage,
        doGenerateImage,
        editImage,

        // Presentations
        createPresentation,
        doCreatePresentation,
        aiGenerateSlides,

        // Files
        organizeFolder,
        browseFolder,
        openFile,

        // Rules
        createRule,
        toggleRule,

        // Quick Actions
        quickAction,

        // Dashboard
        configureDashboard,
        saveDashboardConfig,

        // Settings
        toggleTheme,
        manageWatchFolders,
        saveApiKey,
        openPrivacySettings,

        // Modal
        closeModal,

        // Command Palette
        openCommandPalette,
        closeCommandPalette,
        _execCommand: execCommand,

        // Toast
        toast,
    };

})();
