/**
 * SortMeOut API — Cloudflare Worker
 *
 * Handles:
 * 1. Stripe webhooks (subscription lifecycle)
 * 2. License key generation and validation
 * 3. Stripe Checkout session creation
 * 4. Owner notifications (email + Discord)
 *
 * Flow:
 *   User → "Get Pro" → POST /api/checkout → Stripe Checkout URL
 *   Stripe → webhook → POST /api/webhook → generates license key → stores in KV
 *   User → enters key in app → POST /api/verify → validates key
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MAX_EMAIL_LENGTH = 254;
const WEBHOOK_EVENT_TTL_SECONDS = 60 * 60 * 24 * 30;

// ==========================================
// Shared Helpers
// ==========================================

function normalizeEmail(email) {
    return String(email || '').trim().toLowerCase();
}

function isValidEmail(email) {
    const normalized = normalizeEmail(email);
    return normalized.length > 3 && normalized.length <= MAX_EMAIL_LENGTH && EMAIL_REGEX.test(normalized);
}

function maskLicenseKey(licenseKey) {
    if (typeof licenseKey !== 'string' || !licenseKey) {
        return null;
    }

    const parts = licenseKey.split('-');
    if (parts.length !== 5 || parts[0] !== 'SORTMEOUT') {
        return null;
    }

    return `${parts[0]}-${parts[1]}-${parts[2]}-****-${parts[4]}`;
}

function timingSafeEqual(a, b) {
    if (typeof a !== 'string' || typeof b !== 'string') {
        return false;
    }

    const maxLength = Math.max(a.length, b.length);
    let mismatch = a.length ^ b.length;

    for (let i = 0; i < maxLength; i += 1) {
        const codeA = i < a.length ? a.charCodeAt(i) : 0;
        const codeB = i < b.length ? b.charCodeAt(i) : 0;
        mismatch |= codeA ^ codeB;
    }

    return mismatch === 0;
}

// ==========================================
// Owner Notifications
// ==========================================

/**
 * Send notification to the owner about business events.
 * Uses MailChannels (free via CF Workers) and optionally Discord webhook.
 * Fire-and-forget — failures never block the main flow.
 */
async function notifyOwner(env, subject, details) {
    const promises = [];

    // 1. Email notification via MailChannels
    promises.push(sendEmailNotification(env, subject, details).catch(err => {
        console.error('Email notification failed:', err.message);
    }));

    // 2. Discord webhook (if configured)
    if (env.DISCORD_WEBHOOK_URL) {
        promises.push(sendDiscordNotification(env, subject, details).catch(err => {
            console.error('Discord notification failed:', err.message);
        }));
    }

    // Don't await — fire and forget so webhook response isn't delayed
    await Promise.allSettled(promises);
}

/**
 * Send email via MailChannels API (free for Cloudflare Workers).
 * Requires DNS TXT record: _mailchannels.sortmeout.saidborna.com → "v=mc1 cfid=sortmeout-api"
 */
async function sendEmailNotification(env, subject, details) {
    const ownerEmail = env.OWNER_EMAIL;
    if (!ownerEmail) {
        console.error('OWNER_EMAIL not configured — skipping notification email');
        return;
    }
    const fromDomain = env.FROM_DOMAIN || 'sortmeout.saidborna.com';

    const htmlBody = `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #6366F1, #8B5CF6); padding: 20px 24px; border-radius: 12px 12px 0 0;">
                <h2 style="color: white; margin: 0; font-size: 18px;">🗂️ SortMeOut — ${subject}</h2>
            </div>
            <div style="background: #1a1a2e; color: #e4e4e7; padding: 24px; border-radius: 0 0 12px 12px; border: 1px solid #27273a;">
                ${Object.entries(details).map(([key, val]) =>
        `<p style="margin: 8px 0;"><strong style="color: #a78bfa;">${key}:</strong> ${val}</p>`
    ).join('')}
                <hr style="border: none; border-top: 1px solid #27273a; margin: 16px 0;">
                <p style="color: #71717a; font-size: 12px; margin: 0;">Tidpunkt: ${new Date().toISOString()}</p>
            </div>
        </div>
    `;

    const response = await fetch('https://api.mailchannels.net/tx/v1/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            personalizations: [{
                to: [{ email: ownerEmail, name: 'Said Borna' }],
            }],
            from: {
                email: `notifications@${fromDomain}`,
                name: 'SortMeOut Bot',
            },
            subject: `[SortMeOut] ${subject}`,
            content: [{
                type: 'text/html',
                value: htmlBody,
            }],
        }),
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`MailChannels ${response.status}: ${text}`);
    }
}

