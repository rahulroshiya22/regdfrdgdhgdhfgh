import os
import re
import sys
import uuid
import time
import json
import shutil
import logging
import asyncio
import requests
import psutil
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    for p in [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\aria2.aria2_Microsoft.Winget.Source_8wekyb3d8bbwe\aria2-1.37.0-win-64bit-build1"),
    ]:
        if os.path.isdir(p):
            os.environ["PATH"] = p + ";" + os.environ.get("PATH", "")

import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ━━━ CONFIG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = "6546580342:AAEZSnzj9o5W7goZH5TeLBSlRVUIbN_YdYc"
API_ID = 6
API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"
ADMIN_ID = "5904403234"

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
BANNER = Path(__file__).parent / "banner.png"

URL_STORE = {}
CANCEL_FLAGS = {}  # download_id -> True/False
HAS_FFMPEG = shutil.which("ffmpeg") is not None
HAS_ARIA2 = shutil.which("aria2c") is not None

BRAND = "TurboGrab"
VER = "5.0"

# ━━━ SITES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SITES = {
    "instagram":  {"icon": "💜", "name": "Instagram", "domains": [r"instagram\.com", r"instagr\.am"], "cookies": True},
    "facebook":   {"icon": "🔷", "name": "Facebook",  "domains": [r"facebook\.com", r"fb\.watch", r"fb\.com"]},
    "xhamster":   {"icon": "🔶", "name": "xHamster",  "domains": [r"xhamster\d*\.(?:com|desi|one|gold)", r"xhms\.pro"]},
    "pornhub":    {"icon": "🟠", "name": "PornHub",   "domains": [r"pornhub\.com", r"pornhubpremium\.com"]},
    "xvideos":    {"icon": "🔴", "name": "XVideos",   "domains": [r"xvideos\d*\.com", r"xvideos\.es"]},
    "xnxx":       {"icon": "🟡", "name": "XNXX",      "domains": [r"xnxx\d*\.com", r"xnxx\.tv"]},
    "redtube":    {"icon": "🔺", "name": "RedTube",   "domains": [r"redtube\.com"]},
    "youporn":    {"icon": "🩷", "name": "YouPorn",   "domains": [r"youporn\.com"]},
    "spankbang":  {"icon": "🟤", "name": "SpankBang", "domains": [r"spankbang\.com", r"spankbang\.party"]},
    "eporner":    {"icon": "⬛", "name": "Eporner",   "domains": [r"eporner\.com"]},
    "tube8":      {"icon": "🔵", "name": "Tube8",     "domains": [r"tube8\.com"]},
    "txxx":       {"icon": "🟪", "name": "TXXX",      "domains": [r"txxx\.com"]},
    "chaturbate": {"icon": "🎥", "name": "Chaturbate","domains": [r"chaturbate\.com"]},
    "stripchat":  {"icon": "💃", "name": "Stripchat", "domains": [r"stripchat\.com"]},
    "bongacams":  {"icon": "🎪", "name": "BongaCams", "domains": [r"bongacams\.com"]},
    "cam4":       {"icon": "📹", "name": "CAM4",      "domains": [r"cam4\.com"]},
    "camsoda":    {"icon": "🥤", "name": "CamSoda",   "domains": [r"camsoda\.com"]},
    "pornflip":   {"icon": "🔁", "name": "PornFlip",  "domains": [r"pornflip\.com"]},
    "porntube":   {"icon": "📺", "name": "PornTube",  "domains": [r"porntube\.com"]},
    "sunporno":   {"icon": "☀️", "name": "SunPorno",  "domains": [r"sunporno\.com"]},
    "hellporno":  {"icon": "🔥", "name": "HellPorno", "domains": [r"hellporno\.com"]},
    "alphaporno": {"icon": "🅰️", "name": "AlphaPorno","domains": [r"alphaporno\.com"]},
    "zenporn":    {"icon": "🧘", "name": "ZenPorn",   "domains": [r"zenporn\.com"]},
    "pornoxo":    {"icon": "⭕", "name": "PornoXO",   "domains": [r"pornoxo\.com"]},
    "lovehomeporn":{"icon":"🏠", "name": "LoveHomePorn","domains":[r"lovehomeporn\.com"]},
    "nubilesporn":{"icon": "🌸", "name": "NubilesPorn","domains": [r"nubiles-porn\.com"]},
    "manyvids":   {"icon": "🎬", "name": "ManyVids",  "domains": [r"manyvids\.com"]},
    "moviefap":   {"icon": "🎞️", "name": "MovieFap",  "domains": [r"moviefap\.com"]},
    "pornbox":    {"icon": "📦", "name": "PornBox",   "domains": [r"pornbox\.com"]},
    "porntop":    {"icon": "🏆", "name": "PornTop",   "domains": [r"porntop\.com"]},
}

ALL_DOMAINS = []
for s in SITES.values():
    ALL_DOMAINS.extend(s["domains"])
URL_RE = re.compile(rf"https?://(?:[\w-]+\.)*(?:{'|'.join(ALL_DOMAINS)})/\S+")


def detect(url):
    for k, v in SITES.items():
        for d in v["domains"]:
            if re.search(d, url): return k
    return "unknown"


# ━━━ HELPERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def sid_store(url):
    s = uuid.uuid4().hex[:8]
    URL_STORE[s] = url
    return s

