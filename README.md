# Channel Tracker Bot

Tracks, with real per-person identity, two things Telegram actually exposes for a
broadcast channel:

1. **Who joined** — via a unique invite link per friend + `chat_member` updates.
2. **Who clicked** — via an inline "✅ Mark as read" button + `callback_query` updates.

Both events DM you live the moment they happen.

It does **not** fake passive read-receipts. Telegram never exposes per-user "seen"
status for a real broadcast channel, to anyone, through any API — that's a deliberate
privacy wall, not a missing feature. The "Mark as read" button is the honest substitute:
a tap is a real, verifiable confirmation, and it's the same trick every newsletter and
read-receipt-less platform uses.

## Setup

1. **Create the bot**: message [@BotFather](https://t.me/BotFather) → `/newbot` → copy
   the token into `BOT_TOKEN`.

2. **Add the bot as admin** of your channel, with at least:
   - "Invite users via link" (needed for `/invite`)
   - "Post messages" (needed for `/post`)
   - "Edit messages of others" (needed to attach the tracked button after posting)

3. **Get your channel ID**: if the channel has a public `@username`, you can just put
   `@yourchannel` in `CHANNEL_ID`. If it's private, forward any message from the
   channel to [@JsonDumpBot](https://t.me/JsonDumpBot) (or similar) to read the numeric
   ID (looks like `-1001234567890`).

4. **Get your own user ID**: open a private chat with your bot, send `/start`, then
   `/myid`. Put that number in `OWNER_ID`.

   Important: Telegram bots can't message a user who hasn't messaged them first —
   so you must send `/start` to your own bot in a private chat before any
   notifications can reach you.

5. Install and run:
   ```bash
   cp .env.example .env   # fill in the three values
   pip install -r requirements.txt
   python bot.py
   ```

## Using it

- `/invite Sara` → bot creates a one-time invite link tied to "Sara" and replies with
  it. Send that exact link to Sara only. When she joins through it, you get
  `🔔 Sara just joined the channel.`
- `/post Hey everyone, new update is live` → bot publishes that text to the channel
  with a "✅ Mark as read" button, and replies with a post number like `#3`.
  Every distinct person who taps it triggers `🔔 <name> tapped 'read' on post #3.`
- `/friends` → list of everyone you've invited and whether they've joined yet.
- `/stats 3` → full list of who clicked on post #3 and when.

All posts you want tracked should go through `/post` rather than typed directly into
the channel, since the bot needs to be the one attaching the button.

## Notes / honest limitations

- Invite-link joins are reliable but Telegram has occasionally been reported to drop
  a small percentage of `chat_member` updates under heavy load. If exactness matters,
  cross-check with `getChatMember` periodically.
- If someone joins the channel without using your `/invite` link (e.g. an existing
  member, or a shared public link), they'll still show up in the join notification by
  name/username — they just won't be matched to a tracked friend record.
- Click data is exact and instant; there's no equivalent caveat there.
