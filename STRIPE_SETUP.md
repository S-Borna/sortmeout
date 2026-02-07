# SortMeOut — Stripe & Cloudflare Worker Setup Guide

## Översikt

Denna guide kopplar ihop Stripe-betalningar med SortMeOut via en Cloudflare Worker.

**Flöde:**

```
Användare → "Get Pro" → Stripe Checkout → Betalning
    → Webhook → Cloudflare Worker → Licensnyckel genereras
    → Visas på success-sida + sparas i KV
    → Användare klistrar in nyckel i appen
```

---

## Steg 1: Installera Wrangler (Cloudflare CLI)

```bash
npm install -g wrangler
wrangler login
```

---

## Steg 2: Skapa KV Namespace

```bash
cd worker/
wrangler kv namespace create "LICENSES"
```

Kopiera det ID du får (t.ex. `abc123`) och lägg in i `wrangler.toml`:

```toml
[[kv_namespaces]]
binding = "LICENSES"
id = "abc123"  # ← ditt faktiska ID
```

---

## Steg 3: Sätt hemliga nycklar (Secrets)

**VIKTIGT:** Dessa lagras säkert i Cloudflare — aldrig i kod!

```bash
# Stripe Secret Key
wrangler secret put STRIPE_SECRET_KEY
# → klistra in: sk_test_...  (eller sk_live_ för produktion)

# Webhook signing secret (skapas i steg 5)
wrangler secret put STRIPE_WEBHOOK_SECRET
# → klistra in: whsec_...

# License signing key (generera en slumpmässig sträng)
wrangler secret put LICENSE_SIGNING_KEY
# → klistra in: $(openssl rand -hex 32)
```

Generera LICENSE_SIGNING_KEY:

```bash
openssl rand -hex 32
# Kopiera resultatet och klistra in som secret
```

---

## Steg 4: Deploya Worker

```bash
cd worker/
npm install
wrangler deploy
```

Din Worker körs nu på: `https://sortmeout-api.<ditt-konto>.workers.dev`

### Konfigurera custom domain (rekommenderat)

1. Gå till Cloudflare Dashboard → Workers & Pages → sortmeout-api
2. Klicka **Custom Domains** → Add
3. Lägg till: `api.sortmeout.saidborna.com`
4. Cloudflare skapar DNS-posten automatiskt

---

## Steg 5: Konfigurera Stripe Webhook

1. Gå till [Stripe Dashboard → Developers → Webhooks](https://dashboard.stripe.com/webhooks)
2. Klicka **Add endpoint**
3. URL: `https://api.sortmeout.saidborna.com/api/webhook`
4. Välj dessa events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
5. Klicka **Add endpoint**
6. Kopiera **Signing secret** (börjar med `whsec_`)
7. Spara den som Worker secret:

   ```bash
   wrangler secret put STRIPE_WEBHOOK_SECRET
   # → klistra in: whsec_...
   ```

---

## Steg 6: Testa flödet

### Testa med Stripe test-kort

- **Lyckas:** `4242 4242 4242 4242`
- **Avvisas:** `4000 0000 0000 0002`
- **3D Secure:** `4000 0025 0000 3155`

### Steg

1. Öppna `https://sortmeout.saidborna.com/#pricing`
2. Klicka "Get Pro"
3. Använd testkort `4242 4242 4242 4242`, MM/ÅÅ: `12/34`, CVC: `123`
4. Du bör omdirigeras till success-sidan med din licensnyckel
5. Testa nyckeln i appen: `sortmeout license activate DIN-NYCKEL`

### Verifiera i terminal

```bash
# Testa health
curl https://api.sortmeout.saidborna.com/api/health

# Testa nyckelverifiering
curl -X POST https://api.sortmeout.saidborna.com/api/verify \
  -H "Content-Type: application/json" \
  -d '{"license_key": "DIN-NYCKEL"}'
```

---

## Steg 7: Gå live

När allt fungerar med test-nycklar:

1. **Byt Stripe-nycklar:**

   ```bash
   wrangler secret put STRIPE_SECRET_KEY
   # → klistra in sk_live_...
   ```

2. **Skapa ny webhook** i Stripe (live mode) med samma URL och events

3. **Uppdatera webhook secret:**

   ```bash
   wrangler secret put STRIPE_WEBHOOK_SECRET
   # → klistra in nya whsec_...
   ```

4. **Uppdatera `wrangler.toml`** med live Price ID om du har ett annat:

   ```toml
   [vars]
   STRIPE_PRICE_ID = "price_live_..."
   ```

5. Deploya:

   ```bash
   wrangler deploy
   ```

---

## Felsökning

### Se Worker-loggar i realtid

```bash
wrangler tail
```

### Kontrollera KV-data

```bash
wrangler kv key list --binding LICENSES
wrangler kv key get --binding LICENSES "email:user@example.com"
```

### Stripe webhook-loggar

Gå till Stripe Dashboard → Developers → Webhooks → din endpoint → Attempts

---

## Säkerhet

- ✅ Stripe API-nycklar lagras som Cloudflare Secrets (aldrig i kod)
- ✅ Webhook-signaturer verifieras kryptografiskt
- ✅ Licensnycklar genereras med HMAC-SHA256
- ✅ Checksumvalidering offline (fungerar utan internet)
- ✅ Server-verifiering online (kollar prenumerationsstatus)
- ✅ KV-lagring med tre index (key, email, customer) för snabb lookup