def sid_get(s): return URL_STORE.get(s, "")

def dur(s):
    if not s: return "—"
    s = int(s); m, sc = divmod(s, 60); h, m = divmod(m, 60)
    return f"{h}:{m:02}:{sc:02}" if h else f"{m}:{sc:02}"

def sz(b):
    if not b: return "—"
    b = float(b)
    for u in ("B","KB","MB","GB"):
        if b < 1024: return f"{b:.1f}{u}"
        b /= 1024
    return f"{b:.1f}TB"

def pbar(p, w=12):
    f = int(w * p / 100)
    return "█" * f + "░" * (w - f)


def get_formats(info: dict) -> list:
    """Get REAL available formats grouped by resolution with EXACT format IDs."""
    fmts = info.get("formats", [])
    best_audio_id = None
    best_audio_size = 0

    # Find best audio-only stream
    for f in fmts:
        vc = f.get("vcodec", "none")
        ac = f.get("acodec", "none")
        if (vc == "none" or not vc) and ac and ac != "none":
            abr = f.get("abr", 0) or f.get("tbr", 0) or 0
            if abr > best_audio_size:
                best_audio_size = abr
                best_audio_id = f.get("format_id")

    seen = {}
    for f in fmts:
        h = f.get("height")
        vc = f.get("vcodec", "none")
        if not h or h < 100 or vc == "none" or not vc:
            continue

        fid = f.get("format_id", "")
        fsize = f.get("filesize") or f.get("filesize_approx") or 0
        if not fsize:
            tbr = f.get("tbr") or 0
            d = info.get("duration") or 0
            if tbr and d: fsize = int(tbr * 1000 / 8 * d)

        label = f"{h}p"
        ac = f.get("acodec", "none")
        # Keep highest bitrate per resolution
        if label not in seen or fsize > seen[label]["size"]:
            seen[label] = {
                "label": label, "height": h, "size": fsize,
                "fid": fid, "fps": f.get("fps", 0),
                "ext": f.get("ext", ""),
                "has_audio": ac != "none" and ac is not None,
            }

    result = sorted(seen.values(), key=lambda x: x["height"], reverse=True)

    # Attach audio ID for merging only if video has no audio
    for r in result:
        r["audio_id"] = "" if r["has_audio"] else (best_audio_id or "")

    return result[:6]


# ━━━ DOWNLOAD ENGINE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class Tracker:
    def __init__(self, dl_id):
        self.pct = 0; self.speed = "—"; self.eta = "—"
        self.done = 0; self.total = 0; self.finished = False
        self.dl_id = dl_id

    def hook(self, d):
        # Check cancel
        if CANCEL_FLAGS.get(self.dl_id):
            raise Exception("Cancelled by user")
        
        try:
            status = d.get("status")
            if status == "downloading":
                self.done = d.get("downloaded_bytes", 0)
                
                # Check normal bytes first
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                
                # If HLS/fragmented, check fragments
                if not total and d.get("fragment_count"):
                    self.pct = int((d.get("fragment_index", 0) / d.get("fragment_count", 1)) * 100)
                elif total:
                    self.total = total
                    self.pct = int(self.done / self.total * 100)
                
                sp = d.get("speed")
                self.speed = sz(sp) + "/s" if sp else "—"
                e = d.get("eta")
                self.eta = f"{e}s" if e else "—"
                
            elif status == "finished":
                self.finished = True
                self.pct = 100
        except Exception as e:
            pass


def get_info(url):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    site = SITES.get(detect(url), {})
    if site.get("cookies"):
        for br in ["chrome", "edge", "firefox"]:
            try:
                opts["cookiesfrombrowser"] = (br,)
                with yt_dlp.YoutubeDL(opts) as y: return y.extract_info(url, download=False)
            except: continue
        opts.pop("cookiesfrombrowser", None)
    with yt_dlp.YoutubeDL(opts) as y: return y.extract_info(url, download=False)


def do_download(url, video_fid, audio_fid, dl_id, tracker):
    """Download with EXACT format IDs — no fallback to higher quality."""
    site = SITES.get(detect(url), {})
    cookies = site.get("cookies", False)
    has_ff = shutil.which("ffmpeg") is not None
    has_ar = shutil.which("aria2c") is not None

    # Build exact format string
    if video_fid and audio_fid and has_ff:
        fmt = f"{video_fid}+{audio_fid}"
    elif video_fid:
        fmt = video_fid
    else:
        fmt = "best"

    out = str(DOWNLOAD_DIR / f"{dl_id}.%(ext)s")

    opts = {
        "format": fmt,
        "outtmpl": out,
        "quiet": True, "no_warnings": True,
        "restrictfilenames": True, "windowsfilenames": True,
        "concurrent_fragment_downloads": 16,
        "buffersize": 131072, "http_chunk_size": 10485760,
        "socket_timeout": 30, "retries": 10, "fragment_retries": 10,
        "noprogress": True, "progress_hooks": [tracker.hook],
    }

    if has_ff:
        if video_fid == "bestaudio":
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            opts["merge_output_format"] = "mp4"
            opts["postprocessors"] = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]

    if cookies:
        for br in ["chrome", "edge", "firefox"]:
            try:
                opts["cookiesfrombrowser"] = (br,)
                with yt_dlp.YoutubeDL(opts) as y:
                    info = y.extract_info(url, download=True)
                    return y.prepare_filename(info)
            except Exception as e:
                continue
        opts.pop("cookiesfrombrowser", None)

    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=True)
            return y.prepare_filename(info)
    except Exception as e:
        raise e


