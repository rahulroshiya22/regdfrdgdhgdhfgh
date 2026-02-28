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
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ━━━ CONFIG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = os.getenv("BOT_TOKEN", "8394241962:AAEno24N1Fn7UxMyIuLcmQxn_hdSWdcgR7I")
API_ID = int(os.getenv("API_ID", 6))
API_HASH = os.getenv("API_HASH", "eb06d4abfb49dc3eeb1aeb98ae0f581e")
ADMIN_ID = os.getenv("ADMIN_ID", "5904403234")

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
BANNER = Path(__file__).parent / "banner.png"

URL_STORE = {}
INFO_STORE = {}  # url_id -> {title, thumb, uploader, duration}
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


# Sites accessible to ALL users (free)
FREE_SITES = {"xhamster", "instagram", "facebook"}

def detect(url):
    for k, v in SITES.items():
        for d in v["domains"]:
            if re.search(d, url): return k
    return "unknown"

def is_free_site(platform: str) -> bool:
    """Returns True if this platform is free for all users."""
    return platform in FREE_SITES

def check_vip_access(uid, platform: str) -> bool:
    """Returns True if user can access this platform (free site OR VIP user OR admin)."""
    if is_free_site(platform): return True
    if is_admin(uid): return True
    u = db.get("users", {}).get(str(uid), {})
    return u.get("vip", False)


# ━━━ HELPERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def sid_store(url, info=None):
    s = uuid.uuid4().hex[:8]
    URL_STORE[s] = url
    if info:
        INFO_STORE[s] = {
            "title": info.get("title", "Unknown"),
            "thumb": info.get("thumbnail", ""),
            "uploader": info.get("uploader", "") or info.get("channel", "") or "",
            "duration": info.get("duration", 0),
        }
    return s

def sid_get(s): return URL_STORE.get(s, "")
def sid_info(s): return INFO_STORE.get(s, {})

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

DEFAULT_SETTINGS = {
    "maintenance": False,
    "approval_mode": False,
    "force_channel": False,
    "force_channel_id": "",
    "force_channel_link": "",
    "force_channel_name": "Our Channel",
    "welcome_msg": "",
    "dl_limit": 0,
    "max_file_size_mb": 2048,
    "auto_delete_default": 60,
    "bot_name": "TurboGrab",
    "bot_version": "5.0",
    "watermark": "",
    "log_channel": "",
    "vip_mode": False,
    "caption_template": "",
    "restrict_forwards": False,
    "allow_audio": True,
    "allow_gofile": True,
    "custom_thumb": "",
    "notify_admin_dl": False,
    "dump_channels": [],
    "allowed_groups": [],
}

def load_data():
    if not DATA_FILE.exists():
        return {"users": {}, "stats": {"total_dl": 0, "total_users": 0}, "settings": dict(DEFAULT_SETTINGS)}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            # Merge any missing keys from defaults
            for k, v in DEFAULT_SETTINGS.items():
                d["settings"].setdefault(k, v)
            return d
    except:
        return {"users": {}, "stats": {"total_dl": 0, "total_users": 0}, "settings": dict(DEFAULT_SETTINGS)}

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


# ━━━ MIDDLEWARE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def check_force_channel(client, uid) -> bool:
    """Returns True if user is in the force channel (or FC disabled)."""
    if not db["settings"].get("force_channel"): return True
    cid = db["settings"].get("force_channel_id", "").strip()
    if not cid: return True
    try:
        member = await client.get_chat_member(cid, uid)
        from pyrogram.enums import ChatMemberStatus
        return member.status in (
            ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER, ChatMemberStatus.RESTRICTED
        )
    except:
        return False

async def check_user(_, client_or_dummy, query):
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

