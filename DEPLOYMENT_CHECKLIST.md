# 🚀 SortMeOut Security Deployment Checklist

## Pre-Deployment

### 1. Local Testing

- [ ] Testa security.js lokalt
- [ ] Verifiera att DevTools blockeras
- [ ] Testa alla HTML-sidor (index, privacy, terms, docs)
- [ ] Kontrollera att legitima funktioner fungerar
- [ ] Testa på olika browsers (Chrome, Firefox, Safari, Edge)
- [ ] Testa på mobil (iOS, Android)

### 2. Code Review

- [ ] Granska security.js för fel
- [ ] Kontrollera att alla HTML-filer har security headers
- [ ] Verifiera att security.js laddas före main.js
- [ ] Dubbelkolla CSP-policy

### 3. Backup

- [ ] Ta backup av nuvarande website
- [ ] Dokumentera aktuell Cloudflare-konfiguration
- [ ] Spara kopia av .htaccess/nginx.conf

---

## Deployment Steps

### Phase 1: Upload Files

- [ ] Ladda upp `js/security.js`
- [ ] Uppdatera `index.html`
- [ ] Uppdatera `privacy.html`
- [ ] Uppdatera `terms.html`
- [ ] Uppdatera `docs/index.html`
- [ ] Ladda upp `.htaccess` (Apache) ELLER
- [ ] Uppdatera nginx.conf (Nginx)

### Phase 2: Server Configuration

#### För Apache

- [ ] Verifiera att mod_headers är aktiverat: `apache2ctl -M | grep headers`
- [ ] Verifiera att mod_rewrite är aktiverat: `apache2ctl -M | grep rewrite`
- [ ] Testa .htaccess syntax: `apachectl configtest`
- [ ] Restart Apache: `sudo systemctl restart apache2`

#### För Nginx

- [ ] Uppdatera server block-konfiguration
- [ ] Testa Nginx syntax: `nginx -t`
- [ ] Reload Nginx: `sudo systemctl reload nginx`

### Phase 3: Cloudflare Configuration

#### 3.1 SSL/TLS (5 min)

- [ ] Gå till SSL/TLS
- [ ] Sätt till "Full (strict)"
- [ ] Aktivera "Always Use HTTPS"
- [ ] Aktivera "Automatic HTTPS Rewrites"
- [ ] Aktivera TLS 1.3
- [ ] Konfigurera HSTS (12 months, includeSubDomains, preload)

#### 3.2 Firewall Rules (15 min)

- [ ] Blockera kända bottar (curl, wget, python, scrapy, selenium, etc.)
- [ ] Skapa rate limiting för /download (5 requests per 10 min)
- [ ] Skapa geografisk begränsning (om önskat)
- [ ] Blockera känsliga endpoints (/admin, /api, /config)

#### 3.3 Security Headers via Transform Rules (10 min)

- [ ] Content-Security-Policy
- [ ] X-Frame-Options: DENY
- [ ] X-Content-Type-Options: nosniff
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Referrer-Policy: strict-origin-when-cross-origin
- [ ] Permissions-Policy
- [ ] Strict-Transport-Security
- [ ] X-Robots-Tag

#### 3.4 Page Rules (5 min)