def find_file(dl_id):
    for ext in (".mp4", ".webm", ".mkv", ".m4a", ".mp4.part"):
        fp = DOWNLOAD_DIR / f"{dl_id}{ext}"
        if fp.exists(): return str(fp)
    files = sorted(DOWNLOAD_DIR.glob(f"{dl_id}*"), key=os.path.getmtime, reverse=True)
    return str(files[0]) if files else None

def cleanup(fp):
    try:
        if fp and os.path.exists(fp): os.remove(fp)
    except: pass

async def auto_delete(*msgs, delay=60):
    await asyncio.sleep(delay)
    for m in msgs:
        try: await m.delete()
        except: pass

def gofile_upload(filepath):
    """Sync function to upload a file to Gofile."""
    try:
        r = requests.get("https://api.gofile.io/servers").json()
        server = r["data"]["servers"][0]["name"]
        with open(filepath, "rb") as f:
            res = requests.post(f"https://{server}.gofile.io/contents/uploadfile", files={"file": f}).json()
        if res.get("status") == "ok":
            return res["data"]["downloadPage"]
        raise Exception("Upload rejected by Gofile")
    except Exception as e:
        raise Exception(f"Gofile error: {e}")


# ━━━ DATA STORE (NO DB) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA_FILE = Path("data.json")

def load_data():
    if not DATA_FILE.exists():
        return {"users": {}, "stats": {"total_dl": 0, "total_users": 0}, "settings": {"maintenance": False, "approval_mode": False}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}, "stats": {"total_dl": 0, "total_users": 0}, "settings": {"maintenance": False, "approval_mode": False}}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)

db = load_data()

def get_user(uid):
    uid_str = str(uid)
    if uid_str not in db["users"]:
        # If approval_mode is False (Auto Accept), they are approved. Otherwise they wait. Admin gets auto-approved.
        is_appr = not db["settings"].get("approval_mode", False) or is_admin(uid)
        db["users"][uid_str] = {
            "lang": "en", 
            "auto_delete": 60, 
            "banned": False, 
            "approved": is_appr,
            "joined": str(datetime.now())
        }
        db["stats"]["total_users"] = len(db["users"])
        save_data(db)
        
        # Notify Admin of new request if manual approval
        if db["settings"].get("approval_mode", False) and not is_admin(uid):
            try:
                txt = f"🆕 <b>New User Request</b>\n\nID: <code>{uid}</code>\nWant to use the bot."
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve", callback_data=f"adm|app|{uid}"),
                     InlineKeyboardButton("❌ Decline", callback_data=f"adm|dec|{uid}")]
                ])
                asyncio.create_task(bot.send_message(int(ADMIN_ID), txt, parse_mode=ParseMode.HTML, reply_markup=kb))
            except: pass
            
    return db["users"][uid_str]

def is_admin(uid):
    return str(uid) == str(ADMIN_ID)


# ━━━ MIDDLEWARE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_user(_, __, query):
    if not query.from_user: return False
    uid = query.from_user.id
    u = get_user(uid)
    
    if u.get("banned"):
        try:
            if isinstance(query, Message): await query.reply_text("❌ You are banned from using this bot.")
            elif isinstance(query, CallbackQuery): await query.answer("❌ You are banned.", show_alert=True)
        except: pass
        return False
        
    if not u.get("approved", True) and not is_admin(uid):
        try:
            txt = "🔒 <b>Access Denied</b>\nThis is a private bot. Your account is pending admin approval."
            if isinstance(query, Message): await query.reply_text(txt, parse_mode=ParseMode.HTML)
            elif isinstance(query, CallbackQuery): await query.answer("Pending Admin Approval.", show_alert=True)
        except: pass
        return False
        
    if db["settings"].get("maintenance") and not is_admin(uid):
        try:
            txt = "🛠 <b>Bot is under maintenance.</b>\nWe are upgrading the servers. Please try again in a few minutes!"
            if isinstance(query, Message): await query.reply_text(txt, parse_mode=ParseMode.HTML)
            elif isinstance(query, CallbackQuery): await query.answer("🛠 Maintenance Mode Active. Try again later.", show_alert=True)
        except: pass
        return False
        
    return True

user_filter = filters.create(check_user)


# ━━━ BOT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bot = Client("turbograb_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH,
             workdir=str(DOWNLOAD_DIR), max_concurrent_transmissions=8)


# ━━━ ADMIN COMMANDS & STATE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ADMIN_STATE = {}

@bot.on_message(filters.command("admin") & user_filter)
async def cmd_admin(_, msg: Message):
    if not is_admin(msg.from_user.id): return
    t, kb = get_admin_main()
    await msg.reply_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)

