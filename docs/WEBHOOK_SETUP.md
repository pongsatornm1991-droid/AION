# AION real-time comment webhook (optional, free)

`check-comments.yml` already polls for new Facebook/Instagram comments
every 5 minutes on its own — that path is unchanged and keeps working with
zero setup. This adds a second, faster path: Meta pushes a webhook the
instant a real comment lands, and a small Cloudflare Worker (`webhook/worker.js`)
relays that into a `repository_dispatch` that makes `check-comments.yml` run
immediately instead of waiting for its next scheduled tick (which, on this
low-traffic repo, GitHub itself often throttles to well over 5 minutes —
see the project docs). Nothing else about AION changes: the Worker never
talks to Facebook, Instagram, Gemini, or Telegram, never touches AION's
memory, and never decides what AION says — it only wakes the existing,
already-tested pipeline up sooner.

This step is entirely optional and free (Cloudflare's free plan is more
than enough for this volume, no credit card required). Skipping it changes
nothing — the 5-minute poll keeps running exactly as it does today.

## 1. Deploy the Worker (Cloudflare dashboard, no CLI needed)

1. Go to https://dash.cloudflare.com/ and sign up for a free account if you
   don't already have one.
2. In the sidebar: **Workers & Pages** → **Create** → **Create Worker**.
   Give it any name, e.g. `aion-webhook`. Deploy the default "Hello World"
   template first — you'll replace it next.
3. Click **Edit code** (the online editor). Delete everything in the editor
   and paste in the full contents of this repo's `webhook/worker.js` file.
4. Click **Deploy**. Cloudflare gives you a URL like
   `https://aion-webhook.<your-subdomain>.workers.dev` — copy it, you'll
   need it in step 3 below.

## 2. Add the Worker's secrets

Still on the Worker's page: **Settings** → **Variables and Secrets** → **Add**.
Add these four, each as **Secret** (not plain text) except where noted:

| Name | Value | Where to find it |
|---|---|---|
| `META_APP_SECRET` | the Facebook App Secret you already have | Meta for Developers → your app ("สมองกลสร้างเรื่อง") → App settings → Basic → App Secret |
| `META_VERIFY_TOKEN` | any random string you make up yourself, e.g. a long password | you invent this — write it down, you'll paste the exact same value into Meta's webhook setup in step 3 |
| `GITHUB_PAT` | a new GitHub personal access token | GitHub → your profile picture → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token. Scope: `repo`. Copy it immediately — GitHub only shows it once. |
| `GITHUB_REPO` | `pongsatornm1991-droid/AION` | this repo, exactly as-is (can be a plain variable, not secret) |

Click **Deploy** again after adding them so the Worker picks them up.

## 3. Subscribe to webhooks in the Meta App dashboard

1. Meta for Developers → your app → **Webhooks** (left sidebar; add the
   product if it isn't already there).
2. For the **Page** object: click **Subscribe to this object**, paste your
   Worker URL from step 1 as the **Callback URL**, paste the exact
   `META_VERIFY_TOKEN` value from step 2 as the **Verify token**, click
   **Verify and save**. Then subscribe to the **`feed`** field.
3. For the **Instagram** object: same Callback URL and Verify token, then
   subscribe to the **`comments`** field.
4. Meta calls your Worker once immediately to verify (a `GET` request) —
   if the token matches, it shows a green checkmark. If it fails, double
   check the `META_VERIFY_TOKEN` value matches exactly on both sides.
5. Under **Page** → **Manage** (or via the "Test" button next to the
   subscription), send a test event to confirm the Worker responds `200`.

## 4. Confirm it's working end to end

Post a real comment on a public post on the Facebook Page or Instagram
account, then check
`https://github.com/pongsatornm1991-droid/AION/actions/workflows/check-comments.yml` —
a new run should start within a few seconds (event: "Dispatched"), rather
than waiting for the next 5-minute schedule tick.

## If something goes wrong

- **Nothing happens on a new comment**: check the Worker's own logs
  (Cloudflare dashboard → your Worker → Logs) for errors, and confirm all
  four secrets in step 2 are set correctly (a missing `GITHUB_PAT` or
  `GITHUB_REPO` silently does nothing, by design — see the comment in
  `webhook/worker.js`'s `triggerCheckComments()`).
- **Meta shows the webhook subscription as failing repeatedly**: this is
  safe to ignore short-term — `check-comments.yml`'s existing 5-minute poll
  keeps catching every comment regardless, just up to a few minutes later.
- **Want to remove this later**: delete the Worker in Cloudflare and remove
  the subscription in Meta's Webhooks screen. `check-comments.yml` keeps
  working exactly as before — the `repository_dispatch` trigger added to it
  simply never fires again.