/**
 * Send notification to Discord channel via webhook.
 */
async function sendDiscordNotification(env, subject, details) {
    const color = subject.includes('Ny Pro')
        ? 0x22c55e   // green — new sale
        : subject.includes('Avbokad')
            ? 0xef4444  // red — cancellation
            : subject.includes('Misslyckad')
                ? 0xf59e0b // yellow — payment failed
                : 0x6366f1; // indigo — other

    const fields = Object.entries(details).map(([name, value]) => ({
        name,
        value: String(value),
        inline: true,
    }));

    await fetch(env.DISCORD_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            embeds: [{
                title: `🗂️ ${subject}`,
                color,
                fields,
                timestamp: new Date().toISOString(),
                footer: { text: 'SortMeOut API' },
            }],
        }),
    });
}

// ==========================================
// License Key Generation
// ==========================================

/**
 * Generate a deterministic license key from customer data.
 * Format: SORTMEOUT-XXXX-XXXX-XXXX-CHECKSUM
 *
 * The key encodes the customer email hash so we can verify
 * it belongs to the right customer without a database lookup.
 */
async function generateLicenseKey(email, signingKey) {
    const encoder = new TextEncoder();

    // Create HMAC of email with signing key
    const key = await crypto.subtle.importKey(
        'raw',
        encoder.encode(signingKey),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
    );

    const signature = await crypto.subtle.sign(
        'HMAC',
        key,
        encoder.encode(email.toLowerCase().trim())
    );

    // Convert to hex and format as license key
    const hex = Array.from(new Uint8Array(signature))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
        .toUpperCase();

    // Take segments for the key body
    const seg1 = hex.substring(0, 4);
    const seg2 = hex.substring(4, 8);
    const seg3 = hex.substring(8, 12);

    // Generate checksum of the key body
    const keyBody = `SORTMEOUT-${seg1}-${seg2}-${seg3}`;
    const checksumData = await crypto.subtle.digest(
        'SHA-256',
        encoder.encode(keyBody)
    );
    const checksum = Array.from(new Uint8Array(checksumData))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
        .toUpperCase()
        .substring(0, 8);

    return `${keyBody}-${checksum}`;
}

/**
 * Verify a license key format and checksum.
 */
async function verifyLicenseKeyFormat(licenseKey) {
    if (!licenseKey || licenseKey.length < 20) return false;

    const parts = licenseKey.split('-');
    if (parts.length !== 5 || parts[0] !== 'SORTMEOUT') return false;

    // Verify checksum
    const keyBody = parts.slice(0, 4).join('-');
    const checksumData = await crypto.subtle.digest(
        'SHA-256',
        new TextEncoder().encode(keyBody)
    );
    const expectedChecksum = Array.from(new Uint8Array(checksumData))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
        .toUpperCase()
        .substring(0, 8);

    return parts[4] === expectedChecksum;
}


// ==========================================
// Stripe Webhook Signature Verification
// ==========================================

async function verifyStripeSignature(body, signature, secret) {
    const parts = signature.split(',');
    const timestamp = parts.find(p => p.startsWith('t='))?.split('=')[1];
    const sig = parts.find(p => p.startsWith('v1='))?.split('=')[1];

    if (!timestamp || !sig) return false;

    // Check timestamp tolerance (5 minutes)
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(timestamp, 10)) > 300) return false;

    // Compute expected signature
    const payload = `${timestamp}.${body}`;
    const key = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(secret),
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
    );

    const expectedSig = await crypto.subtle.sign(
        'HMAC',
        key,
        new TextEncoder().encode(payload)
    );

    const expectedHex = Array.from(new Uint8Array(expectedSig))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('');

    return timingSafeEqual(sig, expectedHex);
}


// ==========================================
// Request Handlers
// ==========================================

