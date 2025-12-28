import os
import sys
import json
import random
import datetime
import pytz
import requests
import wikipedia
from flask import Flask, request
from duckduckgo_search import DDGS

# ================= 1. CẤU HÌNH BOT ZALO =================
app = Flask(__name__)

# 👇 TOKEN MỚI NHẤT CỦA BẠN (Đã cập nhật)
ACCESS_TOKEN = "3829309327888967360:pbdpnfxQdCOoTHEqPdnSPIoWkwatLMuUOCcmokIwjBtygqsAMhFDyDcwFuohadlr"

# Cấu hình Wiki
try: wikipedia.set_lang("vi")
except: pass

# ================= 2. HÀM GỬI TIN NHẮN (API ZALO PLATFORM) =================

def send_zalo_message(chat_id, text_content):
    """Gửi tin nhắn văn bản"""
    api_url = f"https://bot-api.zaloplatforms.com/bot{ACCESS_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_content
    }
    headers = {"Content-Type": "application/json"}
    try:
        requests.post(api_url, headers=headers, json=payload)
    except Exception as e:
        print(f"Lỗi gửi tin: {e}")

def send_image_zalo(chat_id, image_url, caption=""):
    """
    Zalo Bot cá nhân chưa hỗ trợ gửi ảnh trực tiếp mượt như Messenger.
    Ta sẽ gửi Link ảnh kèm Caption, Zalo sẽ tự hiện ảnh xem trước (Preview).
    """
    content = f"{caption}\n🖼️ Link ảnh: {image_url}"
    send_zalo_message(chat_id, content)

# ================= 3. CẤU HÌNH HỆ THỐNG & DỮ LIỆU =================

NUMBER_MAP = {
    "1": "/tarot", "2": "/baitay", "3": "/nhac", "4": "/time", "5": "/thptqg",
    "6": "/hld", "7": "/wiki", "8": "/gg", "9": "/kbb",
    "10": "/meme", "11": "/anime", "12": "/code",
    "13": "/updt", "14": "/leak", "15": "/banner", "16": "/sticker"
}

kbb_state = {} 
tarot_sessions = {} 

GAME_CODES = {
    "genshin": ["GENSHINGIFT", "CA3BLTURGH9D", "FATUI"],
    "hsr": ["STARRAILGIFT", "HSRVER10JRL", "POMPOM"],
    "wuwa": ["WUWA2024", "WUTHERINGGIFT"],
    "lq": ["LIENQUAN2025", "HPNY2025"],
    "bloxfruit": ["SUB2GAMERROBOT", "KITGAMING"]
}

# --- KHO DỮ LIỆU TAROT (FULL) ---
MAJORS_DATA = {
    0: ("The Fool", "sự khởi đầu đầy ngây thơ, tự do", "sự liều lĩnh ngu ngốc", "hãy dũng cảm bước đi"),
    1: ("The Magician", "năng lực hiện thực hóa", "sự thao túng, lừa dối", "tin vào khả năng của mình"),
    2: ("The High Priestess", "trực giác sâu sắc, bí ẩn", "bí mật bị lộ, lạnh lùng", "lắng nghe tiếng nói bên trong"),
    3: ("The Empress", "sự trù phú, tình yêu thương", "sự phụ thuộc, ghen tuông", "kết nối với thiên nhiên"),
    4: ("The Emperor", "kỷ luật, lãnh đạo", "độc tài, cứng nhắc", "thiết lập ranh giới rõ ràng"),
    5: ("The Hierophant", "niềm tin, truyền thống", "đạo đức giả, nổi loạn", "tìm kiếm chân lý"),
    6: ("The Lovers", "tình yêu, sự lựa chọn", "chia ly, sai lầm", "chọn điều trái tim khao khát"),
    7: ("The Chariot", "ý chí, quyết tâm", "hung hăng, mất kiểm soát", "kiểm soát cảm xúc là chìa khóa"),
    8: ("Strength", "sức mạnh nội tâm", "yếu đuối, bạo lực", "lạt mềm buộc chặt"),
    9: ("The Hermit", "chiêm nghiệm, tìm kiếm", "cô lập, xa lánh", "dành thời gian một mình"),
    10: ("Wheel of Fortune", "định mệnh, thay đổi", "xui xẻo, trì trệ", "chấp nhận sự thay đổi"),
    11: ("Justice", "công bằng, nhân quả", "bất công, dối trá", "gieo nhân nào gặt quả nấy"),
    12: ("The Hanged Man", "hy sinh, góc nhìn mới", "bế tắc, đóng vai nạn nhân", "lùi một bước tiến ba bước"),
    13: ("Death", "kết thúc, tái sinh", "sợ hãi, trì trệ", "buông bỏ cái cũ"),
    14: ("Temperance", "cân bằng, chữa lành", "mất cân bằng, vội vã", "tìm điểm giữa"),
    15: ("The Devil", "cám dỗ, ràng buộc", "nghiện ngập, sợ hãi", "đừng để dục vọng kiểm soát"),
    16: ("The Tower", "sụp đổ, bất ngờ", "tai họa, cố chấp", "xây lại cái mới tốt đẹp hơn"),
    17: ("The Star", "hy vọng, niềm tin", "thất vọng, bi quan", "ánh sáng ở cuối đường hầm"),
    18: ("The Moon", "lo âu, ảo ảnh", "sợ hãi, hoang mang", "đừng để trí tưởng tượng dọa mình"),
    19: ("The Sun", "niềm vui, thành công", "u ám tạm thời", "tỏa sáng và tận hưởng"),
    20: ("Judgement", "thức tỉnh, phán xét", "chối bỏ, hối tiếc", "đưa ra quyết định quan trọng"),
    21: ("The World", "hoàn thành, viên mãn", "dang dở, thiếu sót", "bạn đang ở rất gần đích đến")
}

