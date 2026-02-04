# SortMeOut Build Specification

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        git push                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│   Cloudflare Pages  │         │   GitHub Releases   │
│   (automatic)       │         │   (manual)          │
├─────────────────────┤         ├─────────────────────┤
│ Trigger: git push   │         │ Trigger: manual     │
│ Source: website/    │         │ Source: local build │
│ Output: static site │         │ Output: .dmg        │
└─────────────────────┘         └─────────────────────┘
          │                               │
          ▼                               ▼
   sortmeout.saidborna.com        SortMeOut.dmg download
```

---

## Website (Automatic)

**Platform:** Cloudflare Pages  
**URL:** https://sortmeout.saidborna.com  
**Source directory:** `website/`  
**Build command:** None (static HTML)  

### Deploy
```bash
git push
```
Cloudflare Pages bygger automatiskt vid push till `main`.

---

## macOS App (Manual)

**Tool:** PyInstaller  
**Output:** `dist/SortMeOut.app` → `dist/SortMeOut.dmg`  
**Spec file:** `sortmeout.spec`  

### Prerequisites
```bash
pip3 install pyinstaller pyobjc-core pyobjc-framework-Cocoa anthropic
```

### Build .app
```bash
pyinstaller sortmeout.spec --noconfirm
```

### Create .dmg
```bash
hdiutil create -volname "SortMeOut" -srcfolder dist/SortMeOut.app -ov -format UDZO dist/SortMeOut.dmg
```

### Upload to GitHub Release
```bash
gh release upload v1.0.0 dist/SortMeOut.dmg --clobber
```

---

## Development (Local)

Kör direkt från källkod utan att bygga:
```bash
python3 -m sortmeout.gui.main_window
```

---

## File Structure

```
sortmeout/
├── sortmeout/           # Python source code
│   ├── core/
│   │   └── license.py   # License authority (SINGLE SOURCE OF TRUTH)
│   ├── ai/
│   │   └── assistant.py # Claude AI integration
│   └── gui/
│       └── main_window.py
├── website/             # Static website → Cloudflare Pages
│   └── index.html
├── dist/                # Build output (gitignored)
│   ├── SortMeOut.app
│   └── SortMeOut.dmg
├── sortmeout.spec       # PyInstaller config
└── BUILD.md             # This file
```

---

## Version Bump Checklist

1. Update version in `pyproject.toml`
2. Update version in `website/index.html` (download section)
3. Build: `pyinstaller sortmeout.spec --noconfirm`
4. Create DMG: `hdiutil create ...`
5. Create GitHub release: `gh release create v1.x.x`
6. Upload DMG: `gh release upload v1.x.x dist/SortMeOut.dmg`
7. Push website: `git push`
