/**
 * AION Meta webhook relay (Cloudflare Worker).
 *
 * Meta (Facebook Page + Instagram) can push a webhook the instant a new
 * comment arrives, instead of AION only ever finding out up to 5 minutes
 * later (in practice, up to ~2 hours on this low-traffic repo -- see
 * project docs on GitHub Actions cron throttling) via check-comments.yml's
 * own polling schedule. This Worker is the thin, stateless bridge: Meta
 * cannot call GitHub Actions directly, so this receives Meta's webhook,
 * checks it is genuinely from Meta, and -- only for the specific event
 * check-comments.yml already knows how to handle (a new comment) -- fires
 * a `repository_dispatch` so that workflow runs immediately instead of
 * waiting for its next scheduled tick.
 *
 * This Worker deliberately does NOT talk to Facebook/Instagram/Gemini/
 * Telegram itself, does NOT touch AION's memory, and does NOT decide what
 * AION says. All of that stays exactly where it already lives, inside
 * check-comments.yml / brain/comment_reply.py. This file's only job is
 * "wake the existing pipeline up sooner."
 *
 * check-comments.yml keeps its existing 5-minute cron schedule as a
 * fallback safety net -- if a webhook delivery is ever missed, delayed,
 * or this Worker is briefly down, the poll still catches it, just later.
 * Nothing about the existing polling path is removed or changed.
 *
 * Required Worker secrets (set in the Cloudflare dashboard, never in this
 * file or in git):
 *   META_APP_SECRET   - the same Facebook App Secret already used for the
 *                        Graph API tokens (Meta for Developers -> App
 *                        settings -> Basic). Used only to verify each
 *                        incoming webhook is genuinely signed by Meta.
 *   META_VERIFY_TOKEN - any string you invent yourself, entered again in
 *                        Meta's Webhooks setup screen. Proves to Meta this
 *                        endpoint is the one it just configured.
 *   GITHUB_PAT        - a GitHub personal access token scoped only to
 *                        trigger repository_dispatch on this one repo.
 *   GITHUB_REPO       - "owner/repo", e.g. "pongsatornm1991-droid/AION".
 *
 * See docs/WEBHOOK_SETUP.md for the full step-by-step setup (Cloudflare +
 * Meta dashboard clicks) -- nothing here runs on its own until that setup
 * is done.
 */

const DISPATCH_EVENT_TYPE = "new-comment";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET") {
      return handleVerification(url, env);
    }

    if (request.method === "POST") {
      return handleEvent(request, env, ctx);
    }

    return new Response("Method not allowed", { status: 405 });
  },
};

/**
 * Meta's one-time (and re-triggerable) handshake: it sends
 * hub.mode=subscribe, hub.verify_token=<whatever you configured>, and
 * hub.challenge=<random string>. Echoing the challenge back proves this
 * endpoint belongs to whoever configured META_VERIFY_TOKEN.
 */
function handleVerification(url, env) {
  const mode = url.searchParams.get("hub.mode");
  const token = url.searchParams.get("hub.verify_token");
  const challenge = url.searchParams.get("hub.challenge");

  if (mode === "subscribe" && token && env.META_VERIFY_TOKEN && token === env.META_VERIFY_TOKEN) {
    return new Response(challenge ?? "", { status: 200 });
  }
  return new Response("Verification failed", { status: 403 });
}

/**
 * A real webhook delivery. Meta expects a fast 2xx response (well under its
 * own timeout) or it will retry, and repeated failures can eventually get
 * the subscription auto-disabled -- so this always acknowledges quickly and
 * does the actual GitHub call in the background via ctx.waitUntil().
 */
async function handleEvent(request, env, ctx) {
  const rawBody = await request.text();

  const signatureHeader = request.headers.get("x-hub-signature-256") || "";
  const verified = await isValidSignature(rawBody, signatureHeader, env.META_APP_SECRET);
  if (!verified) {
    // Do not process or forward anything that isn't genuinely from Meta.
    return new Response("Invalid signature", { status: 403 });
  }

  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch (err) {
    // Malformed body from a verified sender should never happen; ack
    // anyway so Meta does not retry a payload that will never parse.
    return new Response("OK", { status: 200 });
  }

  if (isNewCommentEvent(payload)) {
    ctx.waitUntil(triggerCheckComments(env, payload));
  }

  return new Response("OK", { status: 200 });
}

/**
 * Verifies X-Hub-Signature-256 (HMAC-SHA256 over the raw request body,
 * keyed with the Meta App Secret) using the Web Crypto API available in
 * Cloudflare Workers. Comparing against the *raw* body (not the parsed
 * JSON) matters -- re-serializing JSON can change byte-for-byte content
 * and would make a genuine signature look invalid.
 */
async function isValidSignature(rawBody, signatureHeader, appSecret) {
  if (!appSecret || !signatureHeader.startsWith("sha256=")) {
    return false;
  }
  const expectedHex = signatureHeader.slice("sha256=".length).trim().toLowerCase();
  if (!expectedHex) {
    return false;
  }

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(appSecret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signatureBytes = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(rawBody));
  const computedHex = Array.from(new Uint8Array(signatureBytes))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");

  return timingSafeEqualHex(computedHex, expectedHex);
}

/** Constant-time comparison so this never leaks timing information. */
function timingSafeEqualHex(a, b) {
  if (a.length !== b.length) {
    return false;
  }
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

/**
 * Recognises exactly the event check-comments.yml already knows how to
 * handle: a brand-new comment on the Facebook Page's feed, or a new
 * Instagram comment. Everything else (likes, shares, message events,
 * edits, deletions, ...) is deliberately ignored -- this relay only ever
 * wakes AION up for the one thing it already reacts to on its own poll.
 */
function isNewCommentEvent(payload) {
  const entries = Array.isArray(payload?.entry) ? payload.entry : [];

  if (payload?.object === "page") {
    return entries.some((entry) =>
      (entry.changes || []).some(
        (change) =>
          change.field === "feed" &&
          change.value?.item === "comment" &&
          change.value?.verb === "add",
      ),
    );
  }

  if (payload?.object === "instagram") {
    return entries.some((entry) => (entry.changes || []).some((change) => change.field === "comments"));
  }

  return false;
}

/**
 * Fires a repository_dispatch so check-comments.yml runs right now instead
 * of waiting for its next 5-minute (in practice, further-throttled) cron
 * tick. A failure here (GitHub API down, bad token, etc.) is swallowed on
 * purpose -- the existing schedule is still running independently and will
 * pick the same comment up shortly regardless, so this relay failing must
 * never turn into a user-facing error or a retry storm back to Meta.
 */
async function triggerCheckComments(env, payload) {
  if (!env.GITHUB_PAT || !env.GITHUB_REPO) {
    return;
  }
  try {
    await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "aion-webhook-relay",
      },
      body: JSON.stringify({
        event_type: DISPATCH_EVENT_TYPE,
        client_payload: { source: payload?.object ?? "unknown" },
      }),
    });
  } catch (err) {
    // Intentionally swallowed -- see docstring above.
  }
}