@bot.on_message(user_filter, group=-1)
async def admin_state_handler(client, msg: Message):
    uid = str(msg.from_user.id)
    if not is_admin(uid) or uid not in ADMIN_STATE:
        return
        
    if msg.text and msg.text.startswith("/"):
        del ADMIN_STATE[uid] # Cancel on any new command
        return
        
    state = ADMIN_STATE[uid]
    
    if msg.text and msg.text.lower() == "cancel":
        del ADMIN_STATE[uid]
        await msg.reply_text("❌ Action cancelled.")
        msg.stop_propagation()
        
    if state == "ban":
        if not msg.text: return
        target = msg.text.strip()
        if target not in db["users"]:
            await msg.reply_text("❌ User ID not found in database. Type 'cancel' to abort.")
            msg.stop_propagation()
        
        is_banned = db["users"][target].get("banned", False)
        db["users"][target]["banned"] = not is_banned
        save_data(db)
        
        status = "BANNED �" if not is_banned else "UNBANNED ✅"
        await msg.reply_text(f"User <code>{target}</code> is now {status}.", parse_mode=ParseMode.HTML)
        del ADMIN_STATE[uid]
        msg.stop_propagation()
        
    elif state == "broadcast":
        del ADMIN_STATE[uid]
        users = list(db["users"].keys())
        await msg.reply_text(f"🚀 Broadcasting message to {len(users)} users...")
        success, failed = 0, 0
        for u in users:
            try:
                await msg.copy(int(u))
                success += 1
                await asyncio.sleep(0.05)
            except:
                failed += 1
        await msg.reply_text(f"✅ <b>Broadcast Complete</b>\n\n📨 Delivered: {success}\n❌ Failed: {failed}", parse_mode=ParseMode.HTML)
        msg.stop_propagation()


def get_admin_main():
    total_u = db["stats"]["total_users"]
    total_dl = db["stats"]["total_dl"]
    appr_mode = "🔴 Manual" if db["settings"].get("approval_mode", False) else "🟢 Auto-Accept"
    maint = "🔴 ON" if db["settings"]["maintenance"] else "🟢 OFF"
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    t = (
        f"👑 <b>High-Level Admin Dashboard</b>\n\n"
        f"📊 <b>Platform Stats</b>\n"
        f"├ 👥 Users: <code>{total_u}</code>\n"
        f"└ ⬇️ Total Downloads: <code>{total_dl}</code>\n\n"
        f"🖥 <b>Server Resources</b>\n"
        f"├ ⚙️ CPU: <code>{cpu}%</code>\n"
        f"├ 🧩 RAM: <code>{ram}%</code>\n"
        f"└ 💾 Disk: <code>{disk}%</code>\n\n"
        f"🛡 <b>Access Security</b>\n"
        f"├ 🚪 Approval: <b>{appr_mode}</b>\n"
        f"└ 🛠 Maint Mode: <b>{maint}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡 Security & Users", callback_data="adm|nav|users"),
         InlineKeyboardButton("🛠 Bot Settings", callback_data="adm|nav|settings")],
        [InlineKeyboardButton("📢 Send Broadcast", callback_data="adm|state|broadcast")],
        [InlineKeyboardButton("🔙 Exit Panel", callback_data="nav|start")]
    ])
    return t, kb

def get_admin_users():
    pending = sum(1 for u in db["users"].values() if not u.get("approved", True))
    banned = sum(1 for u in db["users"].values() if u.get("banned", False))
    appr_mode = "Manual Approval" if db["settings"].get("approval_mode", False) else "Auto Accept"
    mode_cb = "adm|toggle|appr"
    
    t = (
        f"🛡 <b>User Access & Security</b>\n\n"
        f"⏳ <b>Pending Approvals:</b> <code>{pending}</code>\n"
        f"🚫 <b>Banned Users:</b> <code>{banned}</code>\n\n"
        f"<i>Gatekeeper Mode:</i> <b>{appr_mode}</b>\n"
        f"(When set to Manual, new users must be approved by you before they can use the bot)."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Toggle Approval Mode", callback_data=mode_cb)],
        [InlineKeyboardButton("✅ Approve All", callback_data="adm|appall"),
         InlineKeyboardButton("🔨 Ban/Unban", callback_data="adm|state|ban")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb
    
def get_admin_settings():
    m_cb = "adm|toggle|maint"
    t = (
        f"⚙️ <b>Advanced Bot Settings</b>\n\n"
        f"<b>Maintenance Mode</b> blocks all users except the Admin. "
        f"<b>Clear Cache</b> wipes the internal downloads folder to instantly recover disk space."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Toggle Maintenance", callback_data=m_cb)],
        [InlineKeyboardButton("🧹 Wipe Downloads Cache", callback_data="adm|clearcache")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb


# ━━━ USER COMMANDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_start_menu():
    t = (
        f"<b>⚡ {BRAND}</b> <code>v{VER}</code>\n"
        f"<i>Ultra-Fast Video Downloader</i>\n\n"
        f"<blockquote expandable>"
        f"<b>🌐 30+ Supported Sites</b>\n\n"
        f"💜 Instagram   🔷 Facebook\n"
        f"🔶 xHamster    🟠 PornHub\n"
        f"🔴 XVideos       🟡 XNXX\n"
        f"🔺 RedTube      🩷 YouPorn\n"
        f"🟤 SpankBang   ⬛ Eporner\n"
        f"🎥 Chaturbate   💃 Stripchat\n"
        f"🔵 Tube8   🟪 TXXX   📹 CAM4\n"
        f"<i>+ many more...</i>"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"📤 Up to <b>2GB</b> direct upload\n"
        f"🎯 <b>Exact quality</b> — you pick, we deliver\n"
        f"🚀 <b>aria2 + 16x parallel</b> max speed\n"
        f"📊 Live progress · ❌ Cancel anytime\n"
        f"⏳ Auto-cleanup after 60s"
        f"</blockquote>\n\n"
        f"📎 <b>Paste any video link to start</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="nav|settings"),
         InlineKeyboardButton("🌐 Sites", callback_data="nav|sites")],
        [InlineKeyboardButton("📖 Help", callback_data="nav|help")]
    ])
    return t, kb

def get_settings_menu(uid):
    u = get_user(uid)
    del_time = u.get("auto_delete", 60)
    del_icons = {10: "▫️", 60: "▫️", 0: "▫️"}
    del_icons[del_time] = "✅"
    
    t = (
        f"⚙️ <b>Your Settings</b>\n\n"
        f"👤 <b>ID:</b> <code>{uid}</code>\n"
        f"📅 <b>Joined:</b> <code>{u['joined'].split()[0]}</code>\n\n"
        f"🗑 <b>Auto-Delete Messages:</b>\n"
        f"<i>Keep your chat clean by automatically deleting bot messages after a download.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{del_icons[10]} 10 Sec", callback_data="set|del|10"),
         InlineKeyboardButton(f"{del_icons[60]} 60 Sec", callback_data="set|del|60")],
        [InlineKeyboardButton(f"{del_icons[0]} Disable", callback_data="set|del|0")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]
    ])
    return t, kb

