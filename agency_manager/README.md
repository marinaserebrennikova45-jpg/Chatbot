# GIRLS | Agency Manager (separate bot)

This directory is separate from the working applicant bot at repository root. Do not change root startup command `python bot.py`.

## Setup
1. Create a **new** Telegram bot via @BotFather; never reuse applicant bot token.
2. On a **separate** HOKAS Python service, configure GitHub repo main, dependencies enabled, startup command `python agency_manager/manager.py`.
3. Install dependencies from `agency_manager/requirements.txt` if host doesn't automatically install nested requirements.
4. Add environment variables:
   - `AGENCY_MANAGER_TOKEN` = new bot token (secret)
   - `AGENCY_OWNER_ID` = your numeric Telegram user ID (get it by messaging new bot /start before setting owner ID; bot needs token and an ID to start, so initially set any nonzero placeholder ID, then update and restart)
   - `AGENCY_MANAGER_DB` = `agency_manager.sqlite3` (optional)
   - `VK_GROUP_TOKEN` = VK community access token with wall posting permissions (optional; keep secret)
5. Start service and send /start to the manager bot.

## Commands
/new <vacancy text> ; /vacancies
/addtg @channel <label> ; /addvk -123456 <label> ; /targets
/post <vacancy_id> <target_id>
/schedule <vacancy_id> <target_id> YYYY-MM-DDTHH:MM (UTC)
/queue ; /cancel <queue_id>

**Only add channels/groups where the bot is an admin and has permission to post.** VK posting requires permission and a valid community token. Never automate posting to third-party groups without authorization.

The queue uses SQLite; persistent disk is recommended. UTC times. Publishing errors are reported, not automatically retried, to avoid duplicate posts. This is an MVP; test with a private channel before public use.

**Security:** never commit .env or tokens to GitHub. The applicant bot's SQLite database and photos are separate. Do not put personal applicant data into vacancy posts.