- [ ] Cache Everything för /css/*
- [ ] Cache Everything för /js/*
- [ ] Cache Everything för /images/*
- [ ] Security Level: High för /download*

#### 3.5 Bot Management (2 min)

- [ ] Aktivera "Bot Fight Mode" (Free plan)
- [ ] ELLER "Super Bot Fight Mode" (Betald plan)
- [ ] Konfigurera: Definitely automated = Block
- [ ] Konfigurera: Verified bots = Allow
- [ ] Konfigurera: Static resource protection = ON

#### 3.6 DDoS Protection (1 min)

- [ ] Verifiera HTTP DDoS Attack Protection: ON
- [ ] Verifiera Network-layer DDoS: ON

#### 3.7 Rate Limiting Rules (5 min)

- [ ] General Rate Limit: 100 requests per 10 seconds
- [ ] Download Protection: 5 requests per 60 seconds

#### 3.8 WAF Managed Rules (3 min)

- [ ] Aktivera "Cloudflare Managed Ruleset"
- [ ] Aktivera "Cloudflare OWASP Core Ruleset" (PL1)
- [ ] Aktivera "Cloudflare Exposed Credentials Check"

#### 3.9 Cache Settings (2 min)

- [ ] Caching Level: Standard
- [ ] Browser Cache TTL: 4 hours
- [ ] Always Online: ON
- [ ] Development Mode: OFF

#### 3.10 Performance (3 min)

- [ ] Auto Minify: JavaScript, CSS, HTML
- [ ] Brotli: ON
- [ ] Early Hints: ON
- [ ] HTTP/2: ON
- [ ] HTTP/3 (QUIC): ON
- [ ] 0-RTT: ON

#### 3.11 Custom Error Pages (5 min)

- [ ] Skapa custom 403 page
- [ ] Skapa custom 429 page (Rate Limited)
- [ ] Skapa custom 1020 page (WAF Block)
- [ ] Skapa custom 500 page

#### 3.12 Notifications (5 min)

- [ ] HTTP DDoS Attack Alert → Email
- [ ] SSL Certificate Expiration → Email
- [ ] Security Events Alert → Email

---

## Post-Deployment Testing

### Immediate Tests (within 5 minutes)

#### 1. Basic Functionality

- [ ] Ladda webbplatsen: <https://sortmeout.saidborna.com>
- [ ] Verifiera att sidan laddar korrekt
- [ ] Testa navigation
- [ ] Testa alla länkar
- [ ] Verifiera bilder laddar

#### 2. Security Tests

- [ ] Tryck F12 → Verifiera DevTools blockeras
- [ ] Högerklicka → Verifiera context menu blockeras
- [ ] Ctrl+U → Verifiera view source blockeras
- [ ] Ctrl+S → Verifiera save page blockeras
- [ ] Försök kopiera stor text → Verifiera copyright-meddelande
- [ ] Öppna console → Verifiera att console.log() inte fungerar

#### 3. Mobile Testing

- [ ] Öppna på iPhone/Android
- [ ] Testa long-press → Verifiera blockering
- [ ] Testa pinch-to-zoom
- [ ] Verifiera touch-funktionalitet

### SSL/TLS Tests (5 minutes)

#### 1. SSL Labs Test

```
https://www.ssllabs.com/ssltest/analyze.html?d=sortmeout.saidborna.com
```

- [ ] Mål: **A+ rating**
- [ ] Verifiera TLS 1.3 support
- [ ] Verifiera HSTS active
- [ ] Verifiera certificate valid

#### 2. Security Headers Test

```
https://securityheaders.com/?q=sortmeout.saidborna.com
```

- [ ] Mål: **A+ rating**
- [ ] Verifiera alla headers närvarande
- [ ] Verifiera CSP konfigurerad
- [ ] Verifiera HSTS active

#### 3. CSP Validator

```
https://csp-evaluator.withgoogle.com/
```

- [ ] Klistra in din CSP
- [ ] Verifiera inga kritiska varningar
- [ ] Justera om nödvändigt

#### 4. Mozilla Observatory

```
https://observatory.mozilla.org/analyze/sortmeout.saidborna.com
```

- [ ] Mål: **A+ rating**
- [ ] Granska recommendations
- [ ] Implementera förbättringar

### Bot & Scraper Tests (10 minutes)

#### 1. cURL Test (ska blockeras)

```bash
curl https://sortmeout.saidborna.com/
# Förväntat: 403 Forbidden eller Cloudflare challenge
```

#### 2. wget Test (ska blockeras)

```bash
wget https://sortmeout.saidborna.com/
# Förväntat: 403 Forbidden eller Cloudflare challenge
```

#### 3. Python Requests Test (ska blockeras)

```python
import requests
r = requests.get('https://sortmeout.saidborna.com/')
print(r.status_code)
# Förväntat: 403 eller 503 (Cloudflare challenge)
```

#### 4. Custom User Agent Test (ska blockeras)

```bash
curl -A "BadBot/1.0" https://sortmeout.saidborna.com/
# Förväntat: 403 Forbidden
```

#### 5. Selenium Test (ska blockeras)

```python
from selenium import webdriver
driver = webdriver.Chrome()
driver.get('https://sortmeout.saidborna.com/')
# Förväntat: Cloudflare challenge eller blockering
```

### Rate Limiting Tests (5 minutes)

#### 1. General Rate Limit Test

```bash
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://sortmeout.saidborna.com/
  sleep 0.05
done
# Förväntat: Några 200, sen 429 (Too Many Requests)
```

#### 2. Download Rate Limit Test

```bash
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://sortmeout.saidborna.com/download
done
# Förväntat: Max 5 x 200, sen 429
```

### Browser Compatibility (10 minutes)

Test på olika browsers:

#### Chrome/Edge

- [ ] Ladda sidan
- [ ] Testa F12
- [ ] Testa högerklick
- [ ] Testa Ctrl+Shift+I
- [ ] Verifiera security shield aktivt

#### Firefox

- [ ] Ladda sidan
- [ ] Testa F12
- [ ] Testa högerklick
- [ ] Verifiera security shield aktivt

#### Safari (macOS/iOS)

- [ ] Ladda sidan
- [ ] Testa Cmd+Option+I
- [ ] Testa högerklick
- [ ] Verifiera security shield aktivt

#### Mobile Browsers

- [ ] Chrome Mobile
- [ ] Safari Mobile
- [ ] Samsung Internet
- [ ] Firefox Mobile

### Performance Tests (5 minutes)

#### 1. Google PageSpeed Insights

```
https://pagespeed.web.dev/analysis?url=https://sortmeout.saidborna.com/
```

- [ ] Desktop Score: > 90
- [ ] Mobile Score: > 80
- [ ] Granska recommendations

#### 2. GTmetrix

```
https://gtmetrix.com/
```

- [ ] Performance Score: > A
- [ ] Structure Score: > A
- [ ] Granska waterfall

#### 3. WebPageTest

```
https://www.webpagetest.org/
```

- [ ] First Contentful Paint: < 1.5s
- [ ] Time to Interactive: < 3s
- [ ] Speed Index: < 2s

---

## Monitoring Setup (30 minutes)

### 1. Cloudflare Analytics

- [ ] Sätt upp Cloudflare dashboard bookmarks
- [ ] Bekanta dig med Security Events
- [ ] Bekanta dig med Bot Traffic
- [ ] Bekanta dig med Rate Limiting analytics

### 2. Uptime Monitoring

Rekommenderade services (välj en):

#### Option A: UptimeRobot (gratis)

```
https://uptimerobot.com/
```

- [ ] Skapa konto
- [ ] Lägg till monitor för <https://sortmeout.saidborna.com/>
- [ ] Konfigurera email-notiser
- [ ] Intervall: 5 minuter

#### Option B: Pingdom

```
https://www.pingdom.com/
```

- [ ] Skapa konto
- [ ] Lägg till monitor
- [ ] Konfigurera alerts

#### Option C: StatusCake

```
https://www.statuscake.com/
```

- [ ] Skapa konto
- [ ] Lägg till uptime monitor
- [ ] Lägg till SSL monitor

### 3. Log Monitoring

#### För Apache

```bash
# Real-time security log monitoring
sudo tail -f /var/log/apache2/access.log | grep -E '(403|429|503)'

# Count blocked requests
grep ' 403 ' /var/log/apache2/access.log | wc -l
```

#### För Nginx

```bash
# Real-time security log monitoring
sudo tail -f /var/log/nginx/sortmeout_access.log | grep -E '(403|429|503)'

# Count blocked requests
grep ' 403 ' /var/log/nginx/sortmeout_access.log | wc -l
```

### 4. Error Tracking (optional)

#### Sentry (rekommenderat)

```
https://sentry.io/
```

- [ ] Skapa konto
- [ ] Lägg till JavaScript SDK
- [ ] Konfigurera för sortmeout.saidborna.com
- [ ] Testa error reporting

---

## Week 1 Monitoring

### Daily Checks (första veckan)

#### Dag 1 (Deploy-dag)

- [ ] Morgon: Kontrollera att sidan är uppe
- [ ] Middag: Granska Cloudflare Analytics
- [ ] Kväll: Kontrollera för error reports
- [ ] Kväll: Kontrollera logs för false positives

#### Dag 2-7

- [ ] Daglig Cloudflare Analytics-granskning
- [ ] Granska blocked requests
- [ ] Leta efter patterns
- [ ] Justera rules om false positives

### Weekly Report (Vecka 1)

Sammanställ statistics:

- [ ] Total requests
- [ ] Blocked requests (%)
- [ ] Bot traffic detected
- [ ] Rate limit triggers
- [ ] Top blocked IPs
- [ ] Top blocked User Agents
- [ ] False positives (om några)
- [ ] Performance impact

---

## Rollback Plan

Om något går fel:

### Snabb Rollback (< 5 minuter)

#### 1. Återställ HTML-filer

```bash
# Om du har backup
cp backup/index.html website/index.html
cp backup/privacy.html website/privacy.html
cp backup/terms.html website/terms.html
cp backup/docs/index.html website/docs/index.html
```

#### 2. Inaktivera security.js

```bash
# Byt namn på filen
mv website/js/security.js website/js/security.js.disabled
```

#### 3. Cloudflare: I'm Under Attack Mode OFF

- [ ] Gå till Cloudflare Dashboard
- [ ] Security → Settings
- [ ] Security Level: Medium
- [ ] Bot Fight Mode: OFF (tillfälligt)

#### 4. Cloudflare: Disable Rules

- [ ] Inaktivera nyligen skapade Firewall Rules
- [ ] Inaktivera Rate Limiting Rules
- [ ] Inaktivera Transform Rules (headers)

### Full Rollback (15 minuter)

1. **Återställ alla filer från backup**
2. **Ta bort/återställ .htaccess eller nginx.conf**
3. **Inaktivera alla Cloudflare-regler**
4. **Verifiera att webbplatsen fungerar normalt**
5. **Analysera vad som gick fel**
6. **Planera ny deployment**

---

## Troubleshooting Common Issues

### Issue 1: Legitima användare blockeras

**Symtom:** Användare rapporterar 403-fel

**Lösning:**

1. Kontrollera Cloudflare Firewall Events
2. Identifiera IP eller User Agent
3. Skapa exception rule i Cloudflare
4. Justera Bot Fight Mode sensitivity

### Issue 2: Security.js orsakar JavaScript-fel

**Symtom:** Andra scripts fungerar inte

**Lösning:**

1. Öppna browser console (om möjligt)
2. Identifiera error
3. Justera security.js CONFIG
4. Testa lokalt innan re-deploy

### Issue 3: Sidan laddar långsamt

**Symtom:** Long page load times

**Lösning:**

1. Kontrollera Cloudflare cache hit rate
2. Verifiera att static assets cachas
3. Justera Cache Rules
4. Optimera security.js (minifiera)

### Issue 4: DevTools kan fortfarande öppnas

**Symtom:** F12 fungerar fortfarande

**Lösning:**

1. Verifiera att security.js laddar
2. Kontrollera browser console för errors
3. Testa i incognito mode
4. Rensa browser cache

### Issue 5: CSP blockerar legitim content

**Symtom:** Images/fonts laddar inte

**Lösning:**

1. Kontrollera browser console för CSP violations
2. Justera CSP-policy
3. Lägg till nödvändiga domains
4. Testa i flera browsers

---

## Success Metrics

Efter 1 vecka, utvärdera:

### Security Metrics

- [ ] **0 successful scraping attempts**
- [ ] **> 90% bot detection rate**
- [ ] **< 5% false positive rate**
- [ ] **A+ rating på SSL Labs**
- [ ] **A+ rating på Security Headers**

### Performance Metrics

- [ ] **Page load time: < 2 seconds**
- [ ] **Cloudflare cache hit rate: > 80%**
- [ ] **No increase in bounce rate**
- [ ] **No decrease in legitimate traffic**

### Reliability Metrics

- [ ] **99.9%+ uptime**
- [ ] **No security incidents**
- [ ] **No data breaches**
- [ ] **No successful attacks**

---

## Maintenance Schedule

### Daily (första månaden)

- [ ] Kontrollera Cloudflare Analytics
- [ ] Granska blocked requests

### Weekly

- [ ] Uppdatera blocklist om nödvändigt
- [ ] Granska false positives
- [ ] Justera rules

### Monthly

- [ ] Full security audit
- [ ] Uppdatera security.js om nya hot
- [ ] Review Cloudflare configuration
- [ ] Testa alla security features

### Quarterly

- [ ] Penetration testing (om budget finns)
- [ ] Third-party security audit
- [ ] Update all security documentation

---

## Sign-off Checklist

Before marking deployment complete:

- [ ] All deployment steps completed
- [ ] All tests passed
- [ ] SSL: A+ rating
- [ ] Security Headers: A+ rating
- [ ] No false positives detected
- [ ] Performance not degraded
- [ ] Monitoring active
- [ ] Team notified
- [ ] Documentation updated
- [ ] Rollback plan ready
- [ ] Support prepared for potential issues

---

## Contact Information

**Security Incident Response:**

- Email: <security@sortmeout.saidborna.com>
- Escalation: [Your phone number]

**Technical Support:**

- Email: <said@saidborna.com>

**Cloudflare Support:**

- Dashboard: <https://dash.cloudflare.com/>
- Support: <https://support.cloudflare.com/>

---

## Stripe & Payment System Deployment

### Steg 1: Cloudflare Worker Setup

#### 1.1 Installera Wrangler

- [ ] `npm install -g wrangler`
- [ ] `wrangler login`

#### 1.2 Skapa KV Namespace

```bash
cd worker/
wrangler kv namespace create "LICENSES"
```

- [ ] Kopiera KV namespace ID
- [ ] Uppdatera `worker/wrangler.toml` med ID:t:

  ```toml
  [[kv_namespaces]]
  binding = "LICENSES"
  id = "DITT-FAKTISKA-ID"
  ```

#### 1.3 Sätt Secrets

```bash
# Stripe Secret Key (testläge först)
wrangler secret put STRIPE_SECRET_KEY
# → sk_test_...

# Generera och spara license signing key
openssl rand -hex 32
wrangler secret put LICENSE_SIGNING_KEY
# → klistra in hex-strängen

# Webhook secret (skapas i steg 2.2)
wrangler secret put STRIPE_WEBHOOK_SECRET
# → whsec_...
```

- [ ] STRIPE_SECRET_KEY satt
- [ ] LICENSE_SIGNING_KEY satt
- [ ] STRIPE_WEBHOOK_SECRET satt (efter steg 2.2)

#### 1.4 Deploya Worker

```bash
cd worker/
npm install
wrangler deploy
```

- [ ] Worker deployed
- [ ] Konfigurera custom domain: `api.sortmeout.saidborna.com`

#### 1.5 Verifiera health endpoint

```bash
curl https://api.sortmeout.saidborna.com/api/health
# Förväntat: {"status":"ok","version":"1.0.1"}
```

- [ ] Health endpoint svarar korrekt

### Steg 2: Stripe Dashboard konfiguration

#### 2.1 Skapa produkt och pris

- [ ] Gå till Stripe Dashboard → Products → Add product
- [ ] Namn: "SortMeOut Pro"
- [ ] Pris: $9.99/månad (recurring)
- [ ] Kopiera Price ID (börjar med `price_`)
- [ ] Verifiera att `wrangler.toml` har rätt `STRIPE_PRICE_ID`

#### 2.2 Konfigurera Webhook

- [ ] Gå till Stripe Dashboard → Developers → Webhooks
- [ ] Klicka "Add endpoint"
- [ ] URL: `https://api.sortmeout.saidborna.com/api/webhook`
- [ ] Välj events:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_failed`
- [ ] Kopiera Signing secret (`whsec_...`)
- [ ] Spara som Worker secret: `wrangler secret put STRIPE_WEBHOOK_SECRET`

### Steg 3: Testa betalningsflödet (testläge)

#### 3.1 End-to-end test

- [ ] Öppna `https://sortmeout.saidborna.com/#pricing`
- [ ] Klicka "Get Pro" → Stripe Checkout öppnas
- [ ] Använd testkort: `4242 4242 4242 4242`, MM/ÅÅ: `12/34`, CVC: `123`
- [ ] Omdirigeras till success-sidan
- [ ] Licensnyckel visas (format: SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM)
- [ ] "Copy" knappen fungerar

#### 3.2 Testa licensaktivering

```bash
sortmeout license activate DIN-TESTNYCKEL
# Förväntat: ✓ Pro License Activated!
```

- [ ] CLI aktivering fungerar
- [ ] GUI aktivering fungerar (menyrad → Enter Pro License)

#### 3.3 Testa nyckelverifiering

```bash
curl -X POST https://api.sortmeout.saidborna.com/api/verify \
  -H "Content-Type: application/json" \
  -d '{"license_key": "DIN-TESTNYCKEL"}'
# Förväntat: {"valid":true,"status":"active","email":"..."}
```

- [ ] API-verifiering fungerar

#### 3.4 Testa felfall

- [ ] Avvisat kort (`4000 0000 0000 0002`) → felmeddelande visas
- [ ] 3D Secure (`4000 0025 0000 3155`) → 3DS-flöde → lyckas
- [ ] Ogiltig nyckel → "Invalid license key"

### Steg 4: Gå live med Stripe

- [ ] Byt till Stripe live-nycklar:

  ```bash
  wrangler secret put STRIPE_SECRET_KEY
  # → sk_live_...
  ```

- [ ] Skapa ny webhook i Stripe live mode (samma URL och events)
- [ ] Uppdatera webhook secret:

  ```bash
  wrangler secret put STRIPE_WEBHOOK_SECRET
  # → nya whsec_...
  ```

- [ ] Uppdatera `STRIPE_PRICE_ID` i `wrangler.toml` om live-priset har annat ID
- [ ] Deploya: `wrangler deploy`
- [ ] Testa med riktigt kort (liten summa → refund direkt)

### Steg 5: Övervakning

- [ ] `wrangler tail` — se Worker-loggar i realtid
- [ ] Stripe Dashboard → Developers → Webhooks → kontrollera attempts
- [ ] Konfigurera Stripe email-notifikationer för misslyckade betalningar
- [ ] `wrangler kv key list --binding LICENSES` — verifiera KV-data

---

**Deployment Date:** _____________

**Deployed By:** _____________

**Verified By:** _____________

**Sign-off Date:** _____________

---

✅ **Lycka till med deployment! Din webbplats kommer att vara maximalt skyddad!** 🛡️🔒