def get_help_menu():
    t = (
        f"<b>📖 How to Use {BRAND}</b>\n\n"
        f"<blockquote>"
        f"1. Send any video URL\n"
        f"2. See available qualities with <b>real sizes</b>\n"
        f"3. Tap to download — or ❌ cancel\n"
        f"4. Video arrives directly in chat!"
        f"</blockquote>\n\n"
        f"<b>⚡ Speed:</b> aria2 + 16 connections\n"
        f"<b>📤 Limit:</b> 2GB per file\n"
        f"<b>⏳ Cleanup:</b> messages auto-delete in 60s"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]])
    return t, kb

def get_sites_menu():
    t = (
        f"<b>🌐 Supported Sites</b>\n\n"
        f"<blockquote><b>📱 Social</b>\n💜 Instagram · 🔷 Facebook</blockquote>\n\n"
        f"<blockquote><b>🔞 Adult</b>\nxHamster · PornHub · XVideos · XNXX\n"
        f"RedTube · YouPorn · SpankBang · Eporner\nTube8 · TXXX</blockquote>\n\n"
        f"<blockquote><b>🎥 Cams</b>\nChaturbate · Stripchat · BongaCams · CAM4</blockquote>\n\n"
        f"<blockquote><b>📂 More</b>\nPornFlip · PornTube · SunPorno · HellPorno\n"
        f"ManyVids · MovieFap · 10+ more</blockquote>\n\n"
        f"🌍 <i>All mirror domains auto-detected</i>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]])
    return t, kb


# ━━━ USER COMMANDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("start") & user_filter)
async def cmd_start(_, msg: Message):
    t, kb = get_start_menu()
    if BANNER.exists():
        await msg.reply_photo(str(BANNER), caption=t, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await msg.reply_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)


@bot.on_message(filters.command("settings") & user_filter)
async def cmd_settings(_, msg: Message):
    t, kb = get_settings_menu(str(msg.from_user.id))
    await msg.reply_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)

@bot.on_message(filters.command("help") & user_filter)
async def cmd_help(_, msg: Message):
    t, kb = get_help_menu()
    await msg.reply_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)