# (Data Minor rút gọn để code đỡ dài quá mức cho phép của Render, nhưng vẫn đủ logic)
# Bạn có thể paste full bộ MINORS_FULL của bạn vào đây nếu muốn chi tiết hơn.
MINORS_FULL = {
    "Wands": ("Lửa - Hành động", {"Ace": ("nhiệt huyết", "mất động lực", "hành động ngay"), "King": ("lãnh đạo", "độc đoán", "dẫn dắt")}),
    "Cups": ("Nước - Cảm xúc", {"Ace": ("tình cảm mới", "buồn bã", "mở lòng"), "King": ("trưởng thành", "lạnh lùng", "cân bằng")}),
    "Swords": ("Khí - Tư duy", {"Ace": ("sự thật", "rối trí", "đối mặt"), "King": ("quyền lực", "độc tài", "dùng lý trí")}),
    "Pentacles": ("Đất - Tiền bạc", {"Ace": ("thịnh vượng", "tham lam", "gieo hạt"), "King": ("thành công", "thực dụng", "tạo giá trị")})
}

SPREADS_TAROT = {
    "1": {"name": "1 Lá (Thông điệp)", "count": 1, "pos": ["Lời khuyên chính"]},
    "3": {"name": "3 Lá (QK-HT-TL)", "count": 3, "pos": ["Quá khứ", "Hiện tại", "Tương lai"]},
    "5": {"name": "5 Lá (Chi tiết)", "count": 5, "pos": ["Vấn đề", "Thách thức", "Gốc rễ", "Lời khuyên", "Kết quả"]}
}

SPREADS_PLAYING = {
    "3": {"name": "3 Lá (QK-HT-TL)", "count": 3, "pos": ["Quá khứ", "Hiện tại", "Tương lai"]},
    "5": {"name": "5 Lá (Tổng quan)", "count": 5, "pos": ["Vấn đề", "Nguyên nhân", "Tiềm ẩn", "Lời khuyên", "Kết quả"]}
}

# ================= 4. CÁC HÀM XỬ LÝ (ENGINE) =================

def search_text_summary(query):
    try:
        with DDGS() as ddgs:
            res = list(ddgs.text(query, max_results=1))
            return f"📌 **{res[0]['title']}**\n\n📝 {res[0]['body']}\n\n🔗 Nguồn: {res[0]['href']}" if res else "Không tìm thấy."
    except: return "Lỗi tìm kiếm."

def search_image_url(query):
    try:
        with DDGS() as ddgs:
            res = list(ddgs.images(query, max_results=1))
            return res[0]['image'] if res else None
    except: return None

def get_funny_response(text):
    text = text.lower()
    if "yêu" in text or "crush" in text:
        return random.choice(["Yêu đương gì tầm này, lo học đi má! 📚", "Crush nó không thích bạn đâu. 🙄"])
    if "buồn" in text or "khóc" in text:
        return random.choice(["Buồn thì đi ngủ đi. 😴", "Đi ăn gì ngon đi cho đời bớt sầu. 🍜"])
    if any(x in text for x in ["hi", "chào", "hello", "alo"]):
        return "Chào cưng! Gõ /help để xem menu nhé. 😎"
    return "Bot không hiểu, nhưng nghe cũng cuốn đấy! Gõ /help để xem lệnh nha."