async def enforce_force_channel(client, msg_or_cb):
    """Check force channel and send join prompt. Returns True if OK."""
    if not db["settings"].get("force_channel"): return True
    if not msg_or_cb.from_user: return True
    uid = msg_or_cb.from_user.id
    if is_admin(uid): return True
    joined = await check_force_channel(client, uid)
    if joined: return True
    cname = db["settings"].get("force_channel_name", "Our Channel")
    clink = db["settings"].get("force_channel_link", "")
    txt = (
        f"<b>📢 𝗝𝗼𝗶𝗻 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱!</b>\n\n"
        f"<blockquote>"
        f"🔒 You must join <b>{cname}</b>\n"
        f"before you can use this bot.\n\n"
        f"👇 Tap the button below to join,\n"
        f"then press ✅ to verify."
        f"</blockquote>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>🛠 𝗕𝗼𝘁 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
    )
    btns = []
    if clink: btns.append([InlineKeyboardButton(f"➕ Join {cname}", url=clink)])
    btns.append([InlineKeyboardButton("✅ I Joined — Verify Me", callback_data="fc|check")])
    kb = InlineKeyboardMarkup(btns)
    try:
        if isinstance(msg_or_cb, Message):
            if BANNER.exists():
                await msg_or_cb.reply_photo(str(BANNER), caption=txt, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await msg_or_cb.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
        elif isinstance(msg_or_cb, CallbackQuery):
            await msg_or_cb.message.reply_text(txt, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
    except: pass
    return False


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
        del ADMIN_STATE[uid]
        return
        
    state = ADMIN_STATE[uid]
    
    if msg.text and msg.text.lower() == "cancel":
        del ADMIN_STATE[uid]
        await msg.reply_text("❌ Action cancelled.")
        msg.stop_propagation()
        return
        
    if state == "ban":
        if not msg.text: return
        target = msg.text.strip()
        if target not in db["users"]:
            await msg.reply_text("❌ User ID not found. Type 'cancel' to abort.")
            msg.stop_propagation(); return
        is_banned = db["users"][target].get("banned", False)
        db["users"][target]["banned"] = not is_banned
        save_data(db)
        status = "BANNED 🚫" if not is_banned else "UNBANNED ✅"
        await msg.reply_text(f"User <code>{target}</code> is now {status}.", parse_mode=ParseMode.HTML)
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "broadcast":
        del ADMIN_STATE[uid]
        users = list(db["users"].keys())
        await msg.reply_text(f"🚀 Broadcasting to {len(users)} users...")
        success, failed = 0, 0
        for u in users:
            try:
                await msg.copy(int(u)); success += 1
                await asyncio.sleep(0.05)
            except: failed += 1
        await msg.reply_text(f"✅ <b>Broadcast Done</b>\n📨 {success} sent · ❌ {failed} failed", parse_mode=ParseMode.HTML)
        msg.stop_propagation()

    elif state == "setchanid":
        if not msg.text: return
        db["settings"]["force_channel_id"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Force channel ID set!")
        msg.stop_propagation()

    elif state == "setchanlink":
        if not msg.text: return
        db["settings"]["force_channel_link"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Force channel link set!")
        msg.stop_propagation()

    elif state == "setchanname":
        if not msg.text: return
        db["settings"]["force_channel_name"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Channel name set!")
        msg.stop_propagation()

    elif state == "setbotname":
        if not msg.text: return
        db["settings"]["bot_name"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Bot name updated!")
        msg.stop_propagation()

    elif state == "setver":
        if not msg.text: return
        db["settings"]["bot_version"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Version updated!")
        msg.stop_propagation()

    elif state == "setwm":
        if not msg.text: return
        db["settings"]["watermark"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Watermark set!")
        msg.stop_propagation()

    elif state == "setcap":
        if not msg.text: return
        db["settings"]["caption_template"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Caption set! Use {title}, {platform}, {size}, {brand} as placeholders.")
        msg.stop_propagation()

    elif state == "setwelcome":
        if not msg.text: return
        db["settings"]["welcome_msg"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Welcome message set!")
        msg.stop_propagation()

    elif state == "setlogch":
        if not msg.text: return
        db["settings"]["log_channel"] = msg.text.strip()
        save_data(db); del ADMIN_STATE[uid]
        await msg.reply_text("✅ Log channel set!")
        msg.stop_propagation()

    elif state == "setdllimit":
        if not msg.text: return
        try:
            val = int(msg.text.strip())
            db["settings"]["dl_limit"] = val
            save_data(db); del ADMIN_STATE[uid]
            await msg.reply_text(f"✅ DL limit set to {'∞' if not val else val}/user.")
        except: await msg.reply_text("❌ Send a valid number (0 = unlimited).")
        msg.stop_propagation()

    elif state == "setmaxfile":
        if not msg.text: return
        try:
            val = int(msg.text.strip())
            db["settings"]["max_file_size_mb"] = val
            save_data(db); del ADMIN_STATE[uid]
            await msg.reply_text(f"✅ Max file size set to {val} MB.")
        except: await msg.reply_text("❌ Send a valid number in MB.")
        msg.stop_propagation()

    elif state == "addvip":
        if not msg.text: return
        target = msg.text.strip()
        if target in db["users"]:
            db["users"][target]["vip"] = True
            db["users"][target]["approved"] = True
            save_data(db)
            await msg.reply_text(f"✅ <code>{target}</code> is now VIP 👑!", parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text("❌ User not found.")
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "msguser":
        parts = msg.text.strip().split("\n", 1) if msg.text else []
        if len(parts) < 2:
            await msg.reply_text("❌ Format:\n<code>USER_ID\nYour message</code>", parse_mode=ParseMode.HTML)
            msg.stop_propagation(); return
        target_uid, text = parts[0].strip(), parts[1].strip()
        try:
            await bot.send_message(int(target_uid), text)
            await msg.reply_text(f"✅ Message sent to {target_uid}.")
        except Exception as e:
            await msg.reply_text(f"❌ Failed: {e}")
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "listusers":
        del ADMIN_STATE[uid]
        lines = []
        for u_id, u_data in list(db["users"].items()):
            s = "🚫" if u_data.get("banned") else ("⏳" if not u_data.get("approved", True) else "✅")
            v = "👑" if u_data.get("vip") else ""
            lines.append(f"{s}{v} <code>{u_id}</code>")
        txt = "👥 <b>All Users:</b>\n\n" + "\n".join(lines[:50])
        if len(lines) > 50: txt += f"\n<i>...and {len(lines)-50} more</i>"
        await msg.reply_text(txt, parse_mode=ParseMode.HTML)
        msg.stop_propagation()

    elif state == "deluser":
        if not msg.text: return
        target = msg.text.strip()
        if target in db["users"]:
            del db["users"][target]
            db["stats"]["total_users"] = len(db["users"])
            save_data(db)
            await msg.reply_text(f"🗑 User <code>{target}</code> deleted.", parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text("❌ User not found.")
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "adddump":
        if not msg.text: return
        ch = msg.text.strip()
        dumps = db["settings"].get("dump_channels", [])
        if ch not in dumps:
            dumps.append(ch)
            db["settings"]["dump_channels"] = dumps
            save_data(db)
            await msg.reply_text(f"✅ Dump channel <code>{ch}</code> added!", parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text("⚠️ Channel already in dump list.")
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "remdump":
        if not msg.text: return
        ch = msg.text.strip()
        dumps = db["settings"].get("dump_channels", [])
        if ch in dumps:
            dumps.remove(ch)
            db["settings"]["dump_channels"] = dumps
            save_data(db)
            await msg.reply_text(f"✅ Dump channel <code>{ch}</code> removed.", parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text("❌ Channel not found in dump list.")
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "addgroup":
        if not msg.text: return
        gid = msg.text.strip()
        groups = db["settings"].get("allowed_groups", [])
        if gid not in groups:
            groups.append(gid)
            db["settings"]["allowed_groups"] = groups
            save_data(db)
            await msg.reply_text(f"✅ Group <code>{gid}</code> added to allowed list!", parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text("⚠️ Group already in list.")
        del ADMIN_STATE[uid]; msg.stop_propagation()

    elif state == "remgroup":
        if not msg.text: return
        gid = msg.text.strip()
        groups = db["settings"].get("allowed_groups", [])
        if gid in groups:
            groups.remove(gid)
            db["settings"]["allowed_groups"] = groups
            save_data(db)
            await msg.reply_text(f"✅ Group <code>{gid}</code> removed.", parse_mode=ParseMode.HTML)
        else:
            await msg.reply_text("❌ Group not found in list.")
        del ADMIN_STATE[uid]; msg.stop_propagation()


def get_admin_main():
    total_u = db["stats"]["total_users"]
    total_dl = db["stats"]["total_dl"]
    appr_mode = "🔴 Manual" if db["settings"].get("approval_mode", False) else "🟢 Auto"
    maint = "🔴 ON" if db["settings"]["maintenance"] else "🟢 OFF"
    fc = "🟢 ON" if db["settings"].get("force_channel") else "🔴 OFF"
    vip = "🟢 ON" if db["settings"].get("vip_mode") else "🔴 OFF"
    
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    t = (
        f"👑 <b>TurboGrab Admin Dashboard</b>\n\n"
        f"📊 <b>Platform Stats</b>\n"
        f"├ 👥 Users: <code>{total_u}</code>\n"
        f"└ ⬇️ Downloads: <code>{total_dl}</code>\n\n"
        f"🖥 <b>Server</b>\n"
        f"├ ⚙️ CPU: <code>{cpu}%</code>\n"
        f"├ 🧩 RAM: <code>{ram}%</code>\n"
        f"└ 💾 Disk: <code>{disk}%</code>\n\n"
        f"⚡ <b>Quick Status</b>\n"
        f"├ 🚪 Approval: <b>{appr_mode}</b>\n"
        f"├ 🛠 Maintenance: <b>{maint}</b>\n"
        f"├ 📢 Force Join: <b>{fc}</b>\n"
        f"└ 👑 VIP Mode: <b>{vip}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Users & Access", callback_data="adm|nav|users"),
         InlineKeyboardButton("⚙️ Bot Config", callback_data="adm|nav|settings")],
        [InlineKeyboardButton("📢 Force Channel", callback_data="adm|nav|forcechan"),
         InlineKeyboardButton("📣 Broadcast", callback_data="adm|state|broadcast")],
        [InlineKeyboardButton("📁 Files & Cache", callback_data="adm|nav|files"),
         InlineKeyboardButton("📊 Stats & Logs", callback_data="adm|nav|stats")],
        [InlineKeyboardButton("🎨 Bot Appearance", callback_data="adm|nav|appearance"),
         InlineKeyboardButton("🔗 Integrations", callback_data="adm|nav|integrations")],
        [InlineKeyboardButton("🛡 Security", callback_data="adm|nav|security"),
         InlineKeyboardButton("🔔 Notifications", callback_data="adm|nav|notify")],
        [InlineKeyboardButton("� Dump Channels", callback_data="adm|nav|dump"),
         InlineKeyboardButton("👥 Group Mgmt", callback_data="adm|nav|groups")],
        [InlineKeyboardButton("�🔙 Exit Panel", callback_data="nav|start")]
    ])
    return t, kb

def get_admin_dump():
    dumps = db["settings"].get("dump_channels", [])
    dump_list = "\n".join([f"  📦 <code>{ch}</code>" for ch in dumps]) if dumps else "  <i>None configured</i>"
    t = (
        f"📦 <b>𝗗𝘂𝗺𝗽 𝗖𝗵𝗮𝗻𝗻𝗲𝗹𝘀</b>\n\n"
        f"<blockquote>"
        f"Downloaded videos will be automatically\n"
        f"forwarded to these channels for storage."
        f"</blockquote>\n\n"
        f"<b>Active Channels ({len(dumps)}):</b>\n"
        f"{dump_list}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Dump Channel", callback_data="adm|state|adddump"),
         InlineKeyboardButton("➖ Remove Channel", callback_data="adm|state|remdump")],
        [InlineKeyboardButton("🗑 Clear All Dumps", callback_data="adm|cleardumps")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_groups():
    groups = db["settings"].get("allowed_groups", [])
    grp_list = "\n".join([f"  👥 <code>{g}</code>" for g in groups]) if groups else "  <i>None — bot works in all groups</i>"
    t = (
        f"👥 <b>𝗚𝗿𝗼𝘂𝗽 𝗠𝗮𝗻𝗮𝗴𝗲𝗺𝗲𝗻𝘁</b>\n\n"
        f"<blockquote>"
        f"Anyone can add the bot to groups, but only\n"
        f"admin-approved groups will be active.\n\n"
        f"If no groups are listed, bot works everywhere."
        f"</blockquote>\n\n"
        f"<b>Allowed Groups ({len(groups)}):</b>\n"
        f"{grp_list}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Group", callback_data="adm|state|addgroup"),
         InlineKeyboardButton("➖ Remove Group", callback_data="adm|state|remgroup")],
        [InlineKeyboardButton("🗑 Clear All Groups", callback_data="adm|cleargroups")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_users():
    pending = sum(1 for u in db["users"].values() if not u.get("approved", True))
    banned = sum(1 for u in db["users"].values() if u.get("banned", False))
    total = len(db["users"])
    appr_mode = "Manual Approval" if db["settings"].get("approval_mode", False) else "Auto Accept"
    t = (
        f"👥 <b>User Management</b>\n\n"
        f"👤 Total: <code>{total}</code>\n"
        f"⏳ Pending: <code>{pending}</code>\n"
        f"🚫 Banned: <code>{banned}</code>\n\n"
        f"<i>Mode:</i> <b>{appr_mode}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Toggle Approval Mode", callback_data="adm|toggle|appr")],
        [InlineKeyboardButton("✅ Approve All Pending", callback_data="adm|appall"),
         InlineKeyboardButton("🔨 Ban/Unban User", callback_data="adm|state|ban")],
        [InlineKeyboardButton("📋 List All Users", callback_data="adm|state|listusers"),
         InlineKeyboardButton("🗑 Delete User", callback_data="adm|state|deluser")],
        [InlineKeyboardButton("📩 Message User", callback_data="adm|state|msguser"),
         InlineKeyboardButton("👑 Add VIP", callback_data="adm|state|addvip")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_settings():
    maint = "🔴 ON" if db["settings"]["maintenance"] else "🟢 OFF"
    audio = "🟢 ON" if db["settings"].get("allow_audio", True) else "🔴 OFF"
    gofile = "🟢 ON" if db["settings"].get("allow_gofile", True) else "🔴 OFF"
    restrict = "🟢 ON" if db["settings"].get("restrict_forwards") else "🔴 OFF"
    nadl = "🟢 ON" if db["settings"].get("notify_admin_dl") else "🔴 OFF"
    max_mb = db["settings"].get("max_file_size_mb", 2048)
    dl_lim = db["settings"].get("dl_limit", 0)
    t = (
        f"⚙️ <b>Bot Configuration</b>\n\n"
        f"🛠 Maintenance: <b>{maint}</b>\n"
        f"🎵 Audio DL: <b>{audio}</b>\n"
        f"🔗 Gofile: <b>{gofile}</b>\n"
        f"🚫 Restrict Fwd: <b>{restrict}</b>\n"
        f"🔔 Admin DL Notify: <b>{nadl}</b>\n"
        f"📦 Max File: <b>{max_mb} MB</b>\n"
        f"⬇️ DL Limit/user: <b>{'∞' if not dl_lim else dl_lim}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛠 Toggle Maintenance", callback_data="adm|toggle|maint"),
         InlineKeyboardButton("🎵 Toggle Audio DL", callback_data="adm|toggle|audio")],
        [InlineKeyboardButton("🔗 Toggle Gofile", callback_data="adm|toggle|gofile"),
         InlineKeyboardButton("🚫 Toggle Fwd Restrict", callback_data="adm|toggle|restrict")],
        [InlineKeyboardButton("🔔 Toggle Admin Notify", callback_data="adm|toggle|nadl"),
         InlineKeyboardButton("⬇️ Set DL Limit", callback_data="adm|state|setdllimit")],
        [InlineKeyboardButton("📦 Set Max File Size", callback_data="adm|state|setmaxfile"),
         InlineKeyboardButton("🔁 Reset All Settings", callback_data="adm|resetsettings")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_forcechan():
    fc = db["settings"].get("force_channel", False)
    cid = db["settings"].get("force_channel_id", "") or "<i>Not set</i>"
    clink = db["settings"].get("force_channel_link", "") or "<i>Not set</i>"
    cname = db["settings"].get("force_channel_name", "Our Channel")
    status = "🟢 ENABLED" if fc else "🔴 DISABLED"
    t = (
        f"📢 <b>Force Channel Join</b>\n\n"
        f"Status: <b>{status}</b>\n"
        f"Channel ID: <code>{cid}</code>\n"
        f"Channel Link: {clink}\n"
        f"Channel Name: <b>{cname}</b>\n\n"
        f"<i>Users must join your channel before using the bot.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Enable Force Join" if not fc else "❌ Disable Force Join",
                              callback_data="adm|toggle|forcechan")],
        [InlineKeyboardButton("🆔 Set Channel ID", callback_data="adm|state|setchanid"),
         InlineKeyboardButton("🔗 Set Channel Link", callback_data="adm|state|setchanlink")],
        [InlineKeyboardButton("📝 Set Channel Name", callback_data="adm|state|setchanname"),
         InlineKeyboardButton("✅ Verify Setup", callback_data="adm|verifyfc")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_files():
    count = sum(1 for _ in DOWNLOAD_DIR.glob("*"))
    used = sum(f.stat().st_size for f in DOWNLOAD_DIR.glob("*") if f.is_file())
    t = (
        f"📁 <b>Files & Cache</b>\n\n"
        f"📂 Files in cache: <code>{count}</code>\n"
        f"💾 Cache size: <code>{sz(used)}</code>\n\n"
        f"<i>Wipe cache to recover disk space.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧹 Wipe All Cache", callback_data="adm|clearcache"),
         InlineKeyboardButton("♻️ Refresh Stats", callback_data="adm|nav|files")],
        [InlineKeyboardButton("📤 Set Custom Thumbnail", callback_data="adm|state|setthumb"),
         InlineKeyboardButton("🗑 Clear Custom Thumb", callback_data="adm|clearthumb")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_stats():
    total_u = db["stats"]["total_users"]
    total_dl = db["stats"]["total_dl"]
    banned = sum(1 for u in db["users"].values() if u.get("banned", False))
    pending = sum(1 for u in db["users"].values() if not u.get("approved", True))
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    t = (
        f"📊 <b>Stats & System Info</b>\n\n"
        f"👥 Total Users: <code>{total_u}</code>\n"
        f"⬇️ Total Downloads: <code>{total_dl}</code>\n"
        f"🚫 Banned: <code>{banned}</code>\n"
        f"⏳ Pending: <code>{pending}</code>\n\n"
        f"🖥 <b>System</b>\n"
        f"CPU: <code>{cpu}%</code>\n"
        f"RAM: <code>{ram.used // 1024**2}MB / {ram.total // 1024**2}MB ({ram.percent}%)</code>\n"
        f"Disk: <code>{disk.used // 1024**3}GB / {disk.total // 1024**3}GB ({disk.percent}%)</code>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="adm|nav|stats"),
         InlineKeyboardButton("🗑 Reset DL Counter", callback_data="adm|resetdlcount")],
        [InlineKeyboardButton("📤 Export User List", callback_data="adm|exportusers")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_appearance():
    name = db["settings"].get("bot_name", BRAND)
    ver = db["settings"].get("bot_version", VER)
    wm = db["settings"].get("watermark", "") or "<i>None</i>"
    cap = db["settings"].get("caption_template", "") or "<i>Default</i>"
    t = (
        f"🎨 <b>Bot Appearance</b>\n\n"
        f"🤖 Bot Name: <b>{name}</b>\n"
        f"🔢 Version: <b>{ver}</b>\n"
        f"💧 Watermark: {wm}\n"
        f"📝 Caption: {cap}\n\n"
        f"<i>Customize how the bot presents itself to users.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Set Bot Name", callback_data="adm|state|setbotname"),
         InlineKeyboardButton("🔢 Set Version", callback_data="adm|state|setver")],
        [InlineKeyboardButton("💧 Set Watermark", callback_data="adm|state|setwm"),
         InlineKeyboardButton("🗑 Clear Watermark", callback_data="adm|clearwm")],
        [InlineKeyboardButton("📝 Set Caption Template", callback_data="adm|state|setcap"),
         InlineKeyboardButton("🗑 Clear Caption", callback_data="adm|clearcap")],
        [InlineKeyboardButton("💬 Set Welcome Msg", callback_data="adm|state|setwelcome"),
         InlineKeyboardButton("🗑 Clear Welcome", callback_data="adm|clearwelcome")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_integrations():
    log_ch = db["settings"].get("log_channel", "") or "<i>Not set</i>"
    t = (
        f"🔗 <b>Integrations</b>\n\n"
        f"📋 Log Channel: <code>{log_ch}</code>\n\n"
        f"<i>Set a Telegram channel/group where bot activity is logged.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Set Log Channel", callback_data="adm|state|setlogch"),
         InlineKeyboardButton("🗑 Clear Log Channel", callback_data="adm|clearlogch")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_security():
    appr = "Manual" if db["settings"].get("approval_mode") else "Auto"
    vip = "🟢 ON" if db["settings"].get("vip_mode") else "🔴 OFF"
    t = (
        f"🛡 <b>Security Settings</b>\n\n"
        f"🚪 Registration: <b>{appr}</b>\n"
        f"👑 VIP-Only Mode: <b>{vip}</b>\n\n"
        f"<i>VIP mode restricts bot to approved VIP users only.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Toggle Approval Mode", callback_data="adm|toggle|appr"),
         InlineKeyboardButton("👑 Toggle VIP Mode", callback_data="adm|toggle|vip")],
        [InlineKeyboardButton("🔨 Ban User", callback_data="adm|state|ban"),
         InlineKeyboardButton("✅ Unban User", callback_data="adm|state|ban")],
        [InlineKeyboardButton("🧹 Ban All Pending", callback_data="adm|banpending"),
         InlineKeyboardButton("✅ Unban All", callback_data="adm|unbanall")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb

def get_admin_notify():
    nadl = "🟢 ON" if db["settings"].get("notify_admin_dl") else "🔴 OFF"
    t = (
        f"🔔 <b>Notification Settings</b>\n\n"
        f"📥 Notify Admin on Download: <b>{nadl}</b>\n\n"
        f"<i>Get notified every time a user downloads a file.</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Toggle Download Notify", callback_data="adm|toggle|nadl")],
        [InlineKeyboardButton("📣 Send Broadcast", callback_data="adm|state|broadcast")],
        [InlineKeyboardButton("📩 Message Specific User", callback_data="adm|state|msguser")],
        [InlineKeyboardButton("🔙 Back to Dash", callback_data="adm|nav|main")]
    ])
    return t, kb


# ━━━ USER COMMANDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_start_menu():
    t = (
        f"<b>⚡ {BRAND}</b>  <code>v{VER}</code>\n"
        f"<i>━━━ 𝗨𝗹𝘁𝗿𝗮-𝗙𝗮𝘀𝘁 𝗩𝗶𝗱𝗲𝗼 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗲𝗿 ━━━</i>\n\n"
        f"<blockquote>"
        f"📤 Up to <b>2GB</b> direct upload to Telegram\n"
        f"🎯 <b>Exact quality</b> — you pick, we deliver\n"
        f"� <b>aria2 + 16x parallel</b> max speed\n"
        f"� Live progress · ❌ Cancel anytime\n"
        f"� Direct download links available"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"🌐 <b>30+ Supported Platforms</b>\n"
        f"� Instagram  🔷 Facebook  🔶 xHamster\n"
        f"🟠 PornHub  � XVideos  🟡 XNXX\n"
        f"<i>+ 25 more sites...</i>"
        f"</blockquote>\n\n"
        f"📎 <b>𝗣𝗮𝘀𝘁𝗲 𝗮𝗻𝘆 𝘃𝗶𝗱𝗲𝗼 𝗹𝗶𝗻𝗸 𝘁𝗼 𝘀𝘁𝗮𝗿𝘁 ↓</b>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>🛠 𝗕𝗼𝘁 𝗺𝗮𝗱𝗲 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ Settings", callback_data="nav|settings"),
         InlineKeyboardButton("🌐 Supported Sites", callback_data="nav|sites")],
        [InlineKeyboardButton("📖 How to Use", callback_data="nav|help"),
         InlineKeyboardButton("ℹ️ About Bot", callback_data="nav|about")],
    ])
    return t, kb

def get_settings_menu(uid):
    u = get_user(uid)
    del_time = u.get("auto_delete", 60)
    del_icons = {10: "▫️", 60: "▫️", 0: "▫️"}
    del_icons[del_time] = "✅"
    
    t = (
        f"⚙️ <b>𝗬𝗼𝘂𝗿 𝗦𝗲𝘁𝘁𝗶𝗻𝗴𝘀</b>\n\n"
        f"<blockquote>"
        f"👤 <b>User ID:</b> <code>{uid}</code>\n"
        f"📅 <b>Joined:</b> <code>{u['joined'].split()[0]}</code>"
        f"</blockquote>\n\n"
        f"🗑 <b>𝗔𝘂𝘁𝗼-𝗗𝗲𝗹𝗲𝘁𝗲 𝗠𝗲𝘀𝘀𝗮𝗴𝗲𝘀:</b>\n"
        f"<i>Keep your chat clean — messages auto-delete after download.</i>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>🛠 𝗕𝗼𝘁 𝗺𝗮𝗱𝗲 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{del_icons[10]} 10 Sec", callback_data="set|del|10"),
         InlineKeyboardButton(f"{del_icons[60]} 60 Sec", callback_data="set|del|60")],
        [InlineKeyboardButton(f"{del_icons[0]} Disable Auto-Delete", callback_data="set|del|0")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]
    ])
    return t, kb

def get_help_menu():
    t = (
        f"<b>📖 𝗛𝗼𝘄 𝘁𝗼 𝗨𝘀𝗲 {BRAND}</b>\n\n"
        f"<blockquote>"
        f"𝟭. Send or paste any video URL\n"
        f"𝟮. Bot fetches video info with thumbnail\n"
        f"𝟯. Choose your quality from available list\n"
        f"𝟰. Pick delivery — Telegram or Direct Link\n"
        f"𝟱. Video arrives directly in chat!"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"⚡ <b>Speed:</b> aria2 + 16 parallel streams\n"
        f"📤 <b>Limit:</b> 2GB per file\n"
        f"🎯 <b>Quality:</b> You choose exact resolution\n"
        f"⏳ <b>Auto-Clean:</b> Messages delete after download"
        f"</blockquote>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>🛠 𝗕𝗼𝘁 𝗺𝗮𝗱𝗲 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]])
    return t, kb

def get_sites_menu():
    t = (
        f"<b>🌐 𝗔𝗹𝗹 𝗦𝘂𝗽𝗽𝗼𝗿𝘁𝗲𝗱 𝗦𝗶𝘁𝗲𝘀</b>\n\n"
        f"<blockquote><b>📱 Social Media</b>\n"
        f"💜 Instagram · 🔷 Facebook</blockquote>\n\n"
        f"<blockquote><b>� Tube Sites</b>\n"
        f"🔶 xHamster · 🟠 PornHub · 🔴 XVideos\n"
        f"🟡 XNXX · 🔺 RedTube · 🩷 YouPorn\n"
        f"🟤 SpankBang · ⬛ Eporner · 🔵 Tube8\n"
        f"🟪 TXXX · 🔁 PornFlip · 📺 PornTube</blockquote>\n\n"
        f"<blockquote><b>🎥 Live Cam Sites</b>\n"
        f"🎥 Chaturbate · 💃 Stripchat · 🎪 BongaCams\n"
        f"📹 CAM4 · 🥤 CamSoda</blockquote>\n\n"
        f"<blockquote><b>📂 More Platforms</b>\n"
        f"☀️ SunPorno · 🔥 HellPorno · 🅰️ AlphaPorno\n"
        f"🧘 ZenPorn · ⭕ PornoXO · 🏠 LoveHomePorn\n"
        f"🌸 NubilesPorn · 🎬 ManyVids · 🎞️ MovieFap\n"
        f"📦 PornBox · 🏆 PornTop</blockquote>\n\n"
        f"🌍 <i>All mirror domains are auto-detected!</i>\n"
        f"<i>Total: <b>{len(SITES)}</b> platforms supported</i>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>🛠 𝗕𝗼𝘁 𝗺𝗮𝗱𝗲 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]])
    return t, kb

def get_about_menu():
    t = (
        f"<b>ℹ️ 𝗔𝗯𝗼𝘂𝘁 {BRAND}</b>\n\n"
        f"<blockquote>"
        f"<b>{BRAND}</b> is an ultra-fast multi-platform video\n"
        f"downloader bot for Telegram.\n\n"
        f"🔹 <b>Version:</b> <code>v{VER}</code>\n"
        f"🔹 <b>Platforms:</b> <code>{len(SITES)}+</code>\n"
        f"🔹 <b>Max Upload:</b> <code>2 GB</code>\n"
        f"🔹 <b>Engine:</b> <code>yt-dlp + aria2</code>\n"
        f"🔹 <b>Speed:</b> <code>16x parallel</code>"
        f"</blockquote>\n\n"
        f"<blockquote>"
        f"<b>🔧 Core Features:</b>\n"
        f"• Multi-quality selection with real sizes\n"
        f"• Thumbnail & title from original video\n"
        f"• Live download + upload progress bars\n"
        f"• Direct link delivery via Gofile\n"
        f"• Group support with admin control\n"
        f"• Force channel join system\n"
        f"• Full admin dashboard"
        f"</blockquote>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>👨‍💻 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗱 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>\n"
        f"<b>⚡ 𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗯𝘆</b> <code>IronMaxPro Labs</code>"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]])
    return t, kb


# ━━━ USER COMMANDS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.command("start") & user_filter)
async def cmd_start(client, msg: Message):
    try:
        if not await enforce_force_channel(client, msg): return
        t, kb = get_start_menu()
        if BANNER.exists():
            await msg.reply_photo(str(BANNER), caption=t, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
        else:
            await msg.reply_text(t, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"cmd_start: {e}")
        await send_error_to_admin("cmd_start", e)


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
            elif page == "about":
                t, kb = get_about_menu()
            else:
                t, kb = get_start_menu()
            
            if cb.message.photo:
                await cb.message.edit_caption(caption=t, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await cb.message.edit_text(text=t, parse_mode=ParseMode.HTML, reply_markup=kb, disable_web_page_preview=True)
        except Exception as e:
            pass
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
                elif page == "forcechan": t, kb = get_admin_forcechan()
                elif page == "files": t, kb = get_admin_files()
                elif page == "stats": t, kb = get_admin_stats()
                elif page == "appearance": t, kb = get_admin_appearance()
                elif page == "integrations": t, kb = get_admin_integrations()
                elif page == "security": t, kb = get_admin_security()
                elif page == "notify": t, kb = get_admin_notify()
                elif page == "dump": t, kb = get_admin_dump()
                elif page == "groups": t, kb = get_admin_groups()
                else: t, kb = get_admin_main()
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
            toggle_map = {
                "maint": ("maintenance", get_admin_settings),
                "appr": ("approval_mode", get_admin_users),
                "forcechan": ("force_channel", get_admin_forcechan),
                "audio": ("allow_audio", get_admin_settings),
                "gofile": ("allow_gofile", get_admin_settings),
                "restrict": ("restrict_forwards", get_admin_settings),
                "nadl": ("notify_admin_dl", get_admin_notify),
                "vip": ("vip_mode", get_admin_security),
            }
            if opt in toggle_map:
                key, menu_fn = toggle_map[opt]
                db["settings"][key] = not db["settings"].get(key, False)
                save_data(db)
                await cb.answer(f"{key.replace('_',' ').title()} toggled.")
                t, kb = menu_fn()
                try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
                except: pass

        # State Flow Triggers
        elif act == "state":
            opt = parts[2]
            uid = str(cb.from_user.id)
            state_prompts = {
                "broadcast": "📣 <b>Broadcast Mode</b>\nSend any message/photo/video to broadcast.\nType <code>cancel</code> to abort.",
                "ban": "🔨 <b>Ban/Unban</b>\nSend exact <b>User ID</b> to toggle ban.\nType <code>cancel</code> to abort.",
                "setchanid": "🆔 Send the channel/group ID (e.g. <code>-1001234567890</code> or <code>@username</code>).\nType <code>cancel</code> to abort.",
                "setchanlink": "🔗 Send the invite/public link (e.g. <code>https://t.me/yourchannel</code>).\nType <code>cancel</code> to abort.",
                "setchanname": "� Send the display name for the channel.\nType <code>cancel</code> to abort.",
                "setbotname": "🤖 Send the new bot name.\nType <code>cancel</code> to abort.",
                "setver": "🔢 Send the version string (e.g. <code>5.1</code>).\nType <code>cancel</code> to abort.",
                "setwm": "💧 Send the watermark text.\nType <code>cancel</code> to abort.",
                "setcap": "📝 Send the caption template. Use {title}, {platform}, {size}, {brand}.\nType <code>cancel</code> to abort.",
                "setwelcome": "💬 Send the welcome message for new users.\nType <code>cancel</code> to abort.",
                "setlogch": "📋 Send the log channel ID or @username.\nType <code>cancel</code> to abort.",
                "setdllimit": "⬇️ Send the max downloads per user (0 = unlimited).\nType <code>cancel</code> to abort.",
                "setmaxfile": "📦 Send the max file size in MB (default 2048).\nType <code>cancel</code> to abort.",
                "addvip": "👑 Send the User ID to grant VIP access.\nType <code>cancel</code> to abort.",
                "msguser": "📩 Send User ID on first line, message on second line.\nType <code>cancel</code> to abort.",
                "listusers": "📋 Fetching user list...",
                "deluser": "🗑 Send the User ID to delete from database.\nType <code>cancel</code> to abort.",
                "adddump": "📦 Send the dump channel ID (e.g. <code>-1001234567890</code>).\nType <code>cancel</code> to abort.",
                "remdump": "➖ Send the dump channel ID to remove.\nType <code>cancel</code> to abort.",
                "addgroup": "👥 Send the group ID to allow (e.g. <code>-1001234567890</code>).\nType <code>cancel</code> to abort.",
                "remgroup": "➖ Send the group ID to remove from allowed list.\nType <code>cancel</code> to abort.",
            }
            if opt in state_prompts:
                ADMIN_STATE[uid] = opt
                await cb.message.reply_text(state_prompts[opt], parse_mode=ParseMode.HTML)
                await cb.answer()

        # Other Actions
        elif act == "clearcache":
            count = 0
            for fp in DOWNLOAD_DIR.glob("*"):
                try: fp.unlink(); count += 1
                except: pass
            await cb.answer(f"🧹 Deleted {count} files.", show_alert=True)
        elif act == "clearthumb":
            db["settings"]["custom_thumb"] = ""
            save_data(db)
            await cb.answer("✅ Custom thumbnail cleared.")
        elif act == "clearwm":
            db["settings"]["watermark"] = ""
            save_data(db)
            await cb.answer("✅ Watermark cleared.")
        elif act == "clearcap":
            db["settings"]["caption_template"] = ""
            save_data(db)
            await cb.answer("✅ Caption template cleared.")
        elif act == "clearwelcome":
            db["settings"]["welcome_msg"] = ""
            save_data(db)
            await cb.answer("✅ Welcome message cleared.")
        elif act == "clearlogch":
            db["settings"]["log_channel"] = ""
            save_data(db)
            await cb.answer("✅ Log channel cleared.")
        elif act == "resetdlcount":
            db["stats"]["total_dl"] = 0
            save_data(db)
            await cb.answer("✅ Download counter reset.", show_alert=True)
        elif act == "resetsettings":
            db["settings"] = dict(DEFAULT_SETTINGS)
            save_data(db)
            await cb.answer("✅ All settings reset to defaults!", show_alert=True)
            t, kb = get_admin_main()
            try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
            except: pass
        elif act == "exportusers":
            lines = []
            for u_id, u_data in db["users"].items():
                st = "BAN" if u_data.get("banned") else ("PEND" if not u_data.get("approved", True) else "OK")
                v = "VIP" if u_data.get("vip") else ""
                lines.append(f"{u_id} [{st}]{' ['+v+']' if v else ''} joined:{u_data.get('joined','?')[:10]}")
            txt = "\n".join(lines) or "No users."
            await cb.message.reply_document(
                document=bytes(txt, "utf-8"),
                file_name="users_export.txt",
                caption=f"👥 {len(lines)} users exported."
            )
            await cb.answer()
        elif act == "banpending":
            count = 0
            for u_data in db["users"].values():
                if not u_data.get("approved", True) and not u_data.get("banned"):
                    u_data["banned"] = True; count += 1
            save_data(db)
            await cb.answer(f"🚫 Banned {count} pending users.", show_alert=True)
        elif act == "unbanall":
            count = sum(1 for u_data in db["users"].values() if u_data.get("banned"))
            for u_data in db["users"].values(): u_data["banned"] = False
            save_data(db)
            await cb.answer(f"✅ Unbanned {count} users.", show_alert=True)
        elif act == "verifyfc":
            cid = db["settings"].get("force_channel_id", "").strip()
            if not cid:
                await cb.answer("❌ Channel ID not set!", show_alert=True); return
            try:
                chat = await bot.get_chat(cid)
                await cb.answer(f"✅ Channel found: {chat.title}", show_alert=True)
            except Exception as e:
                await cb.answer(f"❌ Error: {str(e)[:100]}", show_alert=True)
        elif act == "cleardumps":
            db["settings"]["dump_channels"] = []
            save_data(db)
            await cb.answer("✅ All dump channels cleared.", show_alert=True)
            t, kb = get_admin_dump()
            try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
            except: pass
        elif act == "cleargroups":
            db["settings"]["allowed_groups"] = []
            save_data(db)
            await cb.answer("✅ All allowed groups cleared.", show_alert=True)
            t, kb = get_admin_groups()
            try: await cb.message.edit_text(t, parse_mode=ParseMode.HTML, reply_markup=kb)
            except: pass
        return

    # ── VIP Request System ──
    if d.startswith("vip|"):
        parts = d.split("|")
        action = parts[1]
        
        if action == "req":
            req_uid = parts[2]
            user_data = db.get("users", {}).get(req_uid, {})
            if user_data.get("vip"):
                await cb.answer("✅ You already have VIP access!", show_alert=True)
                return
            # Send request to admin
            try:
                await bot.send_message(
                    int(ADMIN_ID),
                    f"👑 <b>𝗩𝗜𝗣 𝗔𝗰𝗰𝗲𝘀𝘀 𝗥𝗲𝗾𝘂𝗲𝘀𝘁</b>\n\n"
                    f"<blockquote>"
                    f"👤 <b>User ID:</b> <code>{req_uid}</code>\n"
                    f"📅 <b>Joined:</b> {user_data.get('joined', 'Unknown')}\n"
                    f"📊 <b>Status:</b> {'Approved' if user_data.get('approved', True) else 'Pending'}"
                    f"</blockquote>\n\n"
                    f"<i>User is requesting VIP access to download from premium sites.</i>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Grant VIP", callback_data=f"vip|grant|{req_uid}"),
                         InlineKeyboardButton("❌ Deny", callback_data=f"vip|deny|{req_uid}")]
                    ])
                )
                await cb.answer("✅ VIP request sent to admin! Please wait for approval.", show_alert=True)
            except:
                await cb.answer("⚠️ Failed to send request. Try contacting admin directly.", show_alert=True)
        
        elif action == "grant":
            if not is_admin(cb.from_user.id): return await cb.answer("Not admin.", show_alert=True)
            tgt = parts[2]
            if tgt in db["users"]:
                db["users"][tgt]["vip"] = True
                save_data(db)
                await cb.answer(f"✅ VIP granted to {tgt}!", show_alert=True)
                try: await cb.message.edit_text(f"✅ <b>VIP Granted</b> to <code>{tgt}</code>", parse_mode=ParseMode.HTML)
                except: pass
                # Notify user
                try:
                    await bot.send_message(
                        int(tgt),
                        f"🎉 <b>𝗖𝗼𝗻𝗴𝗿𝗮𝘁𝘂𝗹𝗮𝘁𝗶𝗼𝗻𝘀!</b>\n\n"
                        f"<blockquote>"
                        f"👑 You have been granted <b>VIP Access</b>!\n\n"
                        f"You can now download from ALL platforms:\n"
                        f"PornHub, XVideos, XNXX, RedTube, and 20+ more!"
                        f"</blockquote>\n\n"
                        f"<i>Send any video link to start downloading.</i>\n\n"
                        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
                        f"<b>⚡ 𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>",
                        parse_mode=ParseMode.HTML, disable_web_page_preview=True
                    )
                except: pass
            else:
                await cb.answer("❌ User not found.", show_alert=True)
        
        elif action == "deny":
            if not is_admin(cb.from_user.id): return await cb.answer("Not admin.", show_alert=True)
            tgt = parts[2]
            await cb.answer(f"❌ VIP denied for {tgt}.", show_alert=True)
            try: await cb.message.edit_text(f"❌ <b>VIP Denied</b> for <code>{tgt}</code>", parse_mode=ParseMode.HTML)
            except: pass
            try:
                await bot.send_message(
                    int(tgt),
                    f"❌ <b>VIP Request Denied</b>\n\n"
                    f"<blockquote>Your VIP access request was not approved.\n"
                    f"Contact <a href='https://t.me/IRONMAXPRO'>@IRONMAXPRO</a> for more info.</blockquote>",
                    parse_mode=ParseMode.HTML, disable_web_page_preview=True
                )
            except: pass
        return

    # ── Force Channel Check ──
    if d.startswith("fc|"):
        action = d.split("|")[1]
        if action == "check":
            uid = cb.from_user.id
            joined = await check_force_channel(bot, uid)
            if joined:
                await cb.answer("✅ Verified! You can now use the bot.", show_alert=True)
                try: await cb.message.delete()
                except: pass
            else:
                await cb.answer("❌ You haven't joined yet. Please join first!", show_alert=True)
        return

    # ── Ask Delivery Mode ──
    if d.startswith("ask|"):
        if not await enforce_force_channel(bot, cb): return
        parts = d.split("|")
        uid = parts[1]
        vid = parts[2]
        aud = parts[3] if len(parts) > 3 else ""
        vinfo = sid_info(uid)
        vtitle = vinfo.get("title", "")
        if vtitle and len(vtitle) > 40: vtitle = vtitle[:37] + "..."
        
        info_line = ""
        if vtitle: info_line = f"\n🎬 <i>{vtitle}</i>\n"
        
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Send to Telegram", callback_data=f"tg|{uid}|{vid}|{aud}")],
            [InlineKeyboardButton("🔗 Direct Link (Fast)", callback_data=f"gf|{uid}|{vid}|{aud}")],
            [InlineKeyboardButton("🔄 Change Quality", callback_data=f"chq|{uid}"),
             InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|")],
        ])
        try:
            if cb.message.photo:
                await cb.message.edit_caption(
                    caption=(
                        f"<b>🚚 𝗦𝗲𝗹𝗲𝗰𝘁 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝘆 𝗠𝗲𝘁𝗵𝗼𝗱</b>\n"
                        f"{info_line}\n"
                        f"<blockquote>"
                        f"<b>📤 Telegram:</b> Directly in chat (up to 2GB)\n"
                        f"<b>🔗 Direct Link:</b> Cloud link via Gofile (No limits)\n"
                        f"<b>🔄 Change:</b> Pick a different quality"
                        f"</blockquote>"
                    ),
                    parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                await cb.message.edit_text(
                    f"<b>🚚 𝗦𝗲𝗹𝗲𝗰𝘁 𝗗𝗲𝗹𝗶𝘃𝗲𝗿𝘆 𝗠𝗲𝘁𝗵𝗼𝗱</b>\n"
                    f"{info_line}\n"
                    f"<blockquote>"
                    f"<b>📤 Telegram:</b> Directly in chat (up to 2GB)\n"
                    f"<b>🔗 Direct Link:</b> Cloud link via Gofile (No limits)\n"
                    f"<b>🔄 Change:</b> Pick a different quality"
                    f"</blockquote>",
                    parse_mode=ParseMode.HTML, reply_markup=kb
                )
        except: pass
        return
    
    # ── Change Quality (re-show quality picker) ──
    if d.startswith("chq|"):
        uid = d.split("|")[1]
        url = sid_get(uid)
        if not url:
            await cb.answer("⚠️ Link expired. Send URL again.", show_alert=True); return
        await cb.answer("🔄 Re-fetching qualities...")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, get_info, url)
            formats = get_formats(info)
            btns = []
            for f in formats:
                s = sz(f["size"]) if f["size"] else "?"
                fps_txt = f" {f['fps']}fps" if f["fps"] and f["fps"] > 30 else ""
                label = f"📹 {f['label']}{fps_txt}  ·  {s}"
                aid = f["audio_id"] or ""
                btns.append([InlineKeyboardButton(label, callback_data=f"ask|{uid}|{f['fid']}|{aid}")])
            btns.append([
                InlineKeyboardButton("🎵 Audio Only", callback_data=f"ask|{uid}|bestaudio|"),
                InlineKeyboardButton("⚡ Best Auto", callback_data=f"ask|{uid}|best|")
            ])
            btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel|")])
            kb = InlineKeyboardMarkup(btns)
            try:
                if cb.message.photo:
                    await cb.message.edit_caption(caption="<b>🎯 𝗖𝗵𝗼𝗼𝘀𝗲 𝗤𝘂𝗮𝗹𝗶𝘁𝘆:</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
                else:
                    await cb.message.edit_text("<b>🎯 𝗖𝗵𝗼𝗼𝘀𝗲 𝗤𝘂𝗮𝗹𝗶𝘁𝘆:</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
            except: pass
        except Exception as e:
            await cb.answer(f"❌ Failed: {str(e)[:80]}", show_alert=True)
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

    # Get video info for thumbnail + title
    vinfo = sid_info(url_id)
    vid_title = vinfo.get("title", "")
    vid_thumb = vinfo.get("thumb", "")
    if vid_title and len(vid_title) > 50: vid_title = vid_title[:47] + "..."
    
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

    # Build caption with title + branding
    title_line = f"🎬 <b>{vid_title}</b>\n" if vid_title else ""
    upload_caption = (
        f"<b>✅ {pi['name']} Video</b>\n\n"
        f"<blockquote>"
        f"{title_line}"
        f"📁 <b>{sz(fsize)}</b> · ⬇️ <b>{dl_spd}</b> · ⏱ <b>{dl_time:.0f}s</b>"
        f"</blockquote>\n\n"
        f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
        f"<b>⚡ 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗱 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
    )

    # Download thumbnail for upload
    thumb_path = None
    if vid_thumb:
        try:
            thumb_path = str(DOWNLOAD_DIR / f"{dl_id}_thumb.jpg")
            r = requests.get(vid_thumb, timeout=10)
            with open(thumb_path, "wb") as f: f.write(r.content)
        except:
            thumb_path = None

    try:
        video_msg = await cb.message.reply_video(
            video=filepath,
            caption=upload_caption,
            parse_mode=ParseMode.HTML,
            supports_streaming=True,
            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
            file_name=f"{vid_title or 'video'}.mp4" if vid_title else None,
            progress=up_prog,
            disable_web_page_preview=True,
        )
        
        # Forward to dump channels
        dump_channels = db["settings"].get("dump_channels", [])
        for ch in dump_channels:
            try: await video_msg.copy(int(ch))
            except: pass
        
        # Increment download counter
        db["stats"]["total_dl"] = db["stats"].get("total_dl", 0) + 1
        save_data(db)

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
        if thumb_path: cleanup(thumb_path)
        CANCEL_FLAGS.pop(dl_id, None)


# ━━━ URL HANDLER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.on_message(filters.text & filters.regex(r"^(?!/)") & user_filter)
async def on_url(client, msg: Message):
    text = msg.text.strip()
    
    # Force channel check
    if not await enforce_force_channel(client, msg): return
    
    # Try to delete user's message
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

    # VIP check — free users can only use xHamster + social media
    uid = msg.from_user.id
    if not check_vip_access(uid, plat):
        vip_txt = (
            f"<b>👑 𝗩𝗜𝗣 𝗔𝗰𝗰𝗲𝘀𝘀 𝗥𝗲𝗾𝘂𝗶𝗿𝗲𝗱</b>\n\n"
            f"<blockquote>"
            f"{pi['icon']} <b>{pi['name']}</b> is a VIP-only platform.\n\n"
            f"This site requires premium access to download."
            f"</blockquote>\n\n"
            f"<blockquote>"
            f"<b>🆓 Free Sites:</b>\n"
            f"🔶 xHamster · 💜 Instagram · 🔷 Facebook\n\n"
            f"<b>👑 VIP Sites:</b>\n"
            f"🟠 PornHub · 🔴 XVideos · 🟡 XNXX\n"
            f"🔺 RedTube · 🩷 YouPorn · 🟤 SpankBang\n"
            f"🎥 Chaturbate · 💃 Stripchat + more"
            f"</blockquote>\n\n"
            f"<blockquote>"
            f"👇 <b>Tap below to request VIP access</b>\n"
            f"Your ID: <code>{uid}</code>"
            f"</blockquote>\n\n"
            f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━</i>\n"
            f"<b>�‍💻 ��𝘃𝗲𝗹�𝗼�𝗲𝗱 𝗯𝘆</b> <a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
        )
        vip_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👑 Request VIP Access", callback_data=f"vip|req|{uid}")],
            [InlineKeyboardButton("💬 Contact @IRONMAXPRO", url="https://t.me/IRONMAXPRO")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="nav|start")]
        ])
        if BANNER.exists():
            await msg.reply_photo(str(BANNER), caption=vip_txt, parse_mode=ParseMode.HTML, reply_markup=vip_kb)
        else:
            await msg.reply_text(vip_txt, parse_mode=ParseMode.HTML, reply_markup=vip_kb, disable_web_page_preview=True)
        return

    status = await msg.reply_text(
        f"{pi['icon']} <b>𝗔𝗻𝗮𝗹𝘆𝘇𝗶𝗻𝗴...</b>", parse_mode=ParseMode.HTML)

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
        uid = sid_store(url, info)

        # Build buttons
        if formats:
            btns = []
            for f in formats:
                s = sz(f["size"]) if f["size"] else "?"
                fps = f" {f['fps']}fps" if f["fps"] and f["fps"] > 30 else ""
                label = f"📹 {f['label']}{fps}  ·  {s}"
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
        btns.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel|")])

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
            f"{pi['icon']} <b>{pi['name']} — 𝗩𝗶𝗱𝗲𝗼 𝗙𝗼𝘂𝗻𝗱</b>\n\n"
            f"<blockquote>"
            f"🎬 <b>{title}</b>\n\n"
            f"⏱ {d}  ·  👤 {who}  ·  👁 {vstr}"
            f"</blockquote>\n\n"
            f"<b>🎯 𝗔𝘃𝗮𝗶𝗹𝗮𝗯𝗹𝗲 𝗤𝘂𝗮𝗹𝗶𝘁𝗶𝗲𝘀:</b>\n"
            f"{q_txt}\n"
            f"👇 <b>Tap to select quality:</b>\n\n"
            f"<i>━ 𝗕𝗼𝘁 𝗯𝘆 </i><a href='https://t.me/IRONMAXPRO'>@𝗜𝗥𝗢𝗡𝗠𝗔𝗫𝗣𝗥𝗢</a>"
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