@bot.on_callback_query(user_filter)
async def on_cb(_, cb: CallbackQuery):
    d = cb.data

    # ── Navigation Callbacks ──
    if d.startswith("nav|"):
        page = d.split("|")[1]
        try:
            if page == "start":
                t, kb = get_start_menu()
            elif page == "help":
                t, kb = get_help_menu()
            elif page == "sites":
                t, kb = get_sites_menu()
            elif page == "settings":
                t, kb = get_settings_menu(str(cb.from_user.id))
            
            # Use edit_message_caption if it has a photo
            if cb.message.photo:
                await cb.message.edit_caption(caption=t, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await cb.message.edit_text(text=t, parse_mode=ParseMode.HTML, reply_markup=kb)
        except Exception as e:
            pass # Message not modified error
        return

    # ── Cancel ──
    if d.startswith("cancel|"):
        parts = d.split("|")
        if len(parts) > 1:
            dl_id = parts[1]
            CANCEL_FLAGS[dl_id] = True
        await cb.answer("❌ Cancelling...")
        try:
            await cb.message.edit_text("❌ <b>Action cancelled.</b>", parse_mode=ParseMode.HTML)
        except: pass
        return

    # ── Settings Callbacks ──
    if d.startswith("set|"):
        _, opt, val = d.split("|")
        uid = str(cb.from_user.id)
        if opt == "del":
            db["users"][uid]["auto_delete"] = int(val)
            save_data(db)
            await cb.answer("✅ Setting saved!", show_alert=False)
            
            # Re-render keyboard
            t, kb = get_settings_menu(uid)
            try: 
                if cb.message.photo:
                    await cb.message.edit_caption(caption=t, parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await cb.message.edit_text(text=t, parse_mode=ParseMode.HTML, reply_markup=kb)
            except: pass
        return

    # ── Admin Flow & Toggles ──
    if d.startswith("adm|"):
        if not is_admin(cb.from_user.id): return await cb.answer("You are not admin.", show_alert=True)
        parts = d.split("|")
        act = parts[1]
        
        # Navigation
        try:
            if act == "nav":
                page = parts[2]
                if page == "main": t, kb = get_admin_main()
                elif page == "users": t, kb = get_admin_users()
                elif page == "settings": t, kb = get_admin_settings()
                await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
        except: pass
        
        # Action Approvals (Inline Buttons from New User Request)
        if act == "app":
            tgt = parts[2]
            if tgt in db["users"]:
                db["users"][tgt]["approved"] = True
                save_data(db)
                await cb.answer(f"Approvals granted to {tgt}.")
                try: await cb.message.edit_text(f"✅ User {tgt} is approved.")
                except: pass
                # Notify User
                try: await bot.send_message(int(tgt), "🎉 <b>Your account has been approved!</b>\nSend /start to begin downloading.", parse_mode=ParseMode.HTML)
                except: pass
            return
            
        elif act == "dec":
            tgt = parts[2]
            if tgt in db["users"]:
                db["users"][tgt]["banned"] = True # Decline means Ban conceptually
                save_data(db)
                await cb.answer(f"Declined & Banned {tgt}.")
                try: await cb.message.edit_text(f"❌ User {tgt} request declined.")
                except: pass
            return
            
        elif act == "appall":
            count = 0
            for uid, details in db["users"].items():
                if not details.get("approved", True) and not details.get("banned", False):
                    details["approved"] = True
                    count += 1
            if count > 0:
                save_data(db)
                await cb.answer(f"Approved {count} pending users!", show_alert=True)
                t, kb = get_admin_users()
                try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
                except: pass
            else:
                await cb.answer("No pending users found.")
        
        # Toggles
        elif act == "toggle":
            opt = parts[2]
            if opt == "maint":
                db["settings"]["maintenance"] = not db["settings"]["maintenance"]
                save_data(db)
                await cb.answer("Maintenance Toggled.")
                t, kb = get_admin_settings()
                try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
                except: pass
            elif opt == "appr":
                db["settings"]["approval_mode"] = not db["settings"].get("approval_mode", False)
                save_data(db)
                await cb.answer("Approval Mode Toggled.")
                t, kb = get_admin_users()
                try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
                except: pass
                
        # State Flow Triggers (Broadcast / Ban)
        elif act == "state":
            opt = parts[2]
            uid = str(cb.from_user.id)
            if opt == "broadcast":
                ADMIN_STATE[uid] = "broadcast"
                await cb.message.reply_text("📣 <b>Broadcast Mode Active</b>\n\nSend me the message, picture, or video you want to broadcast right now.\n\nType <code>cancel</code> to abort.", parse_mode=ParseMode.HTML)
                await cb.answer()
            elif opt == "ban":
                ADMIN_STATE[uid] = "ban"
                await cb.message.reply_text("🔨 <b>Ban/Unban Mode Active</b>\n\nSend me the exact <b>User ID</b> you want to ban or unban.\n\nType <code>cancel</code> to abort.", parse_mode=ParseMode.HTML)
                await cb.answer()
                
        # Other Tools
        elif act == "clearcache":
            await cb.answer("Sweeping cache...")
            count = 0
            for fp in DOWNLOAD_DIR.glob("*"):
                try: fp.unlink(); count += 1
                except: pass
            await cb.answer(f"Deleted {count} files.", show_alert=True)
        elif act == "help":
            await cb.answer("Reply to any media/text with /broadcast to send to all users.", show_alert=True)
        return

    # ── Ask Delivery Mode ──
    if d.startswith("ask|"):
        parts = d.split("|")
        uid = parts[1]
        vid = parts[2]
        aud = parts[3] if len(parts) > 3 else ""
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Send to Telegram", callback_data=f"tg|{uid}|{vid}|{aud}")],
            [InlineKeyboardButton("🔗 Direct Link (Fast)", callback_data=f"gf|{uid}|{vid}|{aud}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|")]
        ])
        await cb.message.edit_text(
            f"<b>🚚 Select Delivery Method</b>\n\n"
            f"<blockquote>"
            f"<b>📤 Telegram:</b> Directly into chat (up to 2GB)\n"
            f"<b>🔗 Direct Link:</b> High-speed cloud link (No limits)"
            f"</blockquote>",
            parse_mode=ParseMode.HTML, reply_markup=kb
        )
        return

    # ── Download: mode|urlid|video_fid|audio_fid ──
    if not (d.startswith("tg|") or d.startswith("gf|")):
        return

    await cb.answer("⚡ Starting...")
    parts = d.split("|")
    mode = parts[0]
    url_id = parts[1]
    video_fid = parts[2] if len(parts) > 2 else "best"
    audio_fid = parts[3] if len(parts) > 3 else None
    url = sid_get(url_id)

    if not url:
        await cb.message.reply_text("⚠️ <b>Link expired.</b> Send URL again.", parse_mode=ParseMode.HTML)
        return

    plat = detect(url)
    pi = SITES.get(plat, {"icon": "🎬", "name": "Video"})
    dl_id = uuid.uuid4().hex[:10]
    CANCEL_FLAGS[dl_id] = False

    cancel_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{dl_id}")]])

    status = await cb.message.reply_text(
        f"<b>⬇️ Downloading</b>\n\n"
        f"<code>{pbar(0)} 0%</code>\n\n"
        f"<blockquote>📡 Speed: starting...\n⏱ ETA: —</blockquote>",
        parse_mode=ParseMode.HTML, reply_markup=cancel_kb,
    )

    t0 = time.time()
    tracker = Tracker(dl_id)
    loop = asyncio.get_event_loop()
    task = loop.run_in_executor(None, do_download, url, video_fid, audio_fid, dl_id, tracker)

    # Live progress (download)
    prev = ""
    last_edit = 0
    spinners = ["◐", "◓", "◑", "◒"]
    spin_idx = 0
    
    # Auto-pin
    try: await status.pin(disable_notification=True)
    except: pass
    
    while not task.done():
        await asyncio.sleep(1)
        if CANCEL_FLAGS.get(dl_id): 
            break
            
        now = time.time()
        # Only update if download has started and 3 seconds have passed
        if tracker.total > 0 and (now - last_edit) > 3:
            p = min(tracker.pct, 99)
            if p > 0:
                spin = spinners[spin_idx % len(spinners)]
                spin_idx += 1
                txt = (
                    f"<b>{spin} Downloading</b>\n\n"
                    f"<code>{pbar(p)} {p}%</code>\n\n"
                    f"<blockquote>"
                    f"📡 Speed   <b>{tracker.speed}</b>\n"
                    f"⏱  ETA       <b>{tracker.eta}</b>\n"
                    f"📦 {sz(tracker.done)} / {sz(tracker.total)}"
                    f"</blockquote>"
                )
                if txt != prev:
                    try:
                        await status.edit_text(txt, parse_mode=ParseMode.HTML, reply_markup=cancel_kb)
                        prev = txt
                        last_edit = now
                    except Exception:
                        pass

    try:
        filepath = await task
    except Exception as e:
        err = str(e)
        if "Cancelled" in err:
            return
        await status.edit_text(
            f"<b>❌ Failed</b>\n\n<blockquote><code>{err[:200]}</code></blockquote>",
            parse_mode=ParseMode.HTML)
        return

    filepath = find_file(dl_id)
    
    # Unpin after download finishes
    try: await status.unpin()
    except: pass
    
    if not filepath:
        await status.edit_text("❌ <b>File not found.</b>", parse_mode=ParseMode.HTML)
        return

    fsize = os.path.getsize(filepath)
    dl_time = time.time() - t0
    dl_spd = sz(fsize / dl_time) + "/s" if dl_time > 0 else "—"

    if fsize > 2 * 1024**3:
        await status.edit_text(
            f"⚠️ File <b>{sz(fsize)}</b> exceeds 2GB limit.",
            parse_mode=ParseMode.HTML)
        cleanup(filepath); return

    if mode == "gf":
        # ━━ Gofile Upload ━━
        await status.edit_text(
            f"<b>🔗 Uploading to Gofile...</b>\n\n"
            f"<code>{pbar(50)} 50%</code>\n\n"
            f"<blockquote>📁 Size: <b>{sz(fsize)}</b></blockquote>",
            parse_mode=ParseMode.HTML)
            
        try:
            loop = asyncio.get_event_loop()
            link = await loop.run_in_executor(None, gofile_upload, filepath)
            
            await status.edit_text(
                f"<b>✅ Ready for Download</b>\n\n"
                f"<blockquote>"
                f"{pi['icon']} Platform   <b>{pi['name']}</b>\n"
                f"📁 Size        <b>{sz(fsize)}</b>\n"
                f"⬇️ Speed     <b>{dl_spd}</b>\n"
                f"</blockquote>\n\n"
                f"👇 <b>Your secure link:</b>\n"
                f"{link}\n\n"
                f"<i>⚡ Powered by {BRAND} v{VER}</i>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Gofile Upload: {e}")
            await status.edit_text(f"❌ <b>Upload failed</b>\n<code>{str(e)[:150]}</code>", parse_mode=ParseMode.HTML)
        finally:
            cleanup(filepath)
            CANCEL_FLAGS.pop(dl_id, None)
        return

    # ━━ Telegram Upload phase ━━
    up_t0 = time.time()
    last_up_edit = 0

    async def up_prog(cur, tot):
        nonlocal prev, last_up_edit
        p = int(cur / tot * 100) if tot else 0
        now = time.time()
        if (now - last_up_edit) < 4: return
        last_up_edit = now
        spd = sz(cur / (now - up_t0)) + "/s" if (now - up_t0) > 1 else "—"
        t = (f"<b>📤 Uploading</b>\n\n"
             f"<code>{pbar(p)} {p}%</code>\n\n"
             f"<blockquote>📡 {spd} · 📦 {sz(cur)}/{sz(tot)}</blockquote>")
        if t != prev:
            try: await status.edit_text(t, parse_mode=ParseMode.HTML); prev = t
            except: pass

    await status.edit_text(
        f"<b>📤 Uploading</b>  <code>{sz(fsize)}</code>\n\n"
        f"<code>{pbar(0)} 0%</code>",
        parse_mode=ParseMode.HTML)

    try:
        video_msg = await cb.message.reply_video(
            video=filepath,
            caption=(
                f"<b>✅ {pi['name']} Video</b>\n\n"
                f"<blockquote>"
                f"📁 <b>{sz(fsize)}</b> · ⬇️ <b>{dl_spd}</b> · ⏱ <b>{dl_time:.0f}s</b>"
                f"</blockquote>\n\n"
                f"<i>⚡ {BRAND} v{VER}</i>"
            ),
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
            progress=up_prog,
        )

        delay = db["users"][str(cb.from_user.id)].get("auto_delete", 60)
        
        if delay > 0:
            await status.edit_text(
                f"✅ <b>Done!</b> {sz(fsize)} in {time.time()-t0:.0f}s\n"
                f"⏳ <i>Auto-deleting in {delay}s</i>",
                parse_mode=ParseMode.HTML)
            asyncio.create_task(auto_delete(status, video_msg, delay=delay))
        else:
            await status.edit_text(
                f"✅ <b>Done!</b> {sz(fsize)} in {time.time()-t0:.0f}s",
                parse_mode=ParseMode.HTML)

    except Exception as e:
        logger.error(f"Upload: {e}")
        await status.edit_text(f"❌ <b>Upload failed</b>\n<code>{str(e)[:150]}</code>", parse_mode=ParseMode.HTML)
    finally:
        cleanup(filepath)
        CANCEL_FLAGS.pop(dl_id, None)


