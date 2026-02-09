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
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // DASHBOARD
    // ═══════════════════════════════════════════════════════════════════════

    async function loadDashboard() {
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

        // Load emails
        try {
            const mail = await Bridge.email.list('inbox', null, 3);
            const emailsEl = document.getElementById('dashboardEmails');
            if (mail.emails && mail.emails.length) {
                emailsEl.innerHTML = mail.emails.map((e) => `
                    <div class="list-item" style="border:none;padding:8px 0;">
                        <div class="list-item-content">
                            <div class="list-item-title">${esc(e.subject)}</div>
                            <div class="list-item-subtitle">${esc(e.from)}</div>
                        </div>
                        <div class="list-item-meta">
                            <span class="list-item-time">${e.date || ''}</span>
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
            addChatMessage('assistant', result.response || result.message || JSON.stringify(result));
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
        Bridge.chat.clear().catch(() => {});
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

        try {
            const data = await Bridge.email.list(mailbox, null, 20);
            if (data.emails && data.emails.length) {
                el.innerHTML = data.emails.map((e) => `
                    <div class="list-item" onclick="SortMeOut.viewEmail(${JSON.stringify(e).replace(/"/g, '&quot;')})">
                        <div class="list-item-icon">✉️</div>
                        <div class="list-item-content">
                            <div class="list-item-title">${esc(e.subject || '(No subject)')}</div>
                            <div class="list-item-subtitle">${esc(e.from || '')} — ${esc(e.preview || '')}</div>
                        </div>
                        <div class="list-item-meta">
                            <span class="list-item-time">${esc(e.date || '')}</span>
                        </div>
                    </div>
                `).join('');
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
                el.innerHTML = data.contacts.map((c) => `
                    <div class="contact-card">
                        <div class="contact-avatar">${(c.name || '?')[0].toUpperCase()}</div>
                        <div>
                            <div class="list-item-title">${esc(c.name)}</div>
                            <div class="list-item-subtitle">${esc(c.email || c.phone || '')}</div>
                        </div>
                    </div>
                `).join('');
            } else {
                el.innerHTML = emptyState('👤', 'No contacts found', query ? 'Try a different search' : 'Add your first contact');
            }
        } catch (err) {
            el.innerHTML = emptyState('⚠️', 'Error loading contacts', err.message);
        }
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
        el.innerHTML = emptyState('💬', 'Messages', 'Use the AI assistant to send messages or view recent conversations');
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
            <div class="form-group">
                <label class="form-label">Title</label>
                <input class="form-input" id="presTitle" placeholder="Presentation title">
            </div>
            <div class="form-group">
                <label class="form-label">Slides (describe each slide on a new line)</label>
                <textarea class="form-textarea" id="presSlides" rows="6" placeholder="Title slide: Welcome&#10;Agenda: Topics for today&#10;…"></textarea>
            </div>
        `, [
            { label: 'Cancel', class: 'btn-secondary', action: 'SortMeOut.closeModal()' },
            { label: 'Create', class: 'btn-primary', action: 'SortMeOut.doCreatePresentation()' },
        ]);
    }

    async function doCreatePresentation() {
        const title = document.getElementById('presTitle').value;
        const slideText = document.getElementById('presSlides').value;
        if (!title) return toast('Title is required', 'warning');

        const slides = slideText.split('\n').filter(Boolean).map((line) => {
            const [t, ...b] = line.split(':');
            return { title: t.trim(), body: b.join(':').trim() || '' };
        });

        closeModal();
        toast('Creating presentation in Keynote…', 'info');

        try {
            await Bridge.presentations.create(title, slides);
            toast('Presentation created!', 'success');
        } catch (err) {
            toast('Failed: ' + err.message, 'error');
        }
    }


    // ═══════════════════════════════════════════════════════════════════════
    // FILES
    // ═══════════════════════════════════════════════════════════════════════

    function organizeFolder() {
        navigate('chat');
        setTimeout(() => sendMessage('Organize my Downloads folder'), 100);
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
    }

    function toggleTheme() {
        const dark = document.getElementById('settingDarkMode').checked;
        document.documentElement.dataset.theme = dark ? 'dark' : 'light';
        Bridge.settings.update({ darkMode: dark }).catch(() => {});
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
            const d = new Date(dateStr + 'T00:00:00');
            const today = new Date();
            const tomorrow = new Date(today);
            tomorrow.setDate(tomorrow.getDate() + 1);

            if (d.toDateString() === today.toDateString()) return 'Today';
            if (d.toDateString() === tomorrow.toDateString()) return 'Tomorrow';

            return d.toLocaleDateString(undefined, {
                weekday: 'long', month: 'long', day: 'numeric',
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

        // Messages
        newMessage,
        doNewMessage,

        // Images
        generateImage,
        doGenerateImage,
        editImage,

        // Presentations
        createPresentation,
        doCreatePresentation,

        // Files
        organizeFolder,

        // Rules
        createRule,
        toggleRule,

        // Quick Actions
        quickAction,

        // Settings
        toggleTheme,
        manageWatchFolders,

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
