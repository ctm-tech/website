/**
 * POST /api/contact
 *
 * Cloudflare Pages Function. Receives the contact form, validates it,
 * runs spam checks, and sends the enquiry on via Resend.
 *
 * Environment variables (Pages → Settings → Environment variables):
 *   RESEND_API_KEY    (secret, required)  API key from resend.com
 *   CONTACT_TO        (required)          Inbox that receives enquiries
 *   CONTACT_FROM      (required)          e.g. "CTM Tech Website <enquiries@ctm-tech.co.uk>"
 *                                         Domain MUST be verified in Resend.
 *   TURNSTILE_SECRET  (secret, optional)  If set, Turnstile is enforced.
 *
 * Set these for BOTH Production and Preview, or previews will 500.
 */

const MAX_FIELD = 5000;

const json = (status, ok, message) =>
  new Response(JSON.stringify({ ok, message }), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8' },
  });

const esc = (s) =>
  String(s ?? '').replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
  );

const clean = (v) => String(v ?? '').trim().slice(0, MAX_FIELD);

// Deliberately permissive. Real validation is whether the reply bounces.
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

export async function onRequestPost(context) {
  const { request, env } = context;

  // --- config sanity -------------------------------------------------
  for (const key of ['RESEND_API_KEY', 'CONTACT_TO', 'CONTACT_FROM']) {
    if (!env[key]) {
      console.error(`Missing environment variable: ${key}`);
      return json(500, false, 'The form is not configured correctly. Please email us directly.');
    }
  }

  // --- parse ---------------------------------------------------------
  let form;
  try {
    form = await request.formData();
  } catch {
    return json(400, false, 'Could not read the form data. Please try again.');
  }

  const data = {
    name: clean(form.get('name')),
    company: clean(form.get('company')),
    email: clean(form.get('email')),
    phone: clean(form.get('phone')),
    type: clean(form.get('type')),
    size: clean(form.get('size')),
    message: clean(form.get('message')),
    website: clean(form.get('website')), // honeypot
  };

  // --- honeypot ------------------------------------------------------
  // Bots fill hidden fields. Return success so they don't retry or adapt.
  if (data.website) {
    return json(200, true, "Thanks — we'll be in touch within one business day.");
  }

  // --- validation ----------------------------------------------------
  if (!data.name || !data.email || !data.message) {
    return json(400, false, 'Please fill in your name, email and a short message.');
  }
  if (!EMAIL_RE.test(data.email)) {
    return json(400, false, 'That email address does not look right. Please check it.');
  }
  // Header-injection guard: newlines have no business in a reply-to address.
  if (/[\r\n]/.test(data.email) || /[\r\n]/.test(data.name)) {
    return json(400, false, 'Those details contain characters we cannot accept.');
  }

  // --- Turnstile (only enforced if the secret is configured) ----------
  if (env.TURNSTILE_SECRET) {
    const token = clean(form.get('cf-turnstile-response'));
    if (!token) {
      return json(400, false, 'Please complete the spam check and try again.');
    }
    try {
      const verify = await fetch(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        {
          method: 'POST',
          body: new URLSearchParams({
            secret: env.TURNSTILE_SECRET,
            response: token,
            remoteip: request.headers.get('CF-Connecting-IP') || '',
          }),
        }
      ).then((r) => r.json());

      if (!verify.success) {
        console.warn('Turnstile rejected:', verify['error-codes']);
        return json(400, false, 'Spam check failed. Please reload the page and try again.');
      }
    } catch (err) {
      console.error('Turnstile verification error:', err);
      return json(502, false, 'Could not complete the spam check. Please try again shortly.');
    }
  }

  // --- compose -------------------------------------------------------
  const rows = [
    ['Name', data.name],
    ['Company', data.company],
    ['Email', data.email],
    ['Phone', data.phone],
    ['Enquiry type', data.type],
    ['Users / property', data.size],
  ].filter(([, v]) => v);

  const meta = [
    ['Received', new Date().toISOString()],
    ['From IP', request.headers.get('CF-Connecting-IP')],
    ['Country', request.headers.get('CF-IPCountry')],
  ].filter(([, v]) => v);

  const table = (pairs) =>
    `<table cellpadding="6" cellspacing="0" style="border-collapse:collapse;font:14px/1.5 system-ui,sans-serif">${pairs
      .map(
        ([k, v]) =>
          `<tr><td style="border:1px solid #e5e7eb;background:#f9fafb"><b>${esc(k)}</b></td><td style="border:1px solid #e5e7eb">${esc(v)}</td></tr>`
      )
      .join('')}</table>`;

  const html = `
    <div style="font:14px/1.6 system-ui,sans-serif;color:#111">
      <h2 style="margin:0 0 12px;font-size:17px">New enquiry via ctm-tech.co.uk</h2>
      ${table(rows)}
      <h3 style="margin:20px 0 8px;font-size:14px">Message</h3>
      <div style="white-space:pre-wrap;padding:12px;background:#f9fafb;border:1px solid #e5e7eb">${esc(data.message)}</div>
      <h3 style="margin:20px 0 8px;font-size:12px;color:#6b7280">Metadata</h3>
      ${table(meta)}
    </div>`;

  const text = [
    'New enquiry via ctm-tech.co.uk',
    '',
    ...rows.map(([k, v]) => `${k}: ${v}`),
    '',
    'Message:',
    data.message,
  ].join('\n');

  // --- send ----------------------------------------------------------
  try {
    const res = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        // MUST be your verified domain. The visitor's address goes in reply_to,
        // otherwise you fail SPF/DKIM alignment and land in spam.
        from: env.CONTACT_FROM,
        to: [env.CONTACT_TO],
        reply_to: data.email,
        subject: `Enquiry: ${data.type || 'General'} — ${data.name}${data.company ? ` (${data.company})` : ''}`,
        html,
        text,
      }),
    });

    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      console.error('Resend error', res.status, detail);
      return json(502, false, 'Your message could not be sent. Please email us directly and we will pick it up.');
    }
  } catch (err) {
    console.error('Resend request failed:', err);
    return json(502, false, 'Your message could not be sent. Please email us directly and we will pick it up.');
  }

  return json(200, true, "Thanks — we'll be in touch within one business day.");
}

// Only onRequestPost is exported, so Pages answers any other method on
// this route with a 405 automatically. Don't add an onRequest catch-all —
// it can shadow the method-specific handler.
