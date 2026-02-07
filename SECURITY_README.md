# SortMeOut Security Shield v2.0

## Översikt

SortMeOut-webbplatsen är skyddad med **balanserade** säkerhetsåtgärder som skyddar mot botar och scraping utan att bryta funktionalitet för riktiga användare.

> **v2.0 Uppgradering**: Tidigare version (v1.0) hade extrema skydd som bröt Stripe checkout, blockerade riktiga användare, och orsakade prestandaproblem. Denna version behåller verklig säkerhet och tar bort allt som skadar UX.

---

## Aktiva Säkerhetsfunktioner

### 1. Tangentbordsskydd

- Blockerar DevTools-genvägar: F12, Ctrl/Cmd+Shift+I/J/C, Ctrl/Cmd+U

### 2. Bot & Automation-detektion

- PhantomJS, Selenium, Headless Chrome, Navigator.webdriver
- Blockerar automatiserade webbläsare

### 3. DOM-skydd (Script Injection Prevention)

- MutationObserver övervakar nya `<script>`-element
- Tillåter bara scripts från betrodda domäner (sortmeout, stripe.com, googleapis, etc.)
- Blockerar injicerade malware-scripts

### 4. View-source Redirect

- `view-source:` protokoll redirectas tillbaka till sidan

### 5. Security Headers (HTTP & Meta)

- Content-Security-Policy med Stripe/API-domäner vitlistade
- X-Frame-Options: DENY (anti-clickjacking)
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- HSTS (nginx)

### 6. Copyright Meta Tags

- Automatiska copyright-taggar

---

## Borttagna Skydd (v1.0 till v2.0)

Dessa skydd bröt funktionalitet och har tagits bort:

| Borttaget skydd | Varför det var problematiskt |
|---|---|
| `Object.freeze(Object.prototype)` | Bröt Stripe.js, alla tredjeparts-libraries |
| DevTools fönsterstorlek-detektion | False positives vid responsive design |
| Debugger-trap varje 100ms | Massiv prestandaförsämring, rekursiv loop |
| Performance monitor (>200ms = radera sida) | GC-pauser, nätverkslatens = blank sida |
| Console helt avstängd + fryst | Omöjliggjorde debugging, tystade errors |
| Högerklick blockerat | Ingen "Öppna i ny flik" |
| Textmarkering blockerad | Kunde inte kopiera installationskommandon |
| Copy begränsad till 50 tecken | Licensnycklar kunde inte kopieras |
| Cut helt blockerad | Bruten inmatning |
| Screen recording "detection" | Ingen effekt, bara prestandakostnad |
| Invisible watermark | Ingen reell nytta |
| `navigator.plugins.length === 0` check | Blockerade riktiga Chrome-användare |
| DOM-observer: alla scripts utan "sortmeout" borttagna | Tog bort Stripe.js och Google Analytics |
| `user-select: none` på allt | Kunde inte markera text |

---

## Filer

- **`website/js/security.js`** — Säkerhetsskript v2.0 (~130 rader)
- **`website/nginx.conf.example`** — CSP med Stripe-stöd
- **Alla HTML-filer** — CSP meta-tags, security headers

---

## Cloudflare-integration

Cloudflare ger det starkaste skyddet — utan att bryta JavaScript:

1. **SSL/TLS**: Full (strict) mode med HSTS
2. **WAF**: Blockerar kända botar
3. **Rate Limiting**: Begränsar requests per IP
4. **Bot Fight Mode**: Automatisk bot-detektion
5. **DDoS Protection**: Enterprise-nivå via Cloudflare

Se **CLOUDFLARE_SETUP.md** för konfigurationsguide.

---

## Konfiguration

### security.js CONFIG

```javascript
const CONFIG = {
    enableKeyboardProtection: true,
    enableBasicBotProtection: true,
    enableDomProtection: true,
};
```

### Betrodda script-domäner

```javascript
const ALLOWED_SCRIPT_DOMAINS = [
    'sortmeout', 'stripe.com', 'googleapis.com',
    'gstatic.com', 'google-analytics.com', 'googletagmanager.com',
];
```

---

## Säkerhetsnivå: BALANSERAD

| Skyddad mot | Status | Ansvar |
|---|---|---|
| Automated bots | Ja | JS + Cloudflare |
| Script injection | Ja | MutationObserver |
| XSS attacks | Ja | CSP Headers |
| Clickjacking | Ja | X-Frame-Options |
| MITM attacks | Ja | HSTS + SSL |
| DDoS | Ja | Cloudflare |
| DevTools genvägar | Ja | Keyboard listener |
| Stripe checkout | Ja | CSP vitlistar Stripe |
| Textkopering | Ja | Tillåten (normal UX) |

---

© 2026 SortMeOut - All Rights Reserved
