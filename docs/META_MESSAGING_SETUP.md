# Enable AION inbox replies

The reply cycle is already deployed in `check-comments.yml` and runs every
five minutes. It remains deliberately off until Meta grants messaging access;
turning on the GitHub variable first cannot bypass Meta's permission check.

## Current connection check (2026-09-09)

| Inbox | Result | Required change |
| --- | --- | --- |
| Facebook Messenger | Meta error 200: `pages_messaging` missing | Add Messenger to the Meta app, request `pages_messaging`, and ensure the token owner has a Page role. |
| Instagram Direct | Meta error 3: app lacks capability | Add Instagram Messaging to the Meta app and complete the required App Review / access configuration for the connected professional account. |

## Meta dashboard steps

1. In [Meta for Developers](https://developers.facebook.com/apps/), open the
   AION app and add the **Messenger** product. Configure the Page under
   Messenger settings and subscribe it to messaging webhooks.
2. Open **App Review → Permissions and Features**. Request
   `pages_messaging` for the Facebook Page use case. The account that creates
   or renews the Page access token must be an administrator, editor, or hold
   another eligible Page role.
3. Add the **Instagram** product / Instagram Messaging use case. Connect the
   same Instagram professional account to its Facebook Page, configure its
   webhook, and complete the messaging access review required by Meta.
4. Generate or renew the Page and Instagram access tokens after the approvals
   are active. Replace only the existing GitHub secrets; never paste tokens
   into this repository.
5. In the GitHub repository open **Settings → Secrets and variables →
   Actions → Variables** and set `AION_MESSAGING_ENABLED` to `true`.
6. Run **AION - check comments** manually once. The run invokes
   `check-facebook-messages` and `check-instagram-messages`; it will read at
   most one new message per inbox per run and retains a durable handled ID so
   it does not answer the same message twice.

## Verification

Send a normal test message from an account that is allowed to message the
Page. The workflow should show `executed` for the relevant inbox. If it shows
`permission-required`, leave `AION_MESSAGING_ENABLED` off and complete the
matching Meta step above. The bot sends only `RESPONSE` messages, so it answers
inside Meta's permitted customer-service reply window and does not initiate
unsolicited conversations.