# ━━━ GLOBAL ERROR HANDLER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import traceback

async def send_error_to_admin(context: str, error: Exception):
    """Send error details to admin — bot never crashes."""
    try:
        tb = traceback.format_exc()
        err_txt = (
            f"🚨 <b>Bot Error Report</b>\n\n"
            f"<blockquote>"
            f"<b>Context:</b> <code>{context[:100]}</code>\n"
            f"<b>Error:</b> <code>{str(error)[:300]}</code>"
            f"</blockquote>\n\n"
            f"<blockquote expandable>"
            f"<b>Traceback:</b>\n<code>{tb[:2000]}</code>"
            f"</blockquote>\n\n"
            f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        )
        await bot.send_message(int(ADMIN_ID), err_txt, parse_mode=ParseMode.HTML)
    except Exception as e2:
        logger.error(f"Failed to send error to admin: {e2}")

def global_exception_handler(loop, context):
    """Catches ALL unhandled asyncio exceptions — bot never dies."""
    exception = context.get("exception")
    msg = context.get("message", "Unknown async error")
    logger.error(f"[GLOBAL] Async exception: {msg} | {exception}")
    if exception:
        try:
            tb_str = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        except:
            tb_str = str(exception)
        asyncio.create_task(send_error_to_admin(f"Global async: {msg[:80]}", exception))

