import telebot
import requests
import hashlib
import base64
import json
import logging
import threading
import socketio
import random
import time
import string
import math
import os
import sys
import traceback
from flask import Flask, jsonify
from collections import deque
from datetime import datetime, timedelta

# =========================
# CẤU HÌNH LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Tắt log không cần thiết
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)

# =========================
# FLASK KEEP ALIVE (RENDER)
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "👑 LC79 ELITE PRO MAX v5.5 | QUANT ENGINE ONLINE ✅"

@app.route("/health")
def health():
    return jsonify({
        "status": "ONLINE",
        "bot": "LC79 ELITE PRO MAX v5.5 SUPER VIP",
        "server": "Render",
        "algo": "QUANT-v5.5 FAST CYCLE PULSE ENGINE",
        "time": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })

def run_web():
    try:
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Web server error: {e}")

# =========================
# CẤU HÌNH BOT
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8901426971:AAGIVDd6eMlzV3ZQcRMMBlHHt-PvNZKQUa0")
ADMIN_ID = 7833803456
ADMIN_USERNAME = "@cskhvilong1"

# Khởi tạo bot với retry
bot = telebot.TeleBot(BOT_TOKEN)
bot.set_my_commands([
    telebot.types.BotCommand("/start", "🏠 Mở menu chính hệ thống VIP"),
    telebot.types.BotCommand("/huongdan", "📖 Bảng hướng dẫn sử dụng chi tiết"),
    telebot.types.BotCommand("/nhapkey", "🔑 Nhập key kích hoạt bản quyền VIP"),
    telebot.types.BotCommand("/thongtin", "💎 Xem thông tin tài khoản & hạn dùng"),
    telebot.types.BotCommand("/login", "🔐 Đăng nhập tài khoản game"),
    telebot.types.BotCommand("/autobet", "⚡ Bật / tắt tự động đặt cược"),
    telebot.types.BotCommand("/chotlai", "🎯 Cài đặt Chốt Lời / Cắt Lỗ tự động"),
    telebot.types.BotCommand("/x2", "💸 Bật / tắt X2 cược khi thua VIP"),
    telebot.types.BotCommand("/lichsucau", "📊 Xem lịch sử cầu & xu hướng 3D"),
    telebot.types.BotCommand("/stop", "⏹️ Ngắt kết nối an toàn"),
    telebot.types.BotCommand("/taokey", "👑 [ADMIN] Tạo key bản quyền VIP"),
    telebot.types.BotCommand("/danhsachkey", "📋 [ADMIN] Xem danh sách key còn lại"),
])

# =========================
# CẤU HÌNH HỆ THỐNG
# =========================
HISTORY_API_URL = "https://wtxmd52.tele68.com/v1/txmd5/lite-sessions"
API_URL_FALLBACK = "https://living-telecommunications-start-consoles.trycloudflare.com/api/txmd5"
MAX_HISTORY_STORE = 500
MIN_CONFIDENCE_AUTO_BET = 52
AUTO_BET_RUN_UNTIL_STOP = True
MAX_MARTINGALE_LEVEL = 6
MARTINGALE_MULTIPLIER = 2

# Cấu hình VIP Chốt Lời / Cắt Lỗ mặc định
AUTO_STOP_LOSS_PERCENT = 15
AUTO_TAKE_PROFIT_PERCENT = 25
AUTO_COOLDOWN_AFTER_LOSE = 0

# =========================
# BIẾN TOÀN CỤC
# =========================
active_sockets = {}
user_states = {}
valid_keys = {}
authorized_users = {}

# =========================
# HÀM TIỆN ÍCH UI VIP v5.5 ULTRA LUXURY
# =========================
def fmt_money(n):
    try:
        return f"{int(n):,}".replace(",", ".")
    except Exception:
        return str(n)

def bar(percent, width=12):
    percent = max(0, min(100, percent))
    filled = int(width * percent / 100)
    return "█" * filled + "▒" * (width - filled)

def pt_name(pt):
    MAP = {
        "1_1_pattern": "⚡ CẦU 1-1 (XEM KẼ)",
        "1_1_LONG_pattern": "🌟 CẦU 1-1 DÀI VIP",
        "2_2_pattern": "🔄 CẦU 2-2 (NHỊP KÉP)",
        "2_2_LONG_pattern": "💫 CẦU 2-2 DÀI TẦN SỐ CAO",
        "2_1_2_pattern": "🎯 CẦU 2-1-2 ĐỐI XỨNG",
        "1_2_1_pattern": "🎯 CẦU 1-2-1 ĐỐI XỨNG",
        "1_3_1_pattern": "📊 CẦU 1-3-1 TAM GIÁC",
        "3_1_3_pattern": "📊 CẦU 3-1-3 TAM GIÁC",
        "3_2_3_pattern": "📈 CẦU 3-2-3 BẬC THANG",
        "2_3_2_pattern": "📈 CẦU 2-3-2 BẬC THANG",
        "3_3_pattern": "🔥 CẦU BỆT 3 PHIÊN",
        "4_4_pattern": "🔥 CẦU BỆT 4 PHIÊN",
        "long_run_pattern": "🐉 CẦU BỆT RỒNG DÀI",
        "super_long_pattern": "🐲 SIÊU BỆT ĐẮC LỘC",
        "fast_break_pattern": "💥 BẺ CẦU BỆT XUNG LỰC MẠNH",
        "dice_extreme_break": "🎯 BẺ CẦU XÚC XẮC CỰC BIÊN",
        "cycle_shift_pattern": "🔄 BẮT BẺ CHU KỲ ĐẢO NHỊP",
        "reversal_warning": "⚠️ SẮP ĐẢO CẦU (ĐỈNH ENTROPY)",
        "bias_pattern": "⚖️ CẦU LỆCH THIÊN HƯỚNG",
        "random_pattern": "🎲 CẦU NGẪU NHIÊN / DAO ĐỘNG"
    }
    return MAP.get(pt, "🔮 " + pt.upper())

ACCENT = {
    "green": "🟩",
    "red": "🟥",
    "gold": "🟨",
    "blue": "🟦",
    "purple": "🟪",
    "diamond": "💎",
    "fire": "🔥"
}

def BOX(title, body, color="blue"):
    """Giao diện Khung VIP v5.5 Ultra - Sang trọng, cân đối, siêu chuẩn mobile."""
    dot = ACCENT.get(color, "🟦")
    rule = "══════════════════════════"
    sub_rule = "──────────────────────────"
    head = f"{dot} <b>{title.strip().upper()}</b>"
    lines = []
    for ln in body.strip().split("\n"):
        s = ln.strip()
        if not s:
            continue
        if set(s) <= {"═", "="}:
            lines.append(rule)
        elif set(s) <= {"─", "-"}:
            lines.append(sub_rule)
        else:
            lines.append(f"│ {s}")
    return f"{head}\n{rule}\n" + "\n".join(lines) + f"\n{rule}"

def card(title, body, color="blue"):
    return BOX(title, body, color)

def send_card(cid, title, body, color="blue", kb=None):
    try:
        bot.send_message(
            cid, card(title, body, color),
            parse_mode="HTML", reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Send card error: {e}")

# =========================
# XỬ LÝ DỮ LIỆU CẦU
# =========================
def parse_lines(data):
    if not data or not isinstance(data.get("list"), list):
        return []
    arr = sorted(data["list"], key=lambda x: x["id"])
    out = []
    for it in arr:
        p = it.get("point", sum(it.get("dices", [0, 0, 0])))
        r = it.get("resultTruyenThong")
        if r in ("TAI", "XIU"):
            out.append({
                "session": it["id"],
                "dice": it.get("dices", [0, 0, 0]),
                "total": p,
                "result": r,
                "tx": "T" if p >= 11 else "X"
            })
    return out

def fetch_history_from_api(limit=80):
    for url in (HISTORY_API_URL, API_URL_FALLBACK):
        try:
            r = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://lc79b.bet"
            }, timeout=10)
            if r.status_code != 200:
                continue
            d = r.json()
            arr = parse_lines(d)
            if arr:
                return arr[-limit:]
        except Exception as e:
            logger.warning(f"Fetch history error: {e}")
            continue
    return []