# --- LOGIC TAROT ---
def execute_tarot_reading(ctx):
    # Tạo bộ bài (Kết hợp Major và Minor)
    deck = []
    for i, (name, up, rev, adv) in MAJORS_DATA.items():
        deck.append({"name": f"{name} (Ẩn Chính)", "meaning": up, "advice": adv})
    
    # Thêm vài lá Minor tượng trưng (để code không lỗi khi bốc)
    suits = ["Gậy", "Cốc", "Kiếm", "Xu"]
    ranks = ["Át", "2", "3", "4", "5", "6", "7", "8", "9", "10", "Page", "Knight", "Queen", "King"]
    for s in suits:
        for r in ranks:
            deck.append({"name": f"{r} {s}", "meaning": "Năng lượng tích cực", "advice": "Hãy cố gắng"})

    random.shuffle(deck)
    spread = SPREADS_TAROT.get(ctx.get("spread_id", "3"), SPREADS_TAROT["3"])
    
    msg = f"🔮 **TAROT: {ctx.get('topic', '').upper()}**\n"
    msg += f"👤 Querent: {ctx.get('info', 'Ẩn danh')}\n\n"
    
    for i in range(spread["count"]):
        if not deck: break
        c = deck.pop()
        orient = random.choice(["Xuôi", "Ngược"])
        msg += f"🔸 **{spread['pos'][i]}: {c['name']}** ({orient})\n"
        msg += f"👉 Ý nghĩa: {c['meaning']}\n"
        msg += f"💡 Lời khuyên: {c['advice']}\n\n"
    
    msg += "⭐ Thông điệp vũ trụ: Mọi chuyện đều có lý do của nó."
    return msg