/**
 * POST /api/checkout
 * Creates a Stripe Checkout session and returns the URL.
 */
async function handleCheckout(request, env) {
    const payload = await request.json().catch(() => null);
    if (!payload || typeof payload !== 'object') {
        return jsonResponse({ error: 'Invalid request body' }, 400);
    }

    if (!env.STRIPE_SECRET_KEY || !env.STRIPE_PRICE_ID || !env.CORS_ORIGIN) {
        return jsonResponse({ error: 'Checkout is not configured' }, 500);
    }

    const email = typeof payload.email === 'string' ? normalizeEmail(payload.email) : '';
    if (email && !isValidEmail(email)) {
        return jsonResponse({ error: 'Invalid email format' }, 400);
    }

    const params = new URLSearchParams({
        'mode': 'subscription',
        'line_items[0][price]': env.STRIPE_PRICE_ID,
        'line_items[0][quantity]': '1',
        'success_url': `${env.CORS_ORIGIN}/success?session_id={CHECKOUT_SESSION_ID}`,
        'cancel_url': `${env.CORS_ORIGIN}/#pricing`,
        'subscription_data[trial_period_days]': '7',
        'allow_promotion_codes': 'true',
    });

    if (email) {
        params.append('customer_email', email);
    }

    const response = await fetch('https://api.stripe.com/v1/checkout/sessions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
    });

    const session = await response.json();

    if (!response.ok) {
        console.error('Stripe checkout error:', JSON.stringify(session));
        return jsonResponse({ error: 'Failed to create checkout session' }, 500);
    }

    return jsonResponse({ url: session.url });
}

/**
 * POST /api/webhook
 * Handles Stripe webhook events for subscription lifecycle.
 */
