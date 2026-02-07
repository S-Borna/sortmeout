# Security Setup — Universell mall för webbprojekt

> Kopiera denna fil till varje nytt projekt och anpassa domännamn.
> Principen: servern skyddar — frontend är publik.

---

## 1. HTML Security Headers (alla sidor)

Lägg i `<head>` på varje HTML-sida. Anpassa domäner efter projekt.

```html
<!-- CSP — Anpassa script-src, connect-src, frame-src per projekt -->
<meta http-equiv="Content-Security-Policy"
    content="
        default-src 'self';
        script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://js.stripe.com;
        style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
        font-src 'self' https://fonts.gstatic.com;
        img-src 'self' data: https:;
        connect-src 'self' https://api.DINDOMÄN.com https://api.stripe.com;
        frame-src https://js.stripe.com;
        frame-ancestors 'none';
        base-uri 'self';
        form-action 'self' https://checkout.stripe.com;
    ">
<meta http-equiv="X-Content-Type-Options" content="nosniff">
<meta http-equiv="X-Frame-Options" content="DENY">
<meta http-equiv="Referrer-Policy" content="strict-origin-when-cross-origin">
<meta http-equiv="Permissions-Policy" content="geolocation=(), microphone=(), camera=()">
```

### Vanliga domäner att vitlista i CSP

| Tjänst | script-src | connect-src | frame-src |
|---|---|---|---|
| Stripe | `https://js.stripe.com` | `https://api.stripe.com` | `https://js.stripe.com` |
| Google Fonts | `https://fonts.googleapis.com` | — | — |
| Google Analytics | `https://www.googletagmanager.com` | `https://www.google-analytics.com` | — |
| Cloudflare Turnstile | `https://challenges.cloudflare.com` | — | `https://challenges.cloudflare.com` |
| Sentry | — | `https://o*.ingest.sentry.io` | — |

---

## 2. Nginx Security Headers

Om du kör nginx (inte Cloudflare Pages/Vercel), lägg detta i server-blocket:

```nginx
# Security Headers
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://js.stripe.com; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.DINDOMÄN.com; frame-ancestors 'none';" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

server_tokens off;
```

---

## 3. Backend-säkerhet (det som faktiskt skyddar)

### 3.1 Miljövariabler

Alla hemligheter i `.env`, aldrig i kod:

```bash
# .env — ALDRIG committa denna
STRIPE_SECRET_KEY=sk_live_...
DATABASE_URL=postgresql://...
JWT_SECRET=...
API_KEY=...
```

```bash
# .gitignore — MÅSTE inkludera
.env
.env.local
.env.production
*.pem
*.key
```

### 3.2 CORS (API)

Bara din egen domän får anropa APIt:

```python
# FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://DINDOMÄN.com"],  # INTE "*"
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
```

```javascript
// Express
const cors = require('cors');
app.use(cors({
    origin: 'https://DINDOMÄN.com',  // INTE '*'
    methods: ['GET', 'POST'],
}));
```

### 3.3 Rate Limiting (API)

```python
# FastAPI med slowapi
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/login")
@limiter.limit("5/minute")
async def login(request: Request): ...

@app.post("/api/checkout")
@limiter.limit("10/minute")
async def checkout(request: Request): ...
```

```javascript
// Express med express-rate-limit
const rateLimit = require('express-rate-limit');
app.use('/api/login', rateLimit({ windowMs: 60000, max: 5 }));
app.use('/api/checkout', rateLimit({ windowMs: 60000, max: 10 }));
```

### 3.4 Input-validering

Validera ALLT på servern. Frontend-validering är UX, inte säkerhet.

```python
# Pydantic (FastAPI)
class CheckoutRequest(BaseModel):
    email: EmailStr
    plan: Literal["monthly", "yearly"]
```

---

## 4. Cloudflare-inställningar

### Obligatoriskt (alla projekt)

1. **SSL/TLS** → Full (strict)
2. **Always Use HTTPS** → On
3. **HSTS** → Enable (max-age 12 months, includeSubDomains)
4. **Bot Fight Mode** → On
5. **Security Level** → Medium

### Rekommenderat

1. **WAF Managed Rules** → On (free tier inkluderar OWASP-regler)
2. **Rate Limiting** → Skapa regel: 100 requests/minut per IP
3. **Browser Integrity Check** → On

---

## 5. Checklista per projekt

Kopiera och bocka av:

```
[ ] .env med alla hemligheter, INTE i git
[ ] .gitignore inkluderar .env, .env.*, *.pem, *.key
[ ] CSP meta-tag i alla HTML-sidor
[ ] X-Frame-Options: DENY
[ ] X-Content-Type-Options: nosniff
[ ] CORS begränsat till egen domän (inte *)
[ ] Rate limiting på auth/checkout endpoints
[ ] Input-validering server-side
[ ] HTTPS only (redirect HTTP → HTTPS)
[ ] Cloudflare Bot Fight Mode on
[ ] Inga API-nycklar i frontend-kod
[ ] Lösenord hashade med bcrypt/argon2 (om auth)
```

---

## 6. Vad du INTE behöver

Följande ger ingen reell säkerhet och riskerar att bryta funktionalitet:

- Client-side DevTools-blockering (kringgås via meny)
- Högerklick-blockering (irriterar användare)
- Console.log-blockering (döljer fel)
- Text selection-blockering (förhindrar copy/paste)
- Object.freeze på prototyper (bryter tredjeparts-JS)
- Debugger-traps (prestandaproblem)
- View-source-blockering (curl fungerar ändå)
- Invisible watermarks (ingen effekt)

---

*Frontend är marknadsföring. Backend är produkten. Skydda rätt sak.*