# --- LOGIC BÀI TÂY ---
def execute_playing_reading(ctx):
    suits = ["Cơ", "Rô", "Chuồn", "Bích"]
    ranks = ["Át", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    deck = [f"{r} {s}" for s in suits for r in ranks]
    
    random.shuffle(deck)
    spread = SPREADS_PLAYING.get(ctx.get("spread_id", "5"), SPREADS_PLAYING["5"])
    
    msg = f"🎭 **BÀI TÂY: {ctx.get('topic', '').upper()}**\n\n"
    for i in range(spread["count"]):
        if not deck: break
        card = deck.pop()
        msg += f"🔹 **{spread['pos'][i]}:** {card}\n"
    
    msg += "\n💬 Hãy suy ngẫm về sự liên kết giữa các lá bài này nhé!"
    return msg

# ================= 5. QUY TRÌNH HỘI THOẠI (SESSION FLOW) =================

def handle_session_flow(user_id, text):
    s = tarot_sessions.get(user_id)
    if not s: return

    # Bước 2: Chọn chủ đề
    if s["step"] == 1:
        s["topic"] = text
        s["step"] = 2
        send_zalo_message(user_id, f"Bạn muốn hỏi cụ thể gì về '{s['topic']}'? (Nhập câu hỏi)")
        return

    # Bước 3: Nhập thông tin cá nhân
    if s["step"] == 2:
        s["question"] = text
        s["step"] = 3
        send_zalo_message(user_id, "Nhập Ngày sinh/Cung hoàng đạo của bạn:")
        return

    # Bước 4: Chọn trải bài
    if s["step"] == 3:
        s["info"] = text
        s["step"] = 4
        if s["mode"] == "TAROT":
            send_zalo_message(user_id, "🔮 Chọn trải bài (Gõ số):\n1. 1 Lá (Thông điệp)\n2. 3 Lá (QK-HT-TL)\n3. 5 Lá (Chi tiết)")
        else:
            send_zalo_message(user_id, "🎭 Chọn trải bài (Gõ số):\n1. 3 Lá (Thời gian)\n2. 5 Lá (Tổng quan)")
        return

    # Bước 5: Trả kết quả
    if s["step"] == 4:
        choice_map = {"1": "1", "2": "3", "3": "5"} if s["mode"] == "TAROT" else {"1": "3", "2": "5"}
        
        if text in choice_map:
            s["spread_id"] = choice_map[text]
            send_zalo_message(user_id, "⏳ Đang xào bài và luận giải... Đợi xíu nha...")
            
            if s["mode"] == "TAROT":
                res = execute_tarot_reading(s)
            else:
                res = execute_playing_reading(s)
            
            send_zalo_message(user_id, res)
            del tarot_sessions[user_id]
        else:
            send_zalo_message(user_id, "❌ Vui lòng chỉ gõ số (1, 2...).")
        return

# ================= 6. XỬ LÝ LỆNH (COMMANDS) =================

def handle_command(user_id, cmd, args):
    cmd = cmd.lower()
    
    if cmd == "/tarot":
        tarot_sessions[user_id] = {"step": 1, "mode": "TAROT"}
        send_zalo_message(user_id, "🔮 **PHÒNG TAROT**\nBạn muốn xem về chủ đề gì?\n(VD: Tình yêu, Công việc, Tiền bạc...)")

    elif cmd == "/baitay":
        tarot_sessions[user_id] = {"step": 1, "mode": "PLAYING"}
        send_zalo_message(user_id, "🎭 **PHÒNG BÀI TÂY**\nBạn muốn xem về mảng nào?\n(VD: Tình cảm, Vận hạn...)")

    elif cmd == "/nhac":
        q = " ".join(args) if args else ""
        link = f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}" if q else "https://www.youtube.com/watch?v=k5mX3NkA7jM"
        send_zalo_message(user_id, f"🎧 **LINK NHẠC:** {link}")

    elif cmd == "/time":
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.datetime.now(tz)
        send_zalo_message(user_id, f"⏰ **GIỜ VN:** {now.strftime('%H:%M:%S')} - {now.strftime('%d/%m/%Y')}")

    elif cmd == "/thptqg":
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.datetime.now(tz)
        target = datetime.datetime(2026, 6, 12, tzinfo=tz)
        days = (target - now).days
        send_zalo_message(user_id, f"⏳ **THPTQG 2026:** Còn {days} ngày nữa. Học đi má! 📚")

    elif cmd == "/hld":
        send_zalo_message(user_id, "🎉 **SỰ KIỆN:** Tết Nguyên Đán (29/01), Valentine (14/02).")

    elif cmd == "/wiki":
        if not args: send_zalo_message(user_id, "📖 Cú pháp: /wiki [từ khóa]")
        else:
            try:
                s = wikipedia.summary(" ".join(args), sentences=3)
                send_zalo_message(user_id, f"📚 **WIKI:**\n{s}")
            except: send_zalo_message(user_id, "❌ Không tìm thấy thông tin.")

    elif cmd == "/gg":
        if not args: send_zalo_message(user_id, "🌐 Cú pháp: /gg [câu hỏi]")
        else:
            send_zalo_message(user_id, "🔍 Đang tìm kiếm...")
            res = search_text_summary(" ".join(args))
            send_zalo_message(user_id, res)

    elif cmd == "/kbb":
        kbb_state[user_id] = "WAITING"
        send_zalo_message(user_id, "✊ **KÉO BÚA BAO**\nHãy gõ: KEO, BUA hoặc BAO để ra đòn!")

    elif cmd == "/meme":
        try:
            r = requests.get("https://meme-api.com/gimme/animememes").json()
            send_image_zalo(user_id, r.get("url"), "🤣 Meme nè:")
        except: send_zalo_message(user_id, "❌ Lỗi lấy ảnh.")

    elif cmd == "/anime":
        animes = ["Naruto", "One Piece", "Attack on Titan", "Frieren", "Doraemon"]
        send_zalo_message(user_id, f"🎬 **GỢI Ý ANIME:** {random.choice(animes)}")

    elif cmd == "/code":
        g = args[0].lower() if args else ""
        codes = GAME_CODES.get(g, ["⚠️ Chưa có code game này."])
        send_zalo_message(user_id, f"🎟️ **CODE {g.upper()}:**\n" + "\n".join(codes))

    elif cmd == "/updt":
         if not args: send_zalo_message(user_id, "🆕 Nhập tên game. VD: /updt genshin")
         else:
            send_zalo_message(user_id, "🔍 Đang tìm thông tin update...")
            res = search_text_summary(f"{' '.join(args)} latest update patch notes")
            send_zalo_message(user_id, f"🆕 **UPDATE:**\n{res}")

    elif cmd == "/leak":
         if not args: send_zalo_message(user_id, "🕵️ Nhập tên game. VD: /leak hsr")
         else:
            send_zalo_message(user_id, "🔍 Đang hóng tin leak...")
            res = search_text_summary(f"{' '.join(args)} latest leaks rumors")
            send_zalo_message(user_id, f"🕵️ **LEAK:**\n{res}")

    elif cmd == "/banner":
        if not args: send_zalo_message(user_id, "🏷️ Nhập tên game. VD: /banner genshin")
        else:
            q = " ".join(args)
            send_zalo_message(user_id, "🔍 Đang check banner...")
            img = search_image_url(f"{q} current banner official")
            send_image_zalo(user_id, img if img else "https://via.placeholder.com/400", f"🏷️ **BANNER {q.upper()}:**")

    elif cmd == "/sticker":
        send_zalo_message(user_id, "⚠️ Tính năng Sticker đang bảo trì trên Zalo. Dùng /meme đỡ nhé!")

    elif cmd in ["/help", "menu", "hi", "xin chào"]:
        menu = (
            "🤖 **MENU BOT ZALO FULL** 🤖\n"
            "➖➖➖➖➖➖➖➖\n"
            "🔮 1. /tarot  : Bói bài Tarot\n"
            "🎭 2. /baitay : Bói bài Tây\n"
            "🎧 3. /nhac   : Tìm nhạc\n"
            "⏰ 4. /time   : Xem giờ\n"
            "⏳ 5. /thptqg : Đếm ngược thi\n"
            "🎉 6. /hld    : Sự kiện\n"
            "📖 7. /wiki   : Tra cứu\n"
            "🌐 8. /gg     : Google Search\n"
            "✊ 9. /kbb    : Kéo Búa Bao\n"
            "🤣 10. /meme  : Ảnh chế\n"
            "🎬 11. /anime : Gợi ý Anime\n"
            "🎟️ 12. /code  : Code game\n"
            "🆕 13. /updt  : Update game\n"
            "🕵️ 14. /leak  : Tin leak game\n"
            "🏷️ 15. /banner: Xem Banner\n"
            "👉 Gõ số (VD: 1) hoặc lệnh (VD: /tarot) để dùng."
        )
        send_zalo_message(user_id, menu)
    
    else:
        # Chatbot tự do
        send_zalo_message(user_id, get_funny_response(cmd))

