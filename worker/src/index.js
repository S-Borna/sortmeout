/**
 * SortMeOut API — Cloudflare Worker
 *
 * Handles:
 * 1. Stripe webhooks (subscription lifecycle)
 * 2. License key generation and validation
 * 3. Stripe Checkout session creation
 *
 * Flow:
 *   User → "Get Pro" → POST /api/checkout → Stripe Checkout URL
 *   Stripe → webhook → POST /api/webhook → generates license key → stores in KV
 *   User → enters key in app → POST /api/verify → validates key
 */

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
    if (Math.abs(now - parseInt(timestamp)) > 300) return false;

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

    return sig === expectedHex;
}


// ==========================================
// Request Handlers
// ==========================================

/**
 * POST /api/checkout
 * Creates a Stripe Checkout session and returns the URL.
 */
async function handleCheckout(request, env) {
    const { email } = await request.json().catch(() => ({}));

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

    const event = JSON.parse(body);
    console.log(`Webhook event: ${event.type}`);

    switch (event.type) {
        case 'checkout.session.completed': {
            const session = event.data.object;
            const email = session.customer_email || session.customer_details?.email;
            const customerId = session.customer;
            const subscriptionId = session.subscription;

            if (email) {
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
                await env.LICENSES.put(`email:${email.toLowerCase()}`, JSON.stringify(licenseData));
                // Store by customer ID (for webhook updates)
                await env.LICENSES.put(`customer:${customerId}`, JSON.stringify(licenseData));

                console.log(`License generated for ${email}: ${licenseKey}`);
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
            }
            break;
        }
    }

    return jsonResponse({ received: true });
}

/**
 * POST /api/verify
 * Verify a license key and return its status.
 * Called by the desktop app when user enters a key.
 */
async function handleVerify(request, env) {
    const { license_key } = await request.json().catch(() => ({}));

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
 * Look up license key by email (for re-sending).
 */
async function handleLicenseLookup(request, env) {
    const url = new URL(request.url);
    const email = url.searchParams.get('email');

    if (!email) {
        return jsonResponse({ error: 'Missing email parameter' }, 400);
    }

    const stored = await env.LICENSES.get(`email:${email.toLowerCase().trim()}`, 'json');
    if (!stored) {
        return jsonResponse({ found: false });
    }

    // Return license key only if subscription is active
    return jsonResponse({
        found: true,
        status: stored.status,
        // Only reveal the key if active
        license_key: stored.status === 'active' ? stored.licenseKey : null,
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

    const email = session.customer_email || session.customer_details?.email;
    if (!email) {
        return jsonResponse({ error: 'No email found for session' }, 400);
    }

    // Look up license
    const stored = await env.LICENSES.get(`email:${email.toLowerCase().trim()}`, 'json');
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
