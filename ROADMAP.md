# SortMeOut — Product Roadmap

> A clear path from current state to polished, shippable product.

---

## Vision

SortMeOut is a native macOS AI-powered personal assistant that deeply integrates with Apple's ecosystem (Mail, Calendar, Contacts, Messages, Notes, Keynote) and adds intelligent file organization, image generation, and workflow automation — all from a single beautiful desktop app.

---

## Current State (v0.9-beta)

| Feature | Status | Notes |
|---------|--------|-------|
| AI Chat (Claude) | ✅ Working | Requires API key in Settings |
| File Manager | ✅ Working | Browse, organize, rule-based automation |
| Calendar | ✅ Working | Read/create events via Calendar.app |
| Notes | ✅ Working | Read/create via Notes.app |
| Email | ✅ Working | Read/compose via Mail.app |
| Contacts | ✅ Working | Read/add via Contacts.app |
| Messages | ⚠️ Permissions | Requires Automation + Full Disk Access |
| Image Gen | ⚠️ API key | Requires OpenAI API key |
| Presentations | ✅ Working | Creates .pptx, opens in Keynote |
| Dashboard | ✅ Working | Configurable widget visibility |
| Automation Rules | ✅ Working | Extension-based, folder-watching, scheduled |
| Desktop App | ✅ Built | PyObjC + WKWebView, .app + .dmg |
| Settings | ✅ Working | Theme, API keys, integration status |

---

## Phase 1 — Polish & Stability (Current → v1.0)

**Goal:** Make every existing feature reliable and user-friendly.

### 1.1 First-Run Experience

- [ ] Onboarding wizard: welcome → set API key → grant permissions → pick watch folders
- [ ] Auto-detect existing API keys from `.env` and environment
- [ ] Show permission status on onboarding (Automation, Full Disk Access, Contacts)
- [ ] "Setup Complete" confirmation with dashboard preview

### 1.2 Error Handling & Feedback

- [ ] Replace all raw JSON/error displays with friendly user messages
- [ ] Add retry buttons for failed operations
- [ ] Loading spinners for all async operations
- [ ] Toast notifications for background successes/failures
- [ ] Graceful degradation when macOS permissions are missing

### 1.3 AI Chat Improvements

- [ ] Conversation history persistence (save to SQLite)
- [ ] Multi-conversation support (sidebar with chat list)
- [ ] Stream responses (typing effect)
- [ ] Markdown rendering in chat (code blocks, tables, lists)
- [ ] Context-aware suggestions based on current page
- [ ] File/image attachment support

### 1.4 Integration Hardening

- [ ] Messages: auto-detect permissions and guide user through granting them
- [ ] Calendar: recurring event support
- [ ] Email: folder browsing (Inbox, Sent, Drafts, custom)
- [ ] Contacts: search + edit + groups
- [ ] Notes: folder support + rich text editing
- [ ] Presentations: template selection, theme picker, more slide layouts

### 1.5 Settings & Configuration

- [ ] Per-feature settings (e.g., default calendar, default mail account)
- [ ] Dashboard widget ordering (drag & drop)
- [ ] Notification preferences (which actions should notify)
- [ ] Data export/backup (rules, settings, chat history)
- [ ] Keyboard shortcut customization

---

## Phase 2 — Intelligence & Automation (v1.1)

**Goal:** Make the AI proactive and the automation powerful.

### 2.1 Smart Automation

- [ ] AI-suggested rules ("You often move PDFs to Documents — want a rule?")
- [ ] Time-based rule triggers (schedule: daily, weekly, on login)
- [ ] Chained actions (move file → rename → tag → notify)
- [ ] Condition builder UI (visual drag-drop rule editor)
- [ ] Template library (pre-built rules for common workflows)

### 2.2 Proactive AI

- [ ] Daily briefing (summarize calendar + emails + tasks on app open)
- [ ] Smart inbox triage (AI categorizes and prioritizes emails)
- [ ] Meeting prep (gather relevant files/notes before calendar events)
- [ ] Follow-up reminders (detect "I'll get back to you" in sent emails)

### 2.3 Enhanced File Management

- [ ] Duplicate file detection
- [ ] Large file finder
- [ ] Folder size analysis / disk usage visualization
- [ ] macOS tags integration (color tags, smart search)
- [ ] Recent files / frequently accessed files dashboard widget

### 2.4 Image Generation Improvements

- [ ] Image editing (crop, resize, filters) in-app
- [ ] Style presets for DALL·E (photorealistic, illustration, watercolor)
- [ ] Image history gallery with regenerate option
- [ ] Batch generation
- [ ] Use generated images in presentations

---

## Phase 3 — Ecosystem & Distribution (v1.5)