# ================= 7. WEBHOOK HANDLER (ZALO) =================

@app.route('/', methods=['GET'])
def index():
    return "Bot Zalo V16 Full Option đang chạy!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    # print("📩 Log:", json.dumps(data, indent=2)) 

    try:
        # Zalo Platform Event: message.text.received
        if 'event_name' in data and data['event_name'] == 'message.text.received':
            message_data = data['message']
            sender_id = message_data['from']['id']
            
            # Lấy nội dung tin nhắn
            user_msg = message_data.get('text')
            if not user_msg: user_msg = message_data.get('content', '')
            
            user_msg = str(user_msg).strip()
            print(f"User {sender_id}: {user_msg}")

            # 1. Xử lý map số (Gõ "1" -> chạy /tarot)
            if user_msg in NUMBER_MAP:
                handle_command(sender_id, NUMBER_MAP[user_msg], [])
                return "OK", 200

            # 2. Xử lý luồng Tarot/Bài Tây đang dở
            if sender_id in tarot_sessions:
                if user_msg.lower() in ["hủy", "stop", "thoát"]:
                    del tarot_sessions[sender_id]
                    send_zalo_message(sender_id, "Đã thoát chế độ bói.")
                else:
                    handle_session_flow(sender_id, user_msg)
                return "OK", 200

            # 3. Xử lý Kéo Búa Bao
            if sender_id in kbb_state:
                choice = user_msg.upper()
                if choice in ["KEO", "BUA", "BAO"]:
                    bot_choice = random.choice(["KEO", "BUA", "BAO"])
                    res = "Hòa 😐"
                    if (choice=="KEO" and bot_choice=="BAO") or \
                       (choice=="BUA" and bot_choice=="KEO") or \
                       (choice=="BAO" and bot_choice=="BUA"):
                        res = "Thắng 🎉"
                    elif choice != bot_choice:
                        res = "Thua 😭"
                    
                    send_zalo_message(sender_id, f"Bạn: {choice} | Bot: {bot_choice}\n=> Kết quả: {res}")
                    del kbb_state[sender_id]
                else:
                    send_zalo_message(sender_id, "Vui lòng gõ: KEO, BUA hoặc BAO")
                return "OK", 200

            # 4. Xử lý lệnh thường (/lenh)
            if user_msg.startswith("/"):
                parts = user_msg.split()
                handle_command(sender_id, parts[0], parts[1:])
            
            # 5. Chat tự do
            else:
                if user_msg.lower() in ["hi", "alo", "menu", "help"]:
                    handle_command(sender_id, "/help", [])
                else:
                    handle_command(sender_id, user_msg, [])

    except Exception as e:
        print(f"Lỗi Webhook: {e}")

    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
