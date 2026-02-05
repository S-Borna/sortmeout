# SortMeOut - Cloudflare Säkerhetskonfiguration

## Översikt

Denna guide hjälper dig att konfigurera Cloudflare för maximal säkerhet för SortMeOut-webbplatsen.

---

## 1. Grundläggande SSL/TLS-inställningar

### Steg 1: SSL/TLS-konfiguration

1. Gå till **SSL/TLS** i Cloudflare Dashboard
2. Välj **Full (strict)** som krypteringsläge
3. Aktivera:
   - ✅ Always Use HTTPS
   - ✅ Automatic HTTPS Rewrites
   - ✅ Opportunistic Encryption
   - ✅ TLS 1.3

### Steg 2: Edge Certificates

1. Under **SSL/TLS** → **Edge Certificates**
2. Aktivera:
   - ✅ Always Use HTTPS
   - ✅ HTTP Strict Transport Security (HSTS)
   - Max Age Header: **12 months** (31536000)
   - ✅ Apply HSTS to subdomains
   - ✅ Preload

---

## 2. Firewall Rules (WAF)

### Regel 1: Blockera kända bottar och scrapers

```
Expression Builder:
(cf.client.bot) or
(http.user_agent contains "curl") or
(http.user_agent contains "wget") or
(http.user_agent contains "python") or
(http.user_agent contains "scrapy") or
(http.user_agent contains "selenium") or
(http.user_agent contains "PhantomJS") or
(http.user_agent contains "headless")

Action: Block
```

### Regel 2: Ratebegränsning

```
Expression Builder:
(http.request.uri.path contains "/download")

Action: Rate Limit
Requests: 5 requests per 10 minutes
```

### Regel 3: Geografisk begränsning (valfritt)

```
Expression Builder:
not (ip.geoip.country in {"SE" "NO" "DK" "FI" "DE" "US" "GB"})

Action: Challenge (Managed Challenge)
```

### Regel 4: Skydda känsliga endpoints

```
Expression Builder:
(http.request.uri.path contains "/admin") or
(http.request.uri.path contains "/api") or
(http.request.uri.path contains "/config")

Action: Block
```

---

## 3. Security Headers (Transform Rules)

Gå till **Rules** → **Transform Rules** → **Modify Response Header**

### Header 1: Strict Content Security Policy

```
Header Name: Content-Security-Policy
Value: default-src 'self'; script-src 'self' 'unsafe-inline' https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests;
Action: Set dynamic
```

### Header 2: X-Frame-Options

```
Header Name: X-Frame-Options
Value: DENY
Action: Set static
```

### Header 3: X-Content-Type-Options

```
Header Name: X-Content-Type-Options
Value: nosniff
Action: Set static
```

### Header 4: X-XSS-Protection

```
Header Name: X-XSS-Protection
Value: 1; mode=block
Action: Set static
```

### Header 5: Referrer-Policy

```
Header Name: Referrer-Policy
Value: strict-origin-when-cross-origin
Action: Set static
```

### Header 6: Permissions-Policy

```
Header Name: Permissions-Policy
Value: geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=()
Action: Set static
```

### Header 7: Strict-Transport-Security

```
Header Name: Strict-Transport-Security
Value: max-age=31536000; includeSubDomains; preload
Action: Set static
```

### Header 8: X-Robots-Tag

```
Header Name: X-Robots-Tag
Value: index, follow, max-snippet:-1, max-image-preview:large
Action: Set static
```

---

## 4. Page Rules

### Regel 1: Cache Everything (för statiska resurser)

```
URL Match: *sortmeout.saidborna.com/css/*
Settings:
- Cache Level: Cache Everything
- Edge Cache TTL: 1 month
- Browser Cache TTL: 1 week
```

```
URL Match: *sortmeout.saidborna.com/js/*
Settings:
- Cache Level: Cache Everything
- Edge Cache TTL: 1 month
- Browser Cache TTL: 1 week
```

```
URL Match: *sortmeout.saidborna.com/images/*
Settings:
- Cache Level: Cache Everything
- Edge Cache TTL: 1 month
- Browser Cache TTL: 1 week
```

### Regel 2: Säkerhet för nedladdningssidor

```
URL Match: *sortmeout.saidborna.com/download*
Settings:
- Security Level: High
- Browser Integrity Check: On
```

---