**Goal:** Make SortMeOut distributable and sustainable.

### 3.1 App Store Readiness

- [ ] Code signing with Apple Developer certificate
- [ ] Notarization workflow
- [ ] App Sandbox compliance evaluation
- [ ] Privacy manifest (explain all data access)
- [ ] App Store screenshots and preview video
- [ ] macOS 13+ version check and compatibility testing

### 3.2 Licensing & Payment

- [ ] Stripe integration for Pro subscriptions
- [ ] License key validation (online + offline grace period)
- [ ] Feature gating (free tier vs. Pro)
- [ ] Trial period (14 days full access)
- [ ] Renewal/cancellation flow

### 3.3 Auto-Update

- [ ] Sparkle framework integration for in-app updates
- [ ] Release notes display on update
- [ ] Background update check

### 3.4 Analytics & Telemetry (opt-in)

- [ ] Anonymous usage metrics (which features are used most)
- [ ] Crash reporting
- [ ] Performance monitoring
- [ ] Feature request collection in-app

---

## Phase 4 — Advanced Features (v2.0)

**Goal:** Differentiate with unique, powerful features.

### 4.1 Workflows

- [ ] Multi-step workflow builder (visual canvas)
- [ ] If/else branching in workflows
- [ ] Webhook triggers (incoming HTTP events)
- [ ] Shortcuts.app integration (run SortMeOut actions from Shortcuts)
- [ ] AppleScript dictionary (let other apps control SortMeOut)

### 4.2 Knowledge Base

- [ ] Index local files for semantic search (RAG)
- [ ] "Chat with your documents" (PDF, Word, spreadsheet Q&A)
- [ ] Automatic filing suggestions based on content analysis
- [ ] Cross-reference notes, emails, and calendar events

### 4.3 Collaboration

- [ ] Shared rule libraries (export/import rule packs)
- [ ] Team presets for enterprise (centralized rule deployment)
- [ ] iCloud sync for rules and settings

### 4.4 Additional Integrations

- [ ] Reminders.app integration
- [ ] Safari/browser bookmarks
- [ ] Finder Quick Actions plugin
- [ ] Menu bar mini-mode (quick access without full app)
- [ ] Spotlight extension (search SortMeOut from Spotlight)

---

## Development Process

### Branching Strategy

```
main ──────────────────────────────────── production
  └── develop ─────────────────────────── integration
        ├── feature/onboarding ────────── feature branch
        ├── feature/chat-history ──────── feature branch
        └── fix/messages-permissions ──── bugfix branch
```

### Release Process

1. Feature branches merge → `develop`
2. When `develop` is stable → merge to `main`
3. Tag release: `git tag v1.0.0`
4. Build: `pyinstaller SortMeOutDesktop.spec`
5. Sign & notarize: `codesign + xcrun notarytool`
6. Create DMG: `create-dmg`
7. Upload to website / distribute

### Testing Strategy

- **Unit tests**: `tests/` directory (pytest)
- **Integration tests**: `tests/test_bridge.py` (85 tests)
- **Manual testing**: Checklist in `DEPLOYMENT_CHECKLIST.md`
- **Goal**: 80%+ code coverage before v1.0

### Quality Checklist (per feature)

- [ ] Feature works without API keys (graceful degradation)
- [ ] Error states have friendly messages
- [ ] Loading states shown during async operations
- [ ] Accessibility: keyboard navigation, screen reader labels
- [ ] Dark mode tested
- [ ] Performance: no blocking UI on long operations

---

## Priority Matrix

| Priority | Feature | Impact | Effort |
|----------|---------|--------|--------|
| 🔴 P0 | Onboarding wizard | High | Medium |
| 🔴 P0 | Error handling polish | High | Low |
| 🔴 P0 | Chat history persistence | High | Medium |
| 🟡 P1 | Per-feature settings | Medium | Medium |
| 🟡 P1 | Proactive daily briefing | High | High |
| 🟡 P1 | Streaming chat responses | Medium | Medium |
| 🟢 P2 | Visual rule builder | Medium | High |
| 🟢 P2 | Document Q&A (RAG) | High | High |
| 🟢 P2 | App Store submission | High | High |
| 🔵 P3 | Workflow canvas | Medium | Very High |
| 🔵 P3 | iCloud sync | Medium | High |

---

## Timeline (Estimated)

| Phase | Target | Duration |
|-------|--------|----------|
| Phase 1 — Polish | v1.0 | 4–6 weeks |
| Phase 2 — Intelligence | v1.1 | 6–8 weeks |
| Phase 3 — Distribution | v1.5 | 4–6 weeks |
| Phase 4 — Advanced | v2.0 | 8–12 weeks |

---

*Last updated: June 2025*