# =========================
# HÀM XỬ LÝ KEY VÀ AUTH
# =========================
def check_auth(chat_id):
    if chat_id == ADMIN_ID:
        return True
    if chat_id in authorized_users:
        if time.time() <= authorized_users[chat_id]:
            return True
        else:
            del authorized_users[chat_id]
    return False

def require_auth(fn):
    def wrapper(m, *args, **kwargs):
        if not check_auth(m.chat.id):
            msg = BOX("🔒 CHƯA KÍCH HOẠT VIP",
                      f"Vui lòng nhập key bản quyền:\n👉 /nhapkey MÃ_KEY\n📩 Liên hệ Admin: {ADMIN_USERNAME}", "red")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
            return
        return fn(m, *args, **kwargs)
    return wrapper

def format_expire_time(ts):
    r = ts - time.time()
    if r <= 0:
        return "❌ HẾT HẠN"
    d = int(r // 86400)
    h = int((r % 86400) // 3600)
    m = int((r % 3600) // 60)
    if d > 0:
        return f"✅ {d} NGÀY {h}G {m}P"
    return f"✅ {h}G {m}P"

# =========================
# KHỞI TẠO USER STATE
# =========================
def init_user_state(chat_id):
    if chat_id not in user_states:
        user_states[chat_id] = {
            "raw_hist": [],
            "history": [],
            "points_history": [],
            "auto_bet_enabled": False,
            "bet_amount": 10000,
            "base_bet": 10000,
            "start_balance": 0,
            "take_profit": 100000,     # Chốt lời mặc định 100k
            "stop_loss": 50000,        # Cắt lỗ mặc định 50k
            "martingale_enabled": False,
            "martingale_level": 0,
            "current_prediction": None,
            "waiting_for_result": False,
            "has_bet_this_session": False,
            "session_id": None,
            "balance": 0,
            "win_streak": 0,
            "lose_streak": 0,
            "total_win": 0,
            "total_lose": 0,
            "cooldown": 0,
            "peak_balance": 0,
            "min_balance": float('inf'),
            "last_bet_result": None,
            "last_analysis": {}
        }

# =========================
# TOÁN HỌC & SIÊU THUẬT TOÁN QUANT-v5.5 PRO
# NÂNG CẤP BẮT BẺ CHU KỲ CẦU NHANH THEO TÍN HIỆU MẠNH NHẤT
# =========================
def _entropy(arr):
    if not arr:
        return 0.0
    f = {}
    n = len(arr)
    for v in arr:
        f[v] = f.get(v, 0) + 1
    return -sum((c / n) * math.log2(c / n) for c in f.values() if c > 0)

def _std(arr):
    if not arr:
        return 0
    m = sum(arr) / len(arr)
    return math.sqrt(sum((x - m) ** 2 for x in arr) / len(arr))

def _similarity(a, b):
    if len(a) != len(b) or not a:
        return 0
    return sum(1 for x, y in zip(a, b) if x == y) / len(a)

def _ema(points, period=5):
    if not points:
        return 10.5
    k = 2 / (period + 1)
    ema_val = points[0]
    for p in points[1:]:
        ema_val = (p * k) + (ema_val * (1 - k))
    return ema_val

def _fast_cycle_break_detector(history, points_history):
    """
    SIÊU THUẬT TOÁN BẮT BẺ CHU KỲ CẦU NHANH:
    Nhận diện gãy bệt, xả điểm xúc xắc cực biên, bẻ nhịp cầu sớm.
    """
    if len(history) < 4:
        return None, 0.0, "N/A"

    h = history[-10:]
    pts = points_history[-5:] if points_history else []

    # 1. Bẻ Cầu Bệt Khi Chạm Ngưỡng Bão Hòa & Đỉnh Entropy
    streak_val = h[-1]
    streak_len = 0
    for i in range(len(h) - 1, -1, -1):
        if h[i] == streak_val:
            streak_len += 1
        else:
            break

    # Tín hiệu Bẻ Bệt Khi Dài 4-7 Phiên Kèm Điểm Xúc Xắc Cực Biên
    if streak_len >= 4:
        opposite = "XIU" if streak_val == "TAI" else "TAI"
        ent = _entropy(h)
        
        # Nếu phiên gần nhất nổ Tài cực đại (16, 17) hoặc Xỉu cực tiểu (3, 4)
        if pts and ((streak_val == "TAI" and pts[-1] >= 15) or (streak_val == "XIU" and pts[-1] <= 5)):
            return opposite, 92.0, "dice_extreme_break"
        
        # Bẻ Bệt Tự Động theo nhịp chu kỳ
        if streak_len >= 5 or ent > 0.82:
            return opposite, 88.0, "fast_break_pattern"

    # 2. Bắt Bẻ Đảo Nhịp 1-1-2-1 / 3-1-1 Nhanh
    if len(h) >= 4:
        # Nhịp 1-1-2 gãy -> Bẻ về 1-1
        if h[-4] != h[-3] and h[-3] == h[-2] and h[-2] != h[-1]:
            target = "XIU" if h[-1] == "TAI" else "TAI"
            return target, 83.0, "cycle_shift_pattern"

    return None, 0.0, "NONE"

def _markov_chain_predict(history):
    """Mô hình Markov Chain bậc 1 & bậc 2 phân tích xác suất chuyển trạng thái"""
    if len(history) < 5:
        return None, 50.0

    # Bậc 2 (1-step state from 2 previous states)
    last2 = tuple(history[-2:])
    trans_2 = {"TAI": 0, "XIU": 0}
    for i in range(len(history) - 2):
        if (history[i], history[i+1]) == last2:
            trans_2[history[i+2]] += 1
    
    total_2 = trans_2["TAI"] + trans_2["XIU"]
    if total_2 >= 3:
        p_tai = (trans_2["TAI"] / total_2) * 100
        if p_tai > 55:
            return "TAI", p_tai
        elif p_tai < 45:
            return "XIU", 100 - p_tai

    # Bậc 1
    last1 = history[-1]
    trans_1 = {"TAI": 0, "XIU": 0}
    for i in range(len(history) - 1):
        if history[i] == last1:
            trans_1[history[i+1]] += 1
    
    total_1 = trans_1["TAI"] + trans_1["XIU"]
    if total_1 >= 5:
        p_tai = (trans_1["TAI"] / total_1) * 100
        if p_tai >= 52:
            return "TAI", p_tai
        else:
            return "XIU", 100 - p_tai

    return None, 50.0

def _pattern_detector(history):
    """Nhận dạng cấu trúc Pattern Cầu chuẩn Xác Suất Thống Kê"""
    if len(history) < 4:
        return "random_pattern", None, 50.0

    h = history[-12:]
    n = len(h)

    # Kiểm tra Siêu Bệt / Bệt Dài
    streak_val = h[-1]
    streak_len = 0
    for i in range(n - 1, -1, -1):
        if h[i] == streak_val:
            streak_len += 1
        else:
            break

    if streak_len >= 6:
        return "super_long_pattern", streak_val, min(95, 75 + streak_len * 3)
    elif streak_len >= 4:
        return "long_run_pattern", streak_val, 78.0
    elif streak_len == 3:
        return "3_3_pattern", streak_val, 68.0

    # Cầu 1-1
    is_1_1 = True
    for i in range(max(0, n - 6), n - 1):
        if h[i] == h[i+1]:
            is_1_1 = False
            break
    if is_1_1 and n >= 5:
        next_pred = "TAI" if h[-1] == "XIU" else "XIU"
        pattern_type = "1_1_LONG_pattern" if n >= 8 else "1_1_pattern"
        return pattern_type, next_pred, 82.0

    # Cầu 2-2
    if n >= 6:
        sub = h[-6:]
        if sub[0] == sub[1] and sub[2] == sub[3] and sub[4] == sub[5] and sub[0] != sub[2] and sub[2] != sub[4]:
            next_pred = "TAI" if sub[-1] == "XIU" else "XIU"
            return "2_2_LONG_pattern", next_pred, 84.0
    if n >= 4:
        sub = h[-4:]
        if sub[0] == sub[1] and sub[2] == sub[3] and sub[0] != sub[2]:
            next_pred = "TAI" if sub[-1] == "XIU" else "XIU"
            return "2_2_pattern", next_pred, 75.0

    # Cầu 1-2-1 / 2-1-2
    if n >= 4:
        if h[-4] != h[-3] and h[-3] == h[-2] and h[-2] != h[-1]:
            return "1_2_1_pattern", h[-2], 72.0
        if h[-4] == h[-3] and h[-3] != h[-2] and h[-2] == h[-1]:
            next_pred = "XIU" if h[-1] == "TAI" else "TAI"
            return "2_1_2_pattern", next_pred, 70.0

    # Cầu Lệch / Biased
    tai_cnt = h.count("TAI")
    xiu_cnt = h.count("XIU")
    if abs(tai_cnt - xiu_cnt) >= 4:
        favored = "TAI" if tai_cnt > xiu_cnt else "XIU"
        return "bias_pattern", favored, 66.0

    return "random_pattern", None, 50.0

def super_predict(history, points_history=None, raw_hist=None):
    """
    SIÊU THUẬT TOÁN QUANT-v5.5 PRO MAX
    Tổng hợp Multi-Engine: Fast Cycle Breaking + Pattern + Markov + Dice EMA + Entropy
    """
    if not history or len(history) < 3:
        res = random.choice(["TAI", "XIU"])
        return {
            "prediction": res,
            "confidence": 55,
            "pattern_type": "random_pattern",
            "pattern_name": pt_name("random_pattern"),
            "dice_trend": "Đang thu thập dữ liệu...",
            "risk_level": "🟢 THẤP",
            "reason": "Khởi tạo dữ liệu ban đầu"
        }

    # 1. Fast Cycle Breaking Signal Engine (Ưu tiên tín hiệu mạnh nhất)
    fb_pred, fb_conf, fb_type = _fast_cycle_break_detector(history, points_history)

    # 2. Pattern Matching Engine
    pt_type, pt_pred, pt_conf = _pattern_detector(history)

    # 3. Markov Chain Engine
    mk_pred, mk_conf = _markov_chain_predict(history)

    # 4. Dice EMA & Point Momentum
    ema_val = _ema(points_history[-10:] if points_history else [], period=5)
    ema_pred = "TAI" if ema_val > 10.5 else "XIU"
    ema_conf = min(88, 50 + abs(ema_val - 10.5) * 8)

    # 5. Entropy & Risk Warning
    ent = _entropy(history[-10:])
    risk = "🟢 SAFE"
    if ent > 0.92:
        risk = "⚠️ CAO (BIẾN ĐỘNG CỰC ĐẠI)"
    elif ent < 0.5:
        risk = "🔥 THẤP (CẦU ỔN ĐỊNH)"

    # 6. Ma Trận Đa Đồng Thuận Nâng Cấp (Strong Signal Consensus Vector)
    votes = {"TAI": 0.0, "XIU": 0.0}

    # Nếu có Tín hiệu Bắt Bẻ Cầu Nhanh cực mạnh -> Cộng trọng số ưu tiên vượt trội
    if fb_pred and fb_conf > 80:
        votes[fb_pred] += (fb_conf / 100) * 0.55
        active_pt = fb_type
    else:
        active_pt = pt_type

    if pt_pred:
        votes[pt_pred] += (pt_conf / 100) * 0.35
    if mk_pred:
        votes[mk_pred] += (mk_conf / 100) * 0.25
    votes[ema_pred] += (ema_conf / 100) * 0.25

    final_pred = "TAI" if votes["TAI"] >= votes["XIU"] else "XIU"
    raw_confidence = max(votes["TAI"], votes["XIU"]) * 100
    final_confidence = min(98, max(60, int(raw_confidence)))

    dice_trend_str = f"EMA(5): {ema_val:.1f} → {'KÉO TÀI' if ema_val > 10.5 else 'ÉP XỈU'}"
    reason_str = f"Pulse: {fb_type} | Pattern: {active_pt} | Markov: {mk_pred or 'N/A'}"

    return {
        "prediction": final_pred,
        "confidence": final_confidence,
        "pattern_type": active_pt,
        "pattern_name": pt_name(active_pt),
        "dice_trend": dice_trend_str,
        "risk_level": risk,
        "reason": reason_str
    }

def simple_predict(history):
    """Wrapper tương thích ngược sử dụng Super Predict Engine"""
    res = super_predict(history)
    return res["prediction"]

# =========================
# HÀM LOGIN VÀ WEBSOCKET
# =========================
def md5_hash(t):
    return hashlib.md5(t.encode()).hexdigest()

def login_and_get_token(u, p):
    try:
        r = requests.get(
            f"https://apifo88daigia.tele68.com/api?c=3&un={u}&pw={md5_hash(p)}&cp=R&cl=R&pf=web&at=",
            timeout=12
        ).json()
        if not r.get("success"):
            return {"_error": "Sai TK / MK hoặc tài khoản bị khóa"}
        
        sk = r["sessionKey"] + "=" * ((4 - len(r["sessionKey"]) % 4) % 4)
        nn = json.loads(base64.b64decode(sk)).get("nickname")
        
        r2 = requests.post(
            "https://wlb.tele68.com/v1/lobby/auth/login?cp=R&cl=R&pf=web&at=",
            json={"nickName": nn, "accessToken": r["accessToken"]},
            timeout=12
        ).json()
        
        if not r2.get("token"):
            return {"_error": "Không thể lấy Token xác thực game"}
        
        return {
            "token": r2["token"],
            "nickname": nn,
            "money": r2.get("remoteLoginResp", {}).get("money", 0)
        }
    except Exception as e:
        return {"_error": f"Lỗi kết nối máy chủ: {str(e)}"}

def start_websocket(cid, token):
    if cid in active_sockets:
        try:
            active_sockets[cid].disconnect()
        except Exception:
            pass
    
    sio = socketio.Client(
        reconnection=True,
        reconnection_attempts=99999,
        reconnection_delay=3,
        logger=False,
        engineio_logger=False
    )
    active_sockets[cid] = sio
    init_user_state(cid)
    
    @sio.event(namespace='/tx')
    def connect():
        arr = fetch_history_from_api(80)
        st = user_states[cid]
        if arr:
            st["raw_hist"] = arr
            st["history"] = [x["result"] for x in arr]
            st["points_history"] = [x["total"] for x in arr]
            msg = BOX("🟢 KẾT NỐI VIP THÀNH CÔNG",
                      f"📥 Thu thập thành công {len(arr):>2} phiên gần nhất\n"
                      f"🧠 QUANT-v5.5 BẮT BẺ CHU KỲ KÍCH HOẠT\n"
                      f"🎯 Hệ thống đã sẵn sàng dự đoán tự động!", "green")
            try:
                bot.send_message(cid, f"<pre>{msg}</pre>", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Send message error: {e}")
        else:
            try:
                send_card(cid, "🟢 KẾT NỐI GAME OK", "Đang thu thập và phân tích luồng dữ liệu mới...", "green")
            except Exception as e:
                logger.error(f"Send message error: {e}")

    @sio.on('new-session', namespace='/tx')
    def new_sess(d):
        st = user_states[cid]
        st["session_id"] = d.get("id")
        st["has_bet_this_session"] = False
        
        if st["raw_hist"]:
            analysis = super_predict(st["history"], st["points_history"], st["raw_hist"])
            st["last_analysis"] = analysis
            pred = analysis["prediction"]
            conf = analysis["confidence"]
            st["current_prediction"] = pred
            
            # Tính toán cược X2 Martingale nếu có
            current_bet = st.get("bet_amount", 10000)
            if st.get("martingale_enabled") and st.get("martingale_level", 0) > 0:
                current_bet = st["base_bet"] * (MARTINGALE_MULTIPLIER ** st["martingale_level"])
                st["bet_amount"] = current_bet

            color = "green" if pred == "TAI" else "red"
            badge = "🔵 TÀI" if pred == "TAI" else "🔴 XỈU"
            
            body = (
                f"🎲 PHIÊN MỚI: <b>#{st['session_id']}</b>\n"
                f"══════════════\n"
                f"🔮 DỰ ĐOÁN: <b>{badge}</b>\n"
                f"📊 ĐỘ TỰ TIN: <b>{conf}%</b>\n"
                f"📈 TÍN HIỆU: {bar(conf)}\n"
                f"📌 BẮT CẦU: {analysis['pattern_name']}\n"
                f"📉 ĐỘNG LƯỢNG: {analysis['dice_trend']}\n"
                f"🛡️ RỦI RO: {analysis['risk_level']}\n"
                f"💰 CƯỢC PHIÊN: <b>{fmt_money(current_bet)} VNĐ</b>"
            )
            msg = BOX("💎 DỰ ĐOÁN PHIÊN MỚI VIP", body, color)
            try:
                bot.send_message(cid, f"<pre>{msg}</pre>", parse_mode="HTML")
            except Exception as e:
                logger.error(f"Send message error: {e}")

    @sio.on('tick-update', namespace='/tx')
    def tk(d):
        st = user_states[cid]
        if d.get("state") == "BETTING" and st.get("auto_bet_enabled", False):
            if st.get("current_prediction") and not st.get("has_bet_this_session", False):
                try:
                    amt = st.get("bet_amount", 10000)
                    sio.emit("bet", {
                        "type": st["current_prediction"],
                        "amount": amt
                    }, namespace="/tx")
                    st["has_bet_this_session"] = True
                    bot.send_message(cid, f"⚡ <b>[AUTO BET]</b> Đã đặt cửa <b>{st['current_prediction']}</b> ({fmt_money(amt)} VNĐ) thành công! ✅", parse_mode="HTML")
                except Exception as e:
                    bot.send_message(cid, f"⚠️ LỖI ĐẶT CƯỢC: {e}")

    @sio.on('bet-result', namespace='/tx')
    def br(d):
        st = user_states[cid]
        if "postBalance" in d:
            st["balance"] = d["postBalance"]

    @sio.on('session-result', namespace='/tx')
    def sr(d):
        res = d.get("resultTruyenThong")
        st = user_states[cid]
        if res in ("TAI", "XIU"):
            dices = d.get("dices", [0, 0, 0])
            total_pts = sum(dices)
            rec = {
                "session": d.get("id"),
                "dice": dices,
                "total": total_pts,
                "result": res,
                "tx": "T" if total_pts >= 11 else "X"
            }
            st["raw_hist"].append(rec)
            st["history"].append(res)
            st["points_history"].append(total_pts)
            
            if len(st["raw_hist"]) > MAX_HISTORY_STORE:
                st["raw_hist"].pop(0)
                st["history"].pop(0)
                st["points_history"].pop(0)
            
            pred = st.get("current_prediction")
            if pred:
                win = pred == res
                status = "THẮNG (WIN) 🎉" if win else "THUA (LOSE) 💸"
                color = "green" if win else "red"
                
                total = st["total_win"] + st["total_lose"] + 1
                if win:
                    st["total_win"] += 1
                    st["win_streak"] += 1
                    st["lose_streak"] = 0
                    st["martingale_level"] = 0
                    st["bet_amount"] = st["base_bet"]
                else:
                    st["total_lose"] += 1
                    st["lose_streak"] += 1
                    st["win_streak"] = 0
                    if st.get("martingale_enabled", False):
                        st["martingale_level"] = min(
                            st["martingale_level"] + 1,
                            MAX_MARTINGALE_LEVEL
                        )
                
                wr = (st["total_win"] / total) * 100 if total > 0 else 0
                dice_str = " - ".join(str(x) for x in dices)
                
                # Tính toán PnL Lợi Nhuận
                net_pnl = st["balance"] - st["start_balance"] if st["start_balance"] > 0 else 0
                pnl_str = f"+{fmt_money(net_pnl)}" if net_pnl >= 0 else f"-{fmt_money(abs(net_pnl))}"
                
                body = (
                    f"⚔️ KẾT QUẢ PHIÊN: <b>#{d.get('id')}</b>\n"
                    f"══════════════\n"
                    f"🎲 XÚC XẮC: [ {dice_str} ] = <b>{total_pts}</b> ({res})\n"
                    f"🔮 BOT DỰ ĐOÁN: <b>{pred}</b>\n"
                    f"📌 TRẠNG THÁI: <b>{status}</b>\n"
                    f"──────────────────────────\n"
                    f"📈 TI LỆ THẮNG: <b>{wr:.1f}%</b> ({st['total_win']}W - {st['total_lose']}L)\n"
                    f"🔥 WIN STREAK: {st['win_streak']} | 💀 LOSE STREAK: {st['lose_streak']}\n"
                    f"💵 LỢI NHUẬN PnL: <b>{pnl_str} VNĐ</b>\n"
                    f"💰 SỐ DƯ HIỆN TẠI: <b>{fmt_money(st['balance'])} VNĐ</b>"
                )
                msg = BOX("📊 TỔNG TRẬN KẾT QUẢ VIP", body, color)
                try:
                    bot.send_message(cid, f"<pre>{msg}</pre>", parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Send message error: {e}")

                # ==========================================
                # NÂNG CẤP XỬ LÝ CHỐT LỜI / CẮT LỖ THỜI GIAN THỰC
                # ==========================================
                if st.get("auto_bet_enabled", False) and st["start_balance"] > 0:
                    # 1. Kiểm tra Chốt Lời (Take Profit)
                    if net_pnl >= st.get("take_profit", 100000):
                        st["auto_bet_enabled"] = False
                        tp_body = (
                            f"🎉 <b>ĐÃ ĐẠT MỤC TIÊU CHỐT LỜI VIP!</b>\n"
                            f"══════════════\n"
                            f"💰 Lợi Nhuận Thu Được: <b>+{fmt_money(net_pnl)} VNĐ</b>\n"
                            f"🎯 Chỉ Tiêu Chốt Lời: <b>{fmt_money(st['take_profit'])} VNĐ</b>\n"
                            f"🏦 Số Dư Đỉnh: <b>{fmt_money(st['balance'])} VNĐ</b>\n"
                            f"──────────────────────────\n"
                            f"⚡ Hệ thống đã tự động NGẮT CƯỢC để bảo toàn lợi nhuận!"
                        )
                        msg_tp = BOX("💎 CHỐT LỜI THÀNH CÔNG (TAKE PROFIT)", tp_body, "gold")
                        bot.send_message(cid, f"<pre>{msg_tp}</pre>", parse_mode="HTML", reply_markup=vip_menu(cid))

                    # 2. Kiểm tra Cắt Lỗ (Stop Loss)
                    elif net_pnl <= -abs(st.get("stop_loss", 50000)):
                        st["auto_bet_enabled"] = False
                        sl_body = (
                            f"🛡️ <b>ĐÃ CHẠM NGƯỠNG CẮT LỖ AN TOÀN!</b>\n"
                            f"══════════════\n"
                            f"💸 Tổng Thua Lỗ: <b>-{fmt_money(abs(net_pnl))} VNĐ</b>\n"
                            f"⚠️ Giới Hạn Cắt Lỗ: <b>-{fmt_money(st['stop_loss'])} VNĐ</b>\n"
                            f"🏦 Số Dư Còn Lại: <b>{fmt_money(st['balance'])} VNĐ</b>\n"
                            f"──────────────────────────\n"
                            f"⚡ Tự động dừng Auto Bet để bảo vệ nguồn vốn của bạn!"
                        )
                        msg_sl = BOX("🛡️ CẮT LỖ AN TOÀN (STOP LOSS)", sl_body, "red")
                        bot.send_message(cid, f"<pre>{msg_sl}</pre>", parse_mode="HTML", reply_markup=vip_menu(cid))

    @sio.event(namespace='/tx')
    def connect_error(data):
        logger.error(f"WS connect_error: {data}")
        detail = data.get("message") if isinstance(data, dict) else str(data)
        if detail and "unauthor" in str(detail).lower():
            send_card(cid, "KẾT NỐI THẤT BẠI",
                      "🔑 TOKEN HẾT HẠN HOẶC SAI TÀI KHOẢN\n─\n👉 Vui lòng đăng nhập lại: /login TK MK", "red")
        else:
            send_card(cid, "KẾT NỐI THẤT BẠI", f"⚠️ Chi tiết lỗi: {detail}", "red")

    @sio.event(namespace='/tx')
    def disconnect():
        logger.info(f"WS disconnected: {cid}")

    try:
        sio.connect(
            f"https://wtx.tele68.com?token={token}",
            socketio_path="tx",
            namespaces=["/tx"],
            transports=["websocket"],
            auth={"token": token},
            wait_timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://lc79b.bet",
                "Referer": "https://lc79b.bet/",
            }
        )
        sio.wait()
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        send_card(cid, "LỖI WEBSOCKET",
                  f"⚠️ Lỗi kết nối: {str(e)[:80]}\n─\n👉 Thử thực hiện lại /login sau vài giây", "red")

# =========================
# MENU & GIAO DIỆN BẢNG ĐIỀU KHIỂN
# =========================
def vip_menu(cid=None):
    B = telebot.types.InlineKeyboardButton
    kb = telebot.types.InlineKeyboardMarkup(row_width=2)

    st = user_states.get(cid) if cid else None
    auto_on = bool(st and st.get("auto_bet_enabled"))
    x2_on = bool(st and st.get("martingale_enabled"))
    linked = bool(cid and cid in active_sockets)

    kb.add(B(f"{'🟢' if linked else '🔴'} KẾT NỐI GAME", callback_data="login"))
    kb.add(
        B(f"{'⚡ AUTO: BẬT' if auto_on else '⏸️ AUTO: TẮT'}", callback_data="auto_toggle"),
        B(f"{'💸 X2: BẬT' if x2_on else '🔴 X2: TẮT'}", callback_data="x2_toggle"),
    )
    kb.add(
        B("🎯 CÀI CHỐT LỜI / CẮT LỖ", callback_data="chotlai_info"),
        B("📊 LỊCH SỬ CẦU VIP", callback_data="ls"),
    )
    kb.add(
        B("💎 TÀI KHOẢN VIP", callback_data="tt"),
        B("📖 HƯỚNG DẪN", callback_data="hd"),
    )
    kb.add(
        B("⏹️ DỪNG HỆ THỐNG", callback_data="stop"),
        B("♻️ LÀM MỚI BẢNG ĐIỀU KHIỂN", callback_data="refresh")
    )
    return kb

# =========================
# COMMAND HANDLERS
# =========================
@bot.message_handler(commands=['start'])
def cmd_start(m):
    try:
        cid = m.chat.id
        init_user_state(cid)
        logger.info(f"Start command from {cid}")
        
        if check_auth(cid):
            han = "👑 ADMIN VĨNH VIỄN" if cid == ADMIN_ID else format_expire_time(authorized_users[cid])
            body = (
                f"✨ CHÀO MỪNG QUÝ KHÁCH ĐẾN VIP SYSTEM ✨\n"
                f"══════════════\n"
                f"✅ TÌNH TRẠNG: ĐÃ KÍCH HOẠT VIP\n"
                f"⏳ THỜI HẠN: <b>{han}</b>\n"
                f"🧠 ALGO: <b>QUANT-v5.5 FAST CYCLE PULSE</b>\n"
                f"🎯 TÍN HIỆU: BẮT BẺ CHU KỲ CẦU NHANH CỰC MẠNH\n"
                f"══════════════\n"
                f"👉 Vui lòng chọn chức năng bên dưới menu:"
            )
            msg = BOX("👑 LC79 ELITE PRO MAX v5.5 VIP", body, "gold")
            bot.send_message(cid, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
        else:
            body = (
                f"🔒 BẠN CHƯA KÍCH HOẠT BẢN QUYỀN VIP\n"
                f"══════════════\n"
                f"🔑 Cú pháp nhập key: /nhapkey MÃ_KEY\n"
                f"📩 Liên hệ Admin để mua key: {ADMIN_USERNAME}"
            )
            msg = BOX("🏠 TRANG CHỦ HỆ THỐNG VIP", body, "blue")
            bot.send_message(cid, f"<pre>{msg}</pre>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Start command error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['huongdan'])
def cmd_hd(m):
    try:
        body = (
            f"📖 BẢNG HƯỚNG DẪN LỆNH HỆ THỐNG VIP\n"
            f"══════════════\n"
            f"🔑 /nhapkey KEY - Kích hoạt key VIP\n"
            f"🔐 /login TK MK - Đăng nhập tài khoản Game\n"
            f"⚡ /autobet on [MỨC] | off - Tự động cược\n"
            f"🎯 /chotlai [CHỐT_LỜI] [CẮT_LỖ] - Cài đặt Target\n"
            f"💸 /x2 on | off - Bật/tắt gấp thếp khi thua\n"
            f"📊 /lichsucau - Phân tích soi cầu 3D nâng cao\n"
            f"💎 /thongtin - Kiểm tra tài khoản & số dư\n"
            f"⏹️ /stop - Ngắt kết nối & ngắt Auto\n"
            f"══════════════\n"
            f"🛡️ Hỗ trợ Stop-Loss / Take-Profit bảo vệ vốn tự động\n"
            f"📩 Support VIP: {ADMIN_USERNAME}"
        )
        msg = BOX("📖 HƯỚNG DẪN SỬ DỤNG VIP", body, "blue")
        bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Huongdan command error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['taokey'])
def gk(m):
    if m.chat.id != ADMIN_ID:
        bot.reply_to(m, "⛔ Quyền hạn dành riêng cho ADMIN!")
        return
    
    try:
        p = m.text.split()
        d = int(p[1]) if len(p) > 1 else 30
        k = "VIP-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        valid_keys[k] = d
        ht = (datetime.now() + timedelta(days=d)).strftime("%d/%m/%Y %H:%M")
        body = f"🔑 KEY: <code>{k}</code>\n⏳ HẠN DÙNG: {d} NGÀY\n📅 HẾT HẠN: {ht}"
        msg = BOX("👑 TẠO KEY VIP THÀNH CÔNG", body, "gold")
        bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(m, f"❌ Cú pháp đúng: /taokey 30")

@bot.message_handler(commands=['danhsachkey'])
def lk(m):
    if m.chat.id != ADMIN_ID:
        return
    
    if not valid_keys:
        bot.reply_to(m, "📭 Kho key hiện đang trống!")
        return
    
    ds = "\n".join([f"🔑 <code>{k}</code> → {v} Ngày" for k, v in list(valid_keys.items())[:20]])
    body = f"{ds}\n──────────────────────────\n📊 TỔNG KHO KEY: <b>{len(valid_keys)}</b> KEY"
    msg = BOX("📋 DANH SÁCH KEY HIỆN CÓ", body, "purple")
    bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")

@bot.message_handler(commands=['nhapkey'])
def ak(m):
    try:
        p = m.text.split()
        if len(p) < 2:
            bot.reply_to(m, "⚠️ Cú pháp: /nhapkey VIP-XXXXXXXXXXXX")
            return
        
        k = p[1].upper()
        if k in valid_keys:
            days = valid_keys[k]
            authorized_users[m.chat.id] = time.time() + days * 86400
            del valid_keys[k]
            ht = datetime.fromtimestamp(authorized_users[m.chat.id]).strftime("%d/%m/%Y %H:%M")
            body = (
                f"✅ KÍCH HOẠT BẢN QUYỀN THÀNH CÔNG!\n"
                f"⏳ THỜI HẠN DÙNG: {days} NGÀY\n"
                f"📅 HẾT HẠN LÚC: {ht}\n"
                f"🧠 Thuật toán QUANT-v5.5 BẮT BẺ CHU KỲ đã kích hoạt!"
            )
            msg = BOX("💎 ACTIVE VIP PRO MAX", body, "green")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
        else:
            bot.reply_to(m, f"❌ KEY KHÔNG HỢP LỆ HOẶC ĐÃ ĐƯỢC SỬ DỤNG!\n📩 Liên hệ Admin: {ADMIN_USERNAME}")
    except Exception as e:
        logger.error(f"Nhapkey error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['chotlai'])
@require_auth
def cmd_chotlai(m):
    try:
        cid = m.chat.id
        init_user_state(cid)
        st = user_states[cid]
        p = m.text.split()
        
        if len(p) < 3:
            body = (
                f"🎯 CÀI ĐẶT CHỐT LỜI / CẮT LỖ VIP\n"
                f"══════════════\n"
                f"💎 CHỐT LỜI HIỆN TẠI: <b>+{fmt_money(st.get('take_profit', 100000))} VNĐ</b>\n"
                f"🛡️ CẮT LỖ HIỆN TẠI: <b>-{fmt_money(st.get('stop_loss', 50000))} VNĐ</b>\n"
                f"──────────────────────────\n"
                f"👉 Cú pháp thay đổi target:\n"
                f"<code>/chotlai [Tiền_Chốt_Lời] [Tiền_Cắt_Lỗ]</code>\n"
                f"💡 Ví dụ: <code>/chotlai 200000 100000</code>"
            )
            msg = BOX("🎯 CẤU HÌNH TAKE PROFIT / STOP LOSS", body, "gold")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
            return
        
        tp = int(p[1])
        sl = int(p[2])
        st["take_profit"] = tp
        st["stop_loss"] = sl
        
        body = (
            f"✅ <b>ĐÃ CẬP NHẬT CẤU HÌNH THÀNH CÔNG!</b>\n"
            f"══════════════\n"
            f"🎯 Mục Tiêu Chốt Lời: <b>+{fmt_money(tp)} VNĐ</b>\n"
            f"🛡️ Giới Hạn Cắt Lỗ: <b>-{fmt_money(sl)} VNĐ</b>\n"
            f"──────────────────────────\n"
            f"⚡ Bot sẽ tự động ngắt Auto Bet ngay khi đạt một trong hai điều kiện trên!"
        )
        msg = BOX("🎯 CHỐT LỜI / CẮT LỖ ĐÃ BẬT", body, "green")
        bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(cid))
    except Exception as e:
        bot.reply_to(m, f"❌ Cú pháp chưa đúng! Ví dụ: /chotlai 100000 50000")

@bot.message_handler(commands=['thongtin'])
def tt(m):
    try:
        cid = m.chat.id
        init_user_state(cid)
        
        if not check_auth(cid):
            bot.reply_to(m, "🔒 Vui lòng /nhapkey để kích hoạt bản quyền trước!")
            return
        
        st = user_states[cid]
        han = "👑 ADMIN VĨNH VIỄN" if cid == ADMIN_ID else format_expire_time(authorized_users[cid])
        x2 = f"🟢 BẬT (Cấp {st['martingale_level']})" if st.get("martingale_enabled", False) else "🔴 TẮT"
        auto = "🟢 BẬT" if st.get("auto_bet_enabled", False) else "🔴 TẮT"
        total = st["total_win"] + st["total_lose"]
        wr = (st["total_win"] / total) * 100 if total > 0 else 0
        net_pnl = st["balance"] - st["start_balance"] if st["start_balance"] > 0 else 0
        pnl_str = f"+{fmt_money(net_pnl)}" if net_pnl >= 0 else f"-{fmt_money(abs(net_pnl))}"

        body = (
            f"🆔 CHAT ID: <code>{cid}</code>\n"
            f"⏳ HẠN VIP: <b>{han}</b>\n"
            f"══════════════\n"
            f"⚡ AUTO BET: {auto}\n"
            f"💸 GẤP THẾP X2: {x2}\n"
            f"🎯 CHỐT LỜI: <b>+{fmt_money(st.get('take_profit', 100000))} VNĐ</b>\n"
            f"🛡️ CẮT LỖ: <b>-{fmt_money(st.get('stop_loss', 50000))} VNĐ</b>\n"
            f"──────────────────────────\n"
            f"💰 SỐ DƯ GAME: <b>{fmt_money(st['balance'])} VNĐ</b>\n"
            f"💵 TỔNG LỢI NHUẬN: <b>{pnl_str} VNĐ</b>\n"
            f"📊 TỈ LỆ THẮNG: <b>{wr:.1f}%</b> ({st['total_win']}W - {st['total_lose']}L)\n"
            f"🔥 WIN STREAK: {st['win_streak']} | 💀 LOSE STREAK: {st['lose_streak']}\n"
            f"📜 DỮ LIỆU CẦU: {len(st['history'])} PHIÊN"
        )
        msg = BOX("💎 THÔNG TIN TÀI KHOẢN VIP", body, "purple")
        bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
    except Exception as e:
        logger.error(f"Thongtin error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['lichsucau'])
@require_auth
def ls(m):
    try:
        st = user_states[m.chat.id]
        if not st["history"]:
            bot.reply_to(m, "📭 Chưa có dữ liệu lịch sử cầu!")
            return
        
        last = st["history"][-30:]
        s = "".join("🔵" if x == "TAI" else "🔴" for x in last[-20:])
        tai = st["history"].count("TAI")
        xiu = st["history"].count("XIU")
        total = max(1, tai + xiu)
        
        body = (
            f"🔵 TÀI: <b>{tai}</b> ({tai/total*100:.1f}%)\n"
            f"🔴 XỈU: <b>{xiu}</b> ({xiu/total*100:.1f}%)\n"
            f"📊 TỔNG SỐ PHIÊN: <b>{total}</b> PHIÊN\n"
            f"══════════════\n"
            f"📌 20 PHIÊN GẦN NHẤT:\n{s}"
        )
        msg = BOX("📊 PHÂN TÍCH LỊCH SỬ CẦU VIP", body, "blue")
        bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Lichsucau error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['login'])
@require_auth
def lg(m):
    try:
        p = m.text.split()
        if len(p) != 3:
            bot.reply_to(m, "⚠️ Cú pháp đăng nhập: /login TAIKHOAN MATKHAU")
            return
        
        mm = bot.reply_to(m, "🔄 Đang kết nối và xác thực máy chủ game...")
        res = login_and_get_token(p[1], p[2])
        
        if "_error" in res:
            bot.edit_message_text(f"❌ Lỗi: {res['_error']}", m.chat.id, mm.message_id)
            return
        
        init_user_state(m.chat.id)
        st = user_states[m.chat.id]
        st["balance"] = res["money"]
        st["start_balance"] = res["money"]
        st["peak_balance"] = res["money"]
        st["base_bet"] = st["bet_amount"]
        
        body = (
            f"📛 TÊN NHÂN VẬT: <b>{res['nickname']}</b>\n"
            f"💰 SỐ DƯ TÀI KHOẢN: <b>{fmt_money(res['money'])} VNĐ</b>\n"
            f"══════════════\n"
            f"🟢 WEBSOCKET: ĐÃ KẾT NỐI REALTIME\n"
            f"🧠 ALGO QUANT-v5.5 BẮT BẺ CHU KỲ SẴN SÀNG"
        )
        msg = BOX("✅ ĐĂNG NHẬP THÀNH CÔNG VIP", body, "green")
        bot.edit_message_text(
            f"<pre>{msg}</pre>",
            m.chat.id,
            mm.message_id,
            parse_mode="HTML",
            reply_markup=vip_menu(m.chat.id)
        )
        
        threading.Thread(
            target=start_websocket,
            args=(m.chat.id, res["token"]),
            daemon=True
        ).start()
    except Exception as e:
        logger.error(f"Login error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['autobet'])
@require_auth
def ab(m):
    try:
        cid = m.chat.id
        if cid not in active_sockets:
            bot.reply_to(m, "⚠️ Bạn cần đăng nhập tài khoản trước: /login TK MK")
            return
        
        p = m.text.split()
        if len(p) < 2:
            bot.reply_to(m, "⚠️ Cú pháp: /autobet on 10000 | /autobet off")
            return
        
        st = user_states[cid]
        if p[1].lower() == "on":
            amt = int(p[2]) if len(p) > 2 else 10000
            st["auto_bet_enabled"] = True
            st["bet_amount"] = amt
            st["base_bet"] = amt
            st["martingale_level"] = 0
            st["cooldown"] = 0
            
            if st["start_balance"] <= 0:
                st["start_balance"] = st["balance"]
            
            body = (
                f"⚡ AUTO BET: <b>ĐÃ BẬT ✅</b>\n"
                f"💰 CƯỢC/PHIÊN: <b>{fmt_money(amt)} VNĐ</b>\n"
                f"🎯 CHỐT LỜI: <b>+{fmt_money(st.get('take_profit', 100000))} VNĐ</b>\n"
                f"🛡️ CẮT LỖ: <b>-{fmt_money(st.get('stop_loss', 50000))} VNĐ</b>\n"
                f"──────────────────────────\n"
                f"⏳ Chạy tự động liên tục cho đến khi đạt Target hoặc bấm Dừng!"
            )
            msg = BOX("🟢 TỰ ĐỘNG ĐẶT CƯỢC VIP", body, "green")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
        else:
            st["auto_bet_enabled"] = False
            msg = BOX("🔴 AUTO BET VIP", "⚡ ĐÃ TẮT TỰ ĐỘNG ĐẶT CƯỢC AN TOÀN", "red")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
    except Exception as e:
        logger.error(f"Autobet error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['x2'])
@require_auth
def cmd_x2(m):
    try:
        cid = m.chat.id
        st = user_states[cid]
        p = m.text.split()
        
        if len(p) < 2:
            tt = f"🟢 BẬT (Cấp {st['martingale_level']})" if st.get("martingale_enabled", False) else "🔴 TẮT"
            body = (
                f"TRẠNG THÁI GẤP THẾP: <b>{tt}</b>\n"
                f"MỨC CƯỢC GỐC: <b>{fmt_money(st['base_bet'])} VNĐ</b>\n"
                f"MỨC TỐI ĐA: <b>{MAX_MARTINGALE_LEVEL} CẤP (X2)</b>\n"
                f"──────────────────────────\n"
                f"👉 Bật/Tắt: /x2 on | /x2 off"
            )
            msg = BOX("💸 GẤP THẾP MARTINGALE VIP", body, "gold")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
            return
        
        if p[1].lower() == "on":
            st["martingale_enabled"] = True
            st["martingale_level"] = 0
            body = (
                f"✅ ĐÃ BẬT CHẾ ĐỘ X2 GẤP THẾP VIP\n"
                f"THUA → TỰ ĐỘNG NHÂN {MARTINGALE_MULTIPLIER}X\n"
                f"THẮNG → DỪNG VÀ RESET VỀ MỨC GỐC\n"
                f"🛡️ GIỚI HẠN AN TOÀN TỐI ĐA: {MAX_MARTINGALE_LEVEL} CẤP"
            )
            msg = BOX("💸 GẤP THẾP VIP BẬT", body, "green")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
        else:
            st["martingale_enabled"] = False
            st["martingale_level"] = 0
            msg = BOX("💸 GẤP THẾP VIP", "🔴 ĐÃ TẮT → TRỞ VỀ MỨC CƯỢC ĐƠN GỐC", "red")
            bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML", reply_markup=vip_menu(m.chat.id))
    except Exception as e:
        logger.error(f"X2 error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['stop'])
@require_auth
def sp(m):
    try:
        cid = m.chat.id
        if cid in active_sockets:
            try:
                active_sockets[cid].disconnect()
            except Exception:
                pass
            del active_sockets[cid]
        
        st = user_states[cid]
        st["auto_bet_enabled"] = False
        st["martingale_enabled"] = False
        st["martingale_level"] = 0
        st["cooldown"] = 0
        
        body = (
            f"✅ Đã đóng kết nối WebSocket an toàn!\n"
            f"✅ Đã dừng tính năng Auto Bet tự động!\n"
            f"✅ Đã tắt gấp thếp và reset level cược!\n"
            f"🛡️ Hệ thống bảo vệ hoàn tất thành công."
        )
        msg = BOX("⏹️ DỪNG HỆ THỐNG AN TOÀN", body, "red")
        bot.reply_to(m, f"<pre>{msg}</pre>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Stop error: {e}")
        bot.reply_to(m, f"❌ Lỗi: {str(e)}")

# =========================
# CALLBACK HANDLER
# =========================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    try:
        cid = c.message.chat.id
        init_user_state(cid)
        st = user_states[cid]
        d = c.data

        if not check_auth(cid):
            bot.answer_callback_query(c.id, "🔒 Vui lòng nhập key VIP để sử dụng!", show_alert=True)
            return

        if d == "login":
            bot.answer_callback_query(c.id)
            send_card(cid, "KẾT NỐI TÀI KHOẢN GAME",
                      "🔐 Nhập cú pháp đính kèm:\n👉 /login TAIKHOAN MATKHAU\n─\n🛡️ Lưu ý: Khuyến nghị xoá tin nhắn chứa mật khẩu sau khi đăng nhập.",
                      "blue")
            return

        if d == "auto_toggle":
            if cid not in active_sockets:
                bot.answer_callback_query(c.id, "⚠️ Cần đăng nhập tài khoản (/login) trước!", show_alert=True)
                return
            st["auto_bet_enabled"] = not st.get("auto_bet_enabled", False)
            if st["auto_bet_enabled"]:
                st["martingale_level"] = 0
                if st["start_balance"] <= 0:
                    st["start_balance"] = st["balance"]
            bot.answer_callback_query(
                c.id, "⚡ AUTO BET: BẬT ✅" if st["auto_bet_enabled"] else "⏸️ AUTO BET: TẮT 🔴")

        elif d == "x2_toggle":
            st["martingale_enabled"] = not st.get("martingale_enabled", False)
            st["martingale_level"] = 0
            bot.answer_callback_query(
                c.id, "💸 GẤP THẾP X2: BẬT ✅" if st["martingale_enabled"] else "💸 GẤP THẾP X2: TẮT 🔴")

        elif d == "chotlai_info":
            bot.answer_callback_query(c.id)
            send_card(cid, "🎯 HƯỚNG DẪN CÀI CHỐT LỜI / CẮT LỖ", (
                f"💎 Chốt Lời Hiện Tại: +{fmt_money(st.get('take_profit', 100000))} VNĐ\n"
                f"🛡️ Cắt Lỗ Hiện Tại: -{fmt_money(st.get('stop_loss', 50000))} VNĐ\n──────────────\n"
                f"👉 Đặt target mới: /chotlai [Tiền_Lời] [Tiền_Lỗ]\n"
                f"Ví dụ: /chotlai 200000 100000"
            ), "gold")
            return

        elif d == "ls":
            bot.answer_callback_query(c.id)
            hist = st["history"]
            if not hist:
                send_card(cid, "LỊCH SỬ CẦU VIP", "📭 Chưa thu thập đủ dữ liệu phiên", "blue")
                return
            tai, xiu = hist.count("TAI"), hist.count("XIU")
            total = max(tai + xiu, 1)
            s = "".join("🔵" if x == "TAI" else "🔴" for x in hist[-20:])
            send_card(cid, "LỊCH SỬ CẦU VIP", (
                f"🔵 TÀI: {tai} ({tai/total*100:.1f}%)\n"
                f"🔴 XỈU: {xiu} ({xiu/total*100:.1f}%)\n──────────────\n"
                f"📌 20 PHIÊN GẦN NHẤT:\n{s}"
            ), "blue")
            return

        elif d == "tt":
            bot.answer_callback_query(c.id)
            total = st["total_win"] + st["total_lose"]
            wr = (st["total_win"] / total) * 100 if total else 0
            han = "👑 VĨNH VIỄN" if cid == ADMIN_ID else format_expire_time(authorized_users.get(cid, 0))
            net_pnl = st["balance"] - st["start_balance"] if st["start_balance"] > 0 else 0
            pnl_str = f"+{fmt_money(net_pnl)}" if net_pnl >= 0 else f"-{fmt_money(abs(net_pnl))}"
            send_card(cid, "TÀI KHOẢN VIP PRO MAX", (
                f"🆔 CHAT ID: {cid}\n⏳ THỜI HẠN: {han}\n──────────────\n"
                f"💰 SỐ DƯ GAME: {fmt_money(st['balance'])} VNĐ\n"
                f"💵 LỢI NHUẬN: {pnl_str} VNĐ\n"
                f"🎯 CỰC CƯỢC GỐC: {fmt_money(st['base_bet'])} VNĐ\n──────────────\n"
                f"✅ Thắng: {st['total_win']}  ❌ Thua: {st['total_lose']}  📈 Winrate: {wr:.1f}%\n"
                f"BAR: {bar(wr)}\n"
                f"🔥 Win Streak: {st['win_streak']}  💀 Lose Streak: {st['lose_streak']}"
            ), "purple", vip_menu(cid))
            return

        elif d == "hd":
            bot.answer_callback_query(c.id)
            send_card(cid, "HƯỚNG DẪN VIP", (
                "🔑 /nhapkey KEY - Nhập mã VIP\n"
                "🔐 /login TK MK - Đăng nhập Game\n"
                "⚡ /autobet on [MỨC] | off - Tự động cược\n"
                "🎯 /chotlai [CHỐT_LỜI] [CẮT_LỖ] - Đặt Target\n"
                "💸 /x2 on | off - Bật/tắt gấp thếp\n"
                "📊 /lichsucau - Xem cầu 3D\n"
                "💎 /thongtin - Xem số dư & VIP\n"
                "⏹️ /stop - Ngắt an toàn"
            ), "gold")
            return

        elif d == "stop":
            if cid in active_sockets:
                try:
                    active_sockets[cid].disconnect()
                except Exception:
                    pass
                del active_sockets[cid]
            st["auto_bet_enabled"] = False
            st["martingale_enabled"] = False
            st["martingale_level"] = 0
            bot.answer_callback_query(c.id, "⏹️ Hệ thống đã ngắt kết nối an toàn!")

        else:
            bot.answer_callback_query(c.id, "♻️ Bảng điều khiển đã được làm mới!")

        # Cập nhật lại Bảng điều khiển trực tiếp trên tin nhắn hiện tại
        auto = "🟢 BẬT" if st.get("auto_bet_enabled") else "🔴 TẮT"
        x2 = f"🟢 BẬT (Cấp {st['martingale_level']})" if st.get("martingale_enabled") else "🔴 TẮT"
        link = "🟢 ĐÃ KẾT NỐI" if cid in active_sockets else "🔴 CHƯA KẾT NỐI"
        net_pnl = st["balance"] - st["start_balance"] if st["start_balance"] > 0 else 0
        pnl_str = f"+{fmt_money(net_pnl)}" if net_pnl >= 0 else f"-{fmt_money(abs(net_pnl))}"
        try:
            bot.edit_message_text(
                card("BẢNG ĐIỀU KHIỂN VIP PRO MAX", (
                    f"🔌 WEBSOCKET GAME: <b>{link}</b>\n──────────────\n"
                    f"⚡ AUTO BET: <b>{auto}</b>\n"
                    f"💸 GẤP THẾP X2: <b>{x2}</b>\n"
                    f"🎯 CHỐT LỜI: <b>+{fmt_money(st.get('take_profit', 100000))} VNĐ</b>\n"
                    f"🛡️ CẮT LỖ: <b>-{fmt_money(st.get('stop_loss', 50000))} VNĐ</b>\n"
                    f"💰 MỨC CƯỢC/PHIÊN: <b>{fmt_money(st['bet_amount'])} VNĐ</b>\n"
                    f"📈 SỐ DƯ TÀI KHOẢN: <b>{fmt_money(st['balance'])} VNĐ</b> ({pnl_str})"
                ), "gold"),
                cid, c.message.message_id,
                parse_mode="HTML", reply_markup=vip_menu(cid),
            )
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Callback error: {e}")

# =========================
# KHỞI CHẠY CHÍNH (MAIN)
# =========================
if __name__ == "__main__":
    try:
        # Chạy Web Server Keep-Alive
        web_thread = threading.Thread(target=run_web, daemon=True)
        web_thread.start()
        time.sleep(2)
        
        logger.info("👑 LC79 ELITE PRO MAX v5.5 | FAST CYCLE PULSE ENGINE STARTED")
        logger.info(f"Bot token: {BOT_TOKEN[:10]}...")
        
        # Vòng lặp Polling với tự động Retry
        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"Bot polling error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(10)
                
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())