# Override default sys exception hook  
_orig_excepthook = sys.excepthook
def custom_excepthook(exc_type, exc_value, exc_tb):
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical(f"[UNHANDLED] {tb_str}")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(send_error_to_admin(f"sys.excepthook: {exc_type.__name__}", exc_value))
    except: pass
    _orig_excepthook(exc_type, exc_value, exc_tb)

sys.excepthook = custom_excepthook


if __name__ == "__main__":
    print(f"[*] {BRAND} v{VER}")
    print(f"[*] Sites: {len(SITES)} | ffmpeg: {'Y' if HAS_FFMPEG else 'N'} | aria2: {'Y' if HAS_ARIA2 else 'N'}")
    
    from aiohttp import web
    import os
    
    async def handle(request):
        return web.Response(text=f"{BRAND} Bot is online and running.")
        
    async def start_webserver():
        app = web.Application()
        app.router.add_get('/', handle)
        runner = web.AppRunner(app)
        await runner.setup()
        port = int(os.environ.get("PORT", 8080))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"[OK] Web server started on port {port}")
    
    async def main():
        # Set global asyncio error handler — bot never dies
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(global_exception_handler)
        
        await start_webserver()
        
        # Infinite retry loop — bot NEVER stops on Render
        while True:
            try:
                await bot.start()
                print(f"[OK] Telegram Bot fully operational...")
                
                # Notify admin that bot started
                try:
                    await bot.send_message(
                        int(ADMIN_ID),
                        f"✅ <b>{BRAND} v{VER}</b> is now <b>ONLINE</b>\n\n"
                        f"<blockquote>"
                        f"🖥 CPU: {psutil.cpu_percent()}%\n"
                        f"💾 RAM: {psutil.virtual_memory().percent}%\n"
                        f"👥 Users: {len(db['users'])}\n"
                        f"📥 Total Downloads: {db['stats'].get('total_dl', 0)}"
                        f"</blockquote>\n\n"
                        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>",
                        parse_mode=ParseMode.HTML
                    )
                except: pass
                
                await idle()
                
            except Exception as e:
                logger.critical(f"Bot crashed: {e}")
                tb = traceback.format_exc()
                print(f"[CRITICAL] Bot crashed: {e}\n{tb}")
                
                # Try to notify admin
                try:
                    await bot.send_message(
                        int(ADMIN_ID),
                        f"🚨 <b>BOT CRASHED — Auto Restarting!</b>\n\n"
                        f"<blockquote><code>{str(e)[:500]}</code></blockquote>\n\n"
                        f"<blockquote expandable><code>{tb[:2000]}</code></blockquote>\n\n"
                        f"<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n"
                        f"<i>🔄 Restarting in 10 seconds...</i>",
                        parse_mode=ParseMode.HTML
                    )
                except: pass
                
                # Stop and wait before retry
                try: await bot.stop()
                except: pass
                
                await asyncio.sleep(10)
                print("[*] Attempting restart...")
                continue
    
    bot.run(main())