async function handleWebhook(request, env) {
    const body = await request.text();
    const signature = request.headers.get('stripe-signature');

    if (!signature) {
        return jsonResponse({ error: 'Missing signature' }, 400);
    }

    // Verify webhook signature
    const isValid = await verifyStripeSignature(body, signature, env.STRIPE_WEBHOOK_SECRET);
    if (!isValid) {
        console.error('Invalid webhook signature');
        return jsonResponse({ error: 'Invalid signature' }, 400);
    }

    let event;
    try {
        event = JSON.parse(body);
    } catch {
        return jsonResponse({ error: 'Invalid webhook JSON payload' }, 400);
    }

    if (!event || typeof event !== 'object' || !event.type || !event.id) {
        return jsonResponse({ error: 'Invalid webhook event payload' }, 400);
    }

    const eventKey = `event:${event.id}`;
    const previouslyProcessed = await env.LICENSES.get(eventKey);
    if (previouslyProcessed) {
        console.log(`Webhook event already processed: ${event.id}`);
        return jsonResponse({ received: true, duplicate: true });
    }

    console.log(`Webhook event: ${event.type}`);

    switch (event.type) {
        case 'checkout.session.completed': {
            const session = event.data.object;
            const email = normalizeEmail(session.customer_email || session.customer_details?.email);
            const customerId = session.customer;
            const subscriptionId = session.subscription;

            if (email && isValidEmail(email)) {
                // Generate license key
                const licenseKey = await generateLicenseKey(email, env.LICENSE_SIGNING_KEY);

                // Store in KV: key → license data
                const licenseData = {
                    email: email,
                    customerId: customerId,
                    subscriptionId: subscriptionId,
                    licenseKey: licenseKey,
                    status: 'active',
                    createdAt: new Date().toISOString(),
                };

                // Store by license key (for verification)
                await env.LICENSES.put(`key:${licenseKey}`, JSON.stringify(licenseData));
                // Store by email (for lookup)
                await env.LICENSES.put(`email:${email}`, JSON.stringify(licenseData));
                // Store by customer ID (for webhook updates)
                await env.LICENSES.put(`customer:${customerId}`, JSON.stringify(licenseData));

                console.log(`License generated for ${email}: ${licenseKey}`);

                // Notify owner of new Pro customer
                await notifyOwner(env, 'Ny Pro-kund! 💰', {
                    'Email': email,
                    'Licensnyckel': licenseKey,
                    'Stripe Customer': customerId,
                    'Prenumeration': subscriptionId,
                    'Belopp': '$9.99/mån',
                });
            } else {
                console.warn('Checkout session completed without valid customer email');
            }
            break;
        }

        case 'customer.subscription.updated': {
            const subscription = event.data.object;
            const customerId = subscription.customer;
            const status = subscription.status;

            const stored = await env.LICENSES.get(`customer:${customerId}`, 'json');
            if (stored) {
                stored.status = status === 'active' || status === 'trialing' ? 'active' : 'inactive';
                stored.updatedAt = new Date().toISOString();

                await env.LICENSES.put(`key:${stored.licenseKey}`, JSON.stringify(stored));
                await env.LICENSES.put(`email:${stored.email.toLowerCase()}`, JSON.stringify(stored));
                await env.LICENSES.put(`customer:${customerId}`, JSON.stringify(stored));

                console.log(`Subscription updated for ${stored.email}: ${stored.status}`);

                // Notify owner of subscription change
                await notifyOwner(env, `Prenumeration uppdaterad: ${stored.status}`, {
                    'Email': stored.email,
                    'Ny status': stored.status,
                    'Customer ID': customerId,
                });
            }
            break;
        }

        case 'customer.subscription.deleted': {
            const subscription = event.data.object;
            const customerId = subscription.customer;

            const stored = await env.LICENSES.get(`customer:${customerId}`, 'json');
            if (stored) {
                stored.status = 'cancelled';
                stored.cancelledAt = new Date().toISOString();

                await env.LICENSES.put(`key:${stored.licenseKey}`, JSON.stringify(stored));
                await env.LICENSES.put(`email:${stored.email.toLowerCase()}`, JSON.stringify(stored));
                await env.LICENSES.put(`customer:${customerId}`, JSON.stringify(stored));

                console.log(`Subscription cancelled for ${stored.email}`);

                // Notify owner of cancellation
                await notifyOwner(env, 'Prenumeration avbokad ❌', {
                    'Email': stored.email,
                    'Customer ID': customerId,
                    'Avbokad': stored.cancelledAt,
                });
            }
            break;
        }

        case 'invoice.payment_failed': {
            const invoice = event.data.object;
            const customerId = invoice.customer;

            const stored = await env.LICENSES.get(`customer:${customerId}`, 'json');
            if (stored) {
                stored.status = 'past_due';
                stored.updatedAt = new Date().toISOString();

                await env.LICENSES.put(`key:${stored.licenseKey}`, JSON.stringify(stored));
                await env.LICENSES.put(`email:${stored.email.toLowerCase()}`, JSON.stringify(stored));
                await env.LICENSES.put(`customer:${customerId}`, JSON.stringify(stored));

                console.log(`Payment failed for ${stored.email}`);

                // Notify owner of payment failure
                await notifyOwner(env, 'Betalning misslyckad ⚠️', {
                    'Email': stored.email,
                    'Customer ID': customerId,
                    'Status': 'past_due',
                });
            }
            break;
        }
    }

    await env.LICENSES.put(eventKey, new Date().toISOString(), {
        expirationTtl: WEBHOOK_EVENT_TTL_SECONDS,
    });

    return jsonResponse({ received: true });
}

/**
 * POST /api/verify
 * Verify a license key and return its status.
 * Called by the desktop app when user enters a key.
 */
async function handleVerify(request, env) {
    const payload = await request.json().catch(() => null);
    if (!payload || typeof payload !== 'object') {
        return jsonResponse({ valid: false, error: 'Invalid request body' }, 400);
    }

    const license_key = typeof payload.license_key === 'string'
        ? payload.license_key.trim().toUpperCase()
        : '';

    if (!license_key) {
        return jsonResponse({ valid: false, error: 'Missing license key' }, 400);
    }

    // First check format
    const validFormat = await verifyLicenseKeyFormat(license_key);
    if (!validFormat) {
        return jsonResponse({ valid: false, error: 'Invalid license key format' });
    }

    // Look up in KV
    const stored = await env.LICENSES.get(`key:${license_key}`, 'json');
    if (!stored) {
        return jsonResponse({ valid: false, error: 'License key not found' });
    }

    return jsonResponse({
        valid: stored.status === 'active',
        status: stored.status,
        email: stored.email,
    });
}

