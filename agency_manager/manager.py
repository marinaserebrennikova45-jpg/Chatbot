import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("AGENCY_MANAGER_TOKEN", "")
OWNER_ID = int(os.getenv("AGENCY_OWNER_ID", "0"))
DB = os.getenv("AGENCY_MANAGER_DB", "agency_manager.sqlite3")
VK_TOKEN = os.getenv("VK_GROUP_TOKEN", "")
VK_VERSION = "5.199"
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agency_manager")

def connect():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS vacancies (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS targets (id INTEGER PRIMARY KEY, platform TEXT NOT NULL, destination TEXT NOT NULL, label TEXT NOT NULL, UNIQUE(platform,destination))")
    c.execute("CREATE TABLE IF NOT EXISTS queue (id INTEGER PRIMARY KEY, vacancy_id INTEGER, target_id INTEGER, run_at TEXT, status TEXT DEFAULT 'pending', error TEXT)")
    c.commit()
    return c

def allowed(update):
    return OWNER_ID and update.effective_user and update.effective_user.id == OWNER_ID

async def guard(update):
    if not allowed(update):
        await update.effective_message.reply_text("Доступ только для владельца. Твой Telegram ID: " + str(update.effective_user.id))
        return False
    return True

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    await update.message.reply_text("💗 GIRLS | Agency Manager\n/new Текст — создать вакансию\n/vacancies — список\n/addtg @channel Название — Telegram (бот должен быть администратором)\n/addvk -123456 Название — VK (нужен токен сообщества)\n/targets — площадки\n/post ID_вакансии ID_площадки — опубликовать сейчас\n/schedule ID_вакансии ID_площадки YYYY-MM-DDTHH:MM — запланировать по UTC\n/queue — очередь\n/cancel ID — отменить публикацию\nВсе публикации выполняются только по твоей явной команде.")

async def new(update, ctx):
    if not await guard(update): return
    value = update.message.text.partition(" ")[2].strip()
    if not value:
        await update.message.reply_text("Пример: /new 💗 Набор стримеров 18+ ...")
        return
    with connect() as c:
        cur = c.execute("INSERT INTO vacancies(text) VALUES(?)", (value,))
        ident = cur.lastrowid
    await update.message.reply_text(f"Вакансия #{ident} сохранена. Просмотр: /vacancies")

async def vacancies(update, ctx):
    if not await guard(update): return
    with connect() as c: rows=c.execute("SELECT id,text FROM vacancies ORDER BY id DESC LIMIT 20").fetchall()
    await update.message.reply_text("\n\n".join(f"#{i}: {t[:180]}" for i,t in rows) or "Вакансий пока нет.")

async def add_target(update, ctx, platform):
    if not await guard(update): return
    if len(ctx.args)<2:
        await update.message.reply_text("Укажи адрес и название площадки.")
        return
    destination, label=ctx.args[0], " ".join(ctx.args[1:])
    if platform=="vk" and (not destination.startswith("-") or not destination[1:].isdigit()):
        await update.message.reply_text("Для VK нужен отрицательный ID сообщества, например -123456.")
        return
    if platform=="tg" and not (destination.startswith("@") or destination.startswith("-100")):
        await update.message.reply_text("Для Telegram укажи @channel или числовой chat ID.")
        return
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO targets(platform,destination,label) VALUES(?,?,?)",(platform,destination,label))
    await update.message.reply_text("Площадка добавлена. Публикуй только при наличии разрешения администратора.")

async def addtg(update,ctx): await add_target(update,ctx,"tg")
async def addvk(update,ctx): await add_target(update,ctx,"vk")

async def targets(update,ctx):
    if not await guard(update): return
    with connect() as c: rows=c.execute("SELECT id,platform,destination,label FROM targets").fetchall()
    await update.message.reply_text("\n".join(f"#{i} {p}: {label} ({dest})" for i,p,dest,label in rows) or "Площадок пока нет.")

def vk_post(owner, message):
    if not VK_TOKEN: raise RuntimeError("VK_GROUP_TOKEN не настроен")
    data=urlencode({"owner_id":owner,"from_group":1,"message":message,"access_token":VK_TOKEN,"v":VK_VERSION}).encode()
    req=Request("https://api.vk.com/method/wall.post",data=data)
    with urlopen(req,timeout=25) as response:
        import json
        result=json.load(response)
    if "error" in result: raise RuntimeError(str(result["error"]))
    return result.get("response",{})

async def publish(app, vacancy_id, target_id):
    with connect() as c:
        vacancy=c.execute("SELECT text FROM vacancies WHERE id=?",(vacancy_id,)).fetchone()
        target=c.execute("SELECT platform,destination FROM targets WHERE id=?",(target_id,)).fetchone()
    if not vacancy or not target: raise ValueError("Вакансия или площадка не найдена")
    platform,destination=target
    if platform=="tg":
        await app.bot.send_message(chat_id=destination,text=vacancy[0])
    elif platform=="vk":
        await asyncio.to_thread(vk_post,destination,vacancy[0])
    else: raise ValueError("Неизвестная площадка")

async def post(update,ctx):
    if not await guard(update): return
    try:
        vid,tid=map(int,ctx.args[:2])
        await publish(ctx.application,vid,tid)
        await update.message.reply_text("✅ Опубликовано.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось опубликовать: {e}")

async def schedule(update,ctx):
    if not await guard(update): return
    try:
        vid,tid=map(int,ctx.args[:2])
        dt=datetime.fromisoformat(ctx.args[2])
        if dt.replace(tzinfo=timezone.utc)<=datetime.now(timezone.utc): raise ValueError("Укажи будущее время UTC")
        with connect() as c:
            if not c.execute("SELECT 1 FROM vacancies WHERE id=?",(vid,)).fetchone(): raise ValueError("Нет вакансии")
            if not c.execute("SELECT 1 FROM targets WHERE id=?",(tid,)).fetchone(): raise ValueError("Нет площадки")
            cur=c.execute("INSERT INTO queue(vacancy_id,target_id,run_at) VALUES(?,?,?)",(vid,tid,dt.isoformat()))
            ident=cur.lastrowid
        await update.message.reply_text(f"🗓 Публикация #{ident} запланирована на {dt.isoformat()} UTC")
    except Exception as e: await update.message.reply_text(f"Формат: /schedule 1 2 2026-11-01T10:00 (UTC)\nОшибка: {e}")

async def queue(update,ctx):
    if not await guard(update): return
    with connect() as c: rows=c.execute("SELECT id,vacancy_id,target_id,run_at,status,error FROM queue ORDER BY id DESC LIMIT 20").fetchall()
    await update.message.reply_text("\n".join(f"#{i} вак.{v} → площадка {t} | {d} UTC | {s} {e or ''}" for i,v,t,d,s,e in rows) or "Очередь пуста.")

async def cancel(update,ctx):
    if not await guard(update): return
    try:
        ident=int(ctx.args[0])
        with connect() as c: c.execute("UPDATE queue SET status='cancelled' WHERE id=? AND status='pending'",(ident,))
        await update.message.reply_text("Отменено, если публикация ожидала отправки.")
    except Exception: await update.message.reply_text("Формат: /cancel 1")

async def worker(app):
    while True:
        await asyncio.sleep(15)
        now=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="minutes")
        with connect() as c:
            jobs=c.execute("SELECT id,vacancy_id,target_id FROM queue WHERE status='pending' AND run_at<=? ORDER BY id LIMIT 10",(now,)).fetchall()
            for ident,vid,tid in jobs:
                c.execute("UPDATE queue SET status='processing' WHERE id=? AND status='pending'",(ident,))
        for ident,vid,tid in jobs:
            try:
                await publish(app,vid,tid)
                status,error="sent",None
            except Exception as exc:
                status,error="failed",str(exc)[:300]
                log.exception("Publishing failed")
            with connect() as c: c.execute("UPDATE queue SET status=?,error=? WHERE id=?",(status,error,ident))
            try: await app.bot.send_message(OWNER_ID,f"Публикация #{ident}: {status}" + (f" — {error}" if error else ""))
            except Exception: log.exception("Notification failed")

async def on_start(app):
    app.bot_data["worker"]=asyncio.create_task(worker(app))

async def on_stop(app):
    task=app.bot_data.get("worker")
    if task:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass

def main():
    if not TOKEN or not OWNER_ID: raise RuntimeError("Set AGENCY_MANAGER_TOKEN and AGENCY_OWNER_ID")
    Path(DB).parent.mkdir(parents=True,exist_ok=True)
    connect().close()
    app=Application.builder().token(TOKEN).post_init(on_start).post_shutdown(on_stop).build()
    for name,handler in [("start",start),("help",start),("new",new),("vacancies",vacancies),("addtg",addtg),("addvk",addvk),("targets",targets),("post",post),("schedule",schedule),("queue",queue),("cancel",cancel)]:
        app.add_handler(CommandHandler(name,handler))
    app.run_polling(drop_pending_updates=False)

if __name__=="__main__": main()
