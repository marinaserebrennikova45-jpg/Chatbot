# GIRLS | Stream Agency — Hilly recruitment bot

Bilingual Russian/English application bot for @streamingagency_bot. It asks for consent, checks stated age 18+, collects applicant details and 2–3 regular photographs, then forwards applications to manager @girls_mngr.

## Run
1. Install Python 3.10+ and run `pip install -r requirements.txt`.
2. Copy `.env.example` to `.env`. Set BOT_TOKEN from @BotFather privately and a long random MANAGER_CLAIM_CODE (24+ characters). Never commit .env.
3. Run `python bot.py` on a computer/server that remains on.
4. From the actual @girls_mngr Telegram account, open @streamingagency_bot and send `/claim YOUR_SECRET` **in a private chat**. Delete that message afterwards. This connects manager delivery.
5. Test with a separate adult Telegram account: /start, choose language, Apply, consent, complete questions, send 2–3 photos, tap Done. Verify manager receives text and photos.

Commands: /start, /menu, /cancel, /delete_me, /claim.
Only manager chat ID is stored in SQLite. Incomplete applicant details stay in process memory. Submitted photos are copied to the manager's Telegram chat; deletion of those messages requires contacting the manager. No intimate images or identity documents. Self-declared age and photo ownership cannot be verified automatically. Not an official Hilly integration; verify current platform policies and country eligibility. No income guarantees.

GitHub alone does not run the bot 24/7. Use a persistent worker on a hosting service, add BOT_TOKEN and MANAGER_CLAIM_CODE as secret environment variables, and start with `python bot.py`. Keep persistent storage if you want manager binding to survive redeployments.