/**
 * GET /api/license?email=...
 * Support/status lookup by email (returns masked key only).
 */
async function handleLicenseLookup(request, env) {
    const url = new URL(request.url);
    const email = normalizeEmail(url.searchParams.get('email'));

    if (!email) {
        return jsonResponse({ error: 'Missing email parameter' }, 400);
    }

    if (!isValidEmail(email)) {
        return jsonResponse({ error: 'Invalid email format' }, 400);
    }

    const stored = await env.LICENSES.get(`email:${email}`, 'json');
    if (!stored) {
        return jsonResponse({ found: false });
    }

    // Never return full license keys from unauthenticated lookup.
    // Keep this endpoint safe for support/status checks only.
    return jsonResponse({
        found: true,
        status: stored.status,
        license_key_masked: stored.status === 'active' ? maskLicenseKey(stored.licenseKey) : null,
    });
}

/**
 * GET /api/checkout/success?session_id=...
 * Retrieve license key after successful checkout.
 */
async function handleCheckoutSuccess(request, env) {
    const url = new URL(request.url);
    const sessionId = url.searchParams.get('session_id');

    if (!sessionId) {
        return jsonResponse({ error: 'Missing session_id' }, 400);
    }

    // Retrieve session from Stripe to get customer email
    const response = await fetch(`https://api.stripe.com/v1/checkout/sessions/${sessionId}`, {
        headers: {
            'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
        },
    });

    const session = await response.json();
    if (!response.ok) {
        return jsonResponse({ error: 'Invalid session' }, 400);
    }

    const email = normalizeEmail(session.customer_email || session.customer_details?.email);
    if (!email || !isValidEmail(email)) {
        return jsonResponse({ error: 'No email found for session' }, 400);
    }

    // Look up license
    const stored = await env.LICENSES.get(`email:${email}`, 'json');
    if (!stored) {
        // Webhook might not have fired yet — generate key now
        const licenseKey = await generateLicenseKey(email, env.LICENSE_SIGNING_KEY);
        return jsonResponse({
            email: email,
            license_key: licenseKey,
            status: 'active',
            note: 'Your license key will be fully activated shortly.',
        });
    }

    return jsonResponse({
        email: stored.email,
        license_key: stored.licenseKey,
        status: stored.status,
    });
}


// ==========================================
// Router & CORS
// ==========================================

function jsonResponse(data, status = 200) {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-store',
        },
    });
}

/**
 * Add CORS headers to a response using the configured origin.
 */
function withCors(response, corsOrigin) {
    const headers = new Headers(response.headers);
    headers.set('Access-Control-Allow-Origin', corsOrigin);
    headers.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    headers.set('Access-Control-Allow-Headers', 'Content-Type');
    return new Response(response.body, {
        status: response.status,
        headers,
    });
}

function handleCors(request, env) {
    return new Response(null, {
        status: 204,
        headers: {
            'Access-Control-Allow-Origin': env.CORS_ORIGIN || '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '86400',
        },
    });
}

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const path = url.pathname;
        const corsOrigin = env.CORS_ORIGIN || '*';

        // Handle CORS preflight
        if (request.method === 'OPTIONS') {
            return handleCors(request, env);
        }

        try {
            let response;

            // Route requests
            if (path === '/api/checkout' && request.method === 'POST') {
                response = await handleCheckout(request, env);
            } else if (path === '/api/webhook' && request.method === 'POST') {
                response = await handleWebhook(request, env);
            } else if (path === '/api/verify' && request.method === 'POST') {
                response = await handleVerify(request, env);
            } else if (path === '/api/license' && request.method === 'GET') {
                response = await handleLicenseLookup(request, env);
            } else if (path === '/api/checkout/success' && request.method === 'GET') {
                response = await handleCheckoutSuccess(request, env);
            } else if (path === '/api/health') {
                response = jsonResponse({ status: 'ok', version: '1.0.1' });
            } else {
                response = jsonResponse({ error: 'Not found' }, 404);
            }

            // Apply CORS headers to all responses
            return withCors(response, corsOrigin);

        } catch (error) {
            console.error('Worker error:', error);
            return withCors(jsonResponse({ error: 'Internal server error' }, 500), corsOrigin);
        }
    },
};