## 5. Scraping Protection (Bot Management)

### Under **Security** → **Bots**

1. **Bot Fight Mode**: ON (för gratis plan)
   - Eller använd **Super Bot Fight Mode** (betalplan)

2. **Configure Super Bot Fight Mode**:
   - ✅ Definitely automated: Block
   - ✅ Verified bots: Allow (Google, Bing, etc.)
   - ✅ Likely automated: Managed Challenge
   - ✅ Static resource protection: ON

---

## 6. DDoS Protection

### Under **Security** → **DDoS**

1. Aktivera:
   - ✅ HTTP DDoS Attack Protection: ON (Managed Ruleset)
   - ✅ Network-layer DDoS Attack Protection: ON

2. **Advanced DDoS Protection** (betalplan):
   - Sensitivity Level: High
   - Response: Block suspicious traffic

---

## 7. Rate Limiting (avancerat)

### Under **Security** → **Rate Limiting Rules**

#### Regel 1: Generell rate limiting

```
Rule Name: General Rate Limit
If incoming requests match:
  - All incoming requests

Then:
  - Counting expression: (http.request.uri.path)
  - Period: 10 seconds
  - Requests: 100
  - Action: Block for 60 seconds
  - Response: Custom HTML/JSON
```

#### Regel 2: API/Download protection

```
Rule Name: Download Protection
If incoming requests match:
  - URI Path contains "/download"

Then:
  - Period: 60 seconds
  - Requests: 5
  - Action: Block for 300 seconds (5 min)
```

---

## 8. Cache Settings

### Under **Caching** → **Configuration**

1. **Caching Level**: Standard
2. **Browser Cache TTL**: 4 hours
3. **Always Online**: ON
4. **Development Mode**: OFF (i produktion)

### Cache Rules

```
URL Match: *sortmeout.saidborna.com/*.html
Cache Level: Standard
Browser Cache TTL: 1 hour
```

---

## 9. Performance Settings

### Under **Speed** → **Optimization**

1. **Auto Minify**:
   - ✅ JavaScript
   - ✅ CSS
   - ✅ HTML

2. **Brotli**: ON

3. **Early Hints**: ON

4. **HTTP/2**: ON

5. **HTTP/3 (with QUIC)**: ON

6. **0-RTT Connection Resumption**: ON

---

## 10. Network Settings

### Under **Network**

1. **WebSockets**: ON
2. **Onion Routing**: OFF (säkerhetsskäl)
3. **IP Geolocation**: ON
4. **Maximum Upload Size**: 100 MB
5. **Pseudo IPv4**: Add header

---

## 11. WAF Managed Rules

### Under **Security** → **WAF** → **Managed rules**

Aktivera följande ruleset:

1. ✅ **Cloudflare Managed Ruleset**
2. ✅ **Cloudflare OWASP Core Ruleset**
   - Paranoia Level: PL1 eller PL2
3. ✅ **Cloudflare Exposed Credentials Check**

---

## 12. Security Analytics & Monitoring

### Rekommenderade alerts under **Notifications**

1. **HTTP DDoS Attack Alerter**
   - Trigger: When attack detected
   - Action: Email notification

2. **Advanced DDoS Attack Alerter**
   - Trigger: When large attack detected
   - Action: Email + Webhook

3. **SSL/TLS Certificate Expiration**
   - Trigger: 30 days before expiration
   - Action: Email notification

4. **Security Events Alert**
   - Trigger: High number of firewall events
   - Threshold: > 1000 events/hour
   - Action: Email notification

---

## 13. Access Control (valfritt)

### Under **Zero Trust** (om du har Cloudflare for Teams)

Skapa access policies för admin-områden:

```
Application: SortMeOut Admin
Policy Name: Admin Access Only
Allow if:
  - Email ends with: @yourdomain.com
  - IP Range: Your office IP
  - Country: Sweden

Session Duration: 24 hours
```

---

## 14. Custom Error Pages

### Under **Custom Pages**

Skapa anpassade felsidor för:

1. **500-serien fel**: Vackert felmeddelande
2. **1000 DNS errors**: Informativ sida
3. **Rate Limited (1015)**: "Du har gjort för många förfrågningar"
4. **WAF Block (1020)**: "Din begäran har blockerats av säkerhetsskäl"

Exempel HTML:

```html
<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Åtkomst nekad - SortMeOut</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: rgba(0,0,0,0.3);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 48px; margin: 0 0 20px 0; }
        p { font-size: 18px; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Åtkomst Nekad</h1>
        <p>Din begäran har blockerats av vårt säkerhetssystem.</p>
        <p style="font-size: 14px; margin-top: 20px; opacity: 0.7;">
            Om du tror detta är ett fel, kontakta support@sortmeout.saidborna.com
        </p>
    </div>
</body>
</html>
```

---

## 15. Additional Recommendations

### A. IP Access Rules

Under **Security** → **WAF** → **Tools**:

Blockera kända dåliga IP-ranges:

- VPN-provider (om du vill)
- Hosting-providers kända för scraping
- Tor exit nodes

### B. Zone Lockdown (valfritt)

För kritiska endpoints:

```
URL: /admin/*
Allowed IPs:
  - Your office IP
  - Your home IP
```

### C. User Agent Blocking

Skapa custom rules för att blockera specifika user agents:

```
(http.user_agent eq "BadBot/1.0") or
(http.user_agent contains "Scraper")
```

---

## 16. Testing Your Configuration

### Säkerhetstester

1. **SSL Test**: <https://www.ssllabs.com/ssltest/>
   - Mål: A+ rating

2. **Security Headers**: <https://securityheaders.com/>
   - Mål: A+ rating

3. **CSP Validator**: <https://csp-evaluator.withgoogle.com/>

4. **Try DevTools**:
   - Öppna F12 på din webbplats
   - Bekräfta att säkerhetsskyddetet aktiveras

5. **Bot Test**:

   ```bash
   curl -A "BadBot/1.0" https://sortmeout.saidborna.com/
   # Ska blockeras
   ```

---

## 17. Maintenance Checklist

### Månatligt

- [ ] Kontrollera Firewall Analytics
- [ ] Granska blocked requests
- [ ] Uppdatera Rate Limiting om nödvändigt
- [ ] Kontrollera false positives

### Kvartalsvis

- [ ] Review och uppdatera firewall rules
- [ ] Testa alla säkerhetsfunktioner
- [ ] Uppdatera IP whitelist/blacklist
- [ ] Kontrollera SSL-certifikat

### Årligen

- [ ] Full säkerhetsaudit
- [ ] Uppdatera CSP policy
- [ ] Review och optimera cache settings

---

## 18. Emergency Response

### Om webbplatsen är under attack

1. **Aktivera "I'm Under Attack Mode"**:
   - Gå till **Security** → **Settings**
   - Sätt Security Level till "I'm Under Attack"

2. **Enable DDoS override**:
   - Cloudflare gör detta automatiskt för stora attacker

3. **Temporary blocklist**:
   - Blockera misstänkta IP-ranges tillfälligt

4. **Contact Cloudflare Support** (om betalkund)

---

## 19. Kostnadsfri vs. Betalplan

### Free Plan inkluderar

- ✅ Basic DDoS protection
- ✅ SSL/TLS
- ✅ Basic firewall rules
- ✅ Page rules (3 st)
- ✅ Bot Fight Mode

### Pro Plan ($20/mån) ger

- ✅ 20 Page Rules
- ✅ WAF
- ✅ Image optimization
- ✅ Advanced Certificate Manager

### Business Plan ($200/mån) ger

- ✅ 50 Page Rules
- ✅ Advanced DDoS
- ✅ Custom SSL
- ✅ 100% uptime SLA

---

## Sammanfattning

Med denna konfiguration har du:

1. ✅ **Fullständigt SSL/TLS-skydd**
2. ✅ **Avancerad bot- och scraper-blockering**
3. ✅ **Rate limiting för att förhindra missbruk**
4. ✅ **Säkerhetsheaders för att skydda användare**
5. ✅ **DDoS-skydd**
6. ✅ **Prestationsoptimering**
7. ✅ **Övervakning och varningar**

Din SortMeOut-webbplats är nu **maximalt skyddad** mot:

- 🛡️ DevTools scraping
- 🛡️ Automated bots
- 🛡️ DDoS-attacker
- 🛡️ Injection attacks
- 🛡️ Man-in-the-middle
- 🛡️ Clickjacking
- 🛡️ XSS attacks

---

**Frågor?** Kontakta Cloudflare support eller läs deras dokumentation:
<https://developers.cloudflare.com/>