# ━━━ URL HANDLER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.text & filters.regex(r"^(?!/)") & user_filter)
async def on_url(_, msg: Message):
    text = msg.text.strip()
    
    # Try to delete user's message to keep chat clean
    try: await msg.delete()
    except: pass
    
    match = URL_RE.search(text)
    if not match:
        if text.startswith("http"):
            await msg.reply_text("⚠️ <b>Unsupported URL.</b> Try /start", parse_mode=ParseMode.HTML)
        return

    url = match.group(0)
    plat = detect(url)
    pi = SITES.get(plat, {"icon": "🎬", "name": "Video"})

    status = await msg.reply_text(
        f"{pi['icon']} <b>Analyzing...</b>", parse_mode=ParseMode.HTML)

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, get_info, url)

        title = info.get("title", "Unknown")
        if len(title) > 45: title = title[:42] + "..."
        d = dur(info.get("duration", 0))
        who = info.get("uploader", "") or info.get("channel", "") or "—"
        views = info.get("view_count", 0)
        vstr = f"{views:,}" if views else "—"
        thumb = info.get("thumbnail", "")

        formats = get_formats(info)
        uid = sid_store(url)

        # Build buttons with EXACT format IDs and real sizes
        if formats:
            btns = []
            for f in formats:
                s = sz(f["size"]) if f["size"] else "?"
                fps = f" {f['fps']}fps" if f["fps"] and f["fps"] > 30 else ""
                label = f"📹 {f['label']}{fps}  ·  {s}"
                # Store exact video format ID + audio ID in callback
                aid = f["audio_id"] or ""
                btns.append([InlineKeyboardButton(label, callback_data=f"ask|{uid}|{f['fid']}|{aid}")])
            btns.append([
                InlineKeyboardButton("🎵 Audio Only", callback_data=f"ask|{uid}|bestaudio|"),
                InlineKeyboardButton("⚡ Best Auto", callback_data=f"ask|{uid}|best|")
            ])
        else:
            btns = [
                [InlineKeyboardButton("🎵 Audio Only", callback_data=f"ask|{uid}|bestaudio|")],
                [InlineKeyboardButton("⚡ Download Best", callback_data=f"ask|{uid}|best|")]
            ]

        kb = InlineKeyboardMarkup(btns)

        # Quality list
        q_txt = ""
        for i, f in enumerate(formats):
            s = sz(f["size"]) if f["size"] else "?"
            fps = f" {f['fps']}fps" if f["fps"] and f["fps"] > 30 else ""
            dot = "🔹" if i == 0 else "▫️"
            q_txt += f"  {dot} <b>{f['label']}</b>{fps} — <code>{s}</code>\n"
        if not q_txt:
            q_txt = "  <i>Auto quality</i>\n"

        caption = (
            f"{pi['icon']} <b>{pi['name']} — Video Found</b>\n\n"
            f"<blockquote>"
            f"🎬 <b>{title}</b>\n\n"
            f"⏱ {d}  ·  👤 {who}  ·  👁 {vstr}"
            f"</blockquote>\n\n"
            f"<b>🎯 Available Qualities:</b>\n"
            f"{q_txt}\n"
            f"👇 <b>Tap to download exact quality:</b>"
        )

        await status.delete()

        if thumb:
            await msg.reply_photo(thumb, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await msg.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=kb)

    except Exception as e:
        logger.error(f"Info: {e}")
        await status.edit_text(
            f"❌ <b>Failed</b>\n<blockquote><code>{str(e)[:200]}</code></blockquote>",
            parse_mode=ParseMode.HTML)


if __name__ == "__main__":
    print(f"[*] {BRAND} v{VER}")
    print(f"[*] Sites: {len(SITES)} | ffmpeg: {'Y' if HAS_FFMPEG else 'N'} | aria2: {'Y' if HAS_ARIA2 else 'N'}")
    print(f"[OK] Running...")
    bot.run()
