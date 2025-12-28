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
from google import genai
from groq import Groq # Thư viện Groq

# ================= 1. CẤU HÌNH BOT (BẢO MẬT 100%) =================
app = Flask(__name__)

# LẤY TOÀN BỘ KEY TỪ RENDER (KHÔNG HARD-CODE)
ACCESS_TOKEN = os.environ.get("ZALO_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Cấu hình Wiki
try: wikipedia.set_lang("vi")
except: pass

# ================= 2. HÀM GỬI TIN & ẢNH =================

def send_zalo_message(chat_id, text_content):
    if not ACCESS_TOKEN:
        print("⚠️ Lỗi: Chưa cấu hình ZALO_ACCESS_TOKEN trên Render!")
        return
        
    api_url = f"https://bot-api.zaloplatforms.com/bot{ACCESS_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text_content}
    headers = {"Content-Type": "application/json"}
    try: requests.post(api_url, headers=headers, json=payload)
    except Exception as e: print(f"Lỗi gửi tin: {e}")

def send_image_zalo(chat_id, image_url, caption=""):
    if not ACCESS_TOKEN: return

    api_url = f"https://bot-api.zaloplatforms.com/bot{ACCESS_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "message": {
            "text": caption,
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "media",
                    "elements": [{
                        "media_type": "image",
                        "url": image_url
                    }]
                }
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    try:
        r = requests.post(api_url, headers=headers, json=payload)
        if r.status_code != 200: send_zalo_message(chat_id, f"{caption}\nLink: {image_url}")
    except: send_zalo_message(chat_id, f"{caption}\nLink: {image_url}")

# ================= 3. CÁC MÔ HÌNH AI =================

def ask_chatgpt(question):
    """OpenAI (GPT-3.5)"""
    if not OPENAI_API_KEY: return "⚠️ Admin chưa nhập Key OpenAI trên Server."
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"}
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 800
    }
    try:
        r = requests.post(url, headers=headers, json=data)
        if r.status_code == 200: return r.json()['choices'][0]['message']['content']
        return "⚠️ OpenAI hết hạn mức hoặc lỗi Key."
    except: return "Lỗi kết nối OpenAI."

def ask_gemini(question):
    """Google Gemini"""
    if not GEMINI_API_KEY: return "⚠️ Admin chưa nhập Key Gemini trên Server."
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model="gemini-1.5-flash", contents=question)
        return response.text
    except Exception as e: return f"⚠️ Lỗi Gemini: {str(e)}"

def ask_groq(question):
    """Groq (Llama 3 - Siêu nhanh)"""
    if not GROQ_API_KEY: return "⚠️ Admin chưa nhập Key Groq trên Server."
    try:
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": question}],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False,
            stop=None,
        )
        return completion.choices[0].message.content
    except Exception as e: return f"⚠️ Lỗi Groq: {str(e)}"

# ================= 4. CÔNG CỤ TÌM KIẾM =================

def search_text_summary(query):
    try:
        with DDGS() as ddgs:
            res = list(ddgs.text(query, max_results=1))
            return f"📌 **{res[0]['title']}**\n\n📝 {res[0]['body']}\n\n🔗 Nguồn: {res[0]['href']}" if res else "Không tìm thấy."
    except: return "Lỗi tìm kiếm."

def search_multiple_images(query, count=3):
    try:
        with DDGS() as ddgs:
            res = list(ddgs.images(query, max_results=count))
            return [x['image'] for x in res]
    except: return []

def search_image_url(query):
    try:
        with DDGS() as ddgs:
            res = list(ddgs.images(query, max_results=1))
            return res[0]['image'] if res else None
    except: return None

# ================= 5. DỮ LIỆU HỆ THỐNG =================

NUMBER_MAP = {
    "1": "/tarot", "2": "/baitay", "3": "/nhac", "4": "/time", "5": "/thptqg",
    "6": "/hld", "7": "/wiki", "8": "/gg", "9": "/kbb",
    "10": "/meme", "11": "/anime", "12": "/code",
    "13": "/updt", "14": "/leak", "15": "/banner", "16": "/sticker", 
    "17": "/ai", "18": "/ge", "19": "/groq"
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

# --- TAROT FULL DATA ---
MAJORS_DATA = {
    0: ("The Fool", "sự khởi đầu đầy ngây thơ, tự do và tiềm năng vô hạn", "sự liều lĩnh ngu ngốc, ngây thơ quá mức hoặc rủi ro không đáng có", "hãy dũng cảm bước đi nhưng đừng quên nhìn đường"),
    1: ("The Magician", "năng lực hiện thực hóa, sự tập trung và kỹ năng điêu luyện", "sự thao túng, lừa dối hoặc tài năng bị sử dụng sai mục đích", "bạn có đủ mọi nguồn lực, hãy tin vào khả năng của mình"),
    2: ("The High Priestess", "trực giác sâu sắc, bí ẩn và thế giới nội tâm phong phú", "bí mật bị lộ, sự lạnh lùng hoặc ngắt kết nối với trực giác", "hãy lắng nghe tiếng nói nhỏ bé bên trong bạn"),
    3: ("The Empress", "sự trù phú, tình yêu thương nuôi dưỡng và vẻ đẹp sáng tạo", "sự phụ thuộc cảm xúc, thiếu thốn hoặc ghen tuông", "hãy yêu thương bản thân và kết nối với thiên nhiên"),
    4: ("The Emperor", "kỷ luật sắt đá, cấu trúc vững chắc và khả năng lãnh đạo", "sự độc tài, cứng nhắc hoặc thiếu linh hoạt", "cần thiết lập ranh giới và quy tắc rõ ràng"),
    5: ("The Hierophant", "niềm tin, truyền thống và sự học hỏi từ bậc thầy", "sự giáo điều, đạo đức giả hoặc nổi loạn vô cớ", "hãy tìm kiếm chân lý nhưng đừng mù quáng tin theo"),
    6: ("The Lovers", "sự lựa chọn từ trái tim, tình yêu đôi lứa và kết nối sâu sắc", "sự mất cân bằng, chia ly hoặc lựa chọn sai lầm", "hãy chọn điều mà trái tim bạn thực sự khao khát"),
    7: ("The Chariot", "ý chí kiên cường, quyết tâm chiến thắng mọi trở ngại", "sự hung hăng, mất kiểm soát hoặc hiếu thắng", "kiểm soát cảm xúc là chìa khóa của thành công"),
    8: ("Strength", "sức mạnh nội tâm, lòng trắc ẩn và sự kiểm soát mềm mỏng", "sự yếu đuối, thiếu tự tin hoặc bạo lực", "lạt mềm buộc chặt, hãy dùng tình thương để hóa giải"),
    9: ("The Hermit", "sự thu mình để chiêm nghiệm, tìm kiếm ánh sáng chân lý", "sự cô lập, xa lánh xã hội hoặc hoang tưởng", "dành thời gian một mình để hiểu rõ bản thân hơn"),
    10: ("Wheel of Fortune", "sự xoay vần của định mệnh, thay đổi bất ngờ", "xui xẻo, sự trì trệ hoặc kháng cự lại thay đổi", "chấp nhận sự thay đổi như một phần tất yếu của cuộc sống"),
    11: ("Justice", "sự công bằng, nhân quả và sự thật phơi bày", "sự bất công, thiên vị hoặc dối trá", "hãy trung thực với chính mình, gieo nhân nào gặt quả nấy"),
    12: ("The Hanged Man", "sự hy sinh, nhìn vấn đề ở góc độ khác", "sự bế tắc, hy sinh vô ích hoặc đóng vai nạn nhân", "đôi khi lùi một bước là để tiến ba bước"),
    13: ("Death", "kết thúc để tái sinh, buông bỏ cái cũ", "sự sợ hãi thay đổi, trì trệ hoặc không dám buông tay", "cánh cửa này đóng lại sẽ có cánh cửa khác mở ra"),
    14: ("Temperance", "sự cân bằng, chữa lành và kiên nhẫn", "sự mất cân bằng, vội vã hoặc xung đột", "hãy tìm điểm giữa, đừng quá cực đoan"),
    15: ("The Devil", "cám dỗ, ràng buộc vật chất hoặc nỗi sợ", "sự giải thoát, cai nghiện hoặc đối mặt với bóng tối", "đừng để dục vọng hay nỗi sợ kiểm soát bạn"),
    16: ("The Tower", "sự sụp đổ bất ngờ của niềm tin cũ", "sự sợ hãi thảm họa hoặc cố chấp níu giữ cái đã hỏng", "để xây lại cái mới tốt đẹp hơn, cái cũ mục nát phải sụp đổ"),
    17: ("The Star", "niềm hy vọng, sự chữa lành và niềm tin", "sự thất vọng, bi quan hoặc mất niềm tin", "hãy giữ vững niềm tin, ánh sáng luôn ở cuối đường hầm"),
    18: ("The Moon", "nỗi lo âu tiềm thức, ảo ảnh mơ hồ", "sự giải tỏa nỗi sợ, sự thật được phơi bày", "đừng để trí tưởng tượng tiêu cực dọa dẫm bạn"),
    19: ("The Sun", "niềm vui thuần khiết, thành công rực rỡ", "sự u ám tạm thời hoặc kỳ vọng quá cao", "hãy tỏa sáng và tận hưởng niềm vui sống"),
    20: ("Judgement", "tiếng gọi thức tỉnh, phán xét cuối cùng", "sự chối bỏ, hối tiếc hoặc không dám đối diện", "đã đến lúc đưa ra quyết định quan trọng"),
    21: ("The World", "sự hoàn thành trọn vẹn, viên mãn", "sự dang dở, thiếu một mảnh ghép cuối cùng", "bạn đang ở rất gần đích đến, hãy kiên trì thêm chút nữa")
}

MINORS_FULL = {
    "Wands": ("Lửa - Hành động", {
        "Ace": ("khởi đầu đầy nhiệt huyết", "mất động lực, trì hoãn", "hãy nắm bắt ngọn lửa đam mê ngay khi nó bùng lên"),
        "Two": ("lập kế hoạch tương lai", "sợ hãi không dám bước ra vùng an toàn", "tầm nhìn xa sẽ quyết định thành công của bạn"),
        "Three": ("mở rộng và chờ đợi kết quả", "gặp trở ngại ban đầu, thất vọng", "hãy kiên nhẫn, tàu của bạn đang về bến"),
        "Four": ("ăn mừng, ổn định và hạnh phúc", "mâu thuẫn gia đình, cảm giác không thuộc về", "hãy trân trọng những gì đang có"),
        "Five": ("cạnh tranh, mâu thuẫn rèn giũa", "xung đột gay gắt, né tránh mâu thuẫn", "cạnh tranh công bằng sẽ giúp bạn giỏi hơn"),
        "Six": ("chiến thắng, vinh quang", "kiêu ngạo, thất bại hoặc bị lãng quên", "hãy khiêm tốn khi ở trên đỉnh cao"),
        "Seven": ("phòng thủ, bảo vệ lập trường", "bị áp đảo, bỏ cuộc sớm", "đứng vững và bảo vệ niềm tin của mình"),
        "Eight": ("tốc độ, tin tức nhanh chóng", "trì hoãn, vội vàng hấp tấp", "hành động ngay nhưng đừng thiếu suy nghĩ"),
        "Nine": ("kiên trì, đề phòng phút chót", "kiệt sức, muốn bỏ cuộc", "chỉ còn một chút nữa thôi, đừng bỏ cuộc"),
        "Ten": ("gánh nặng, quá tải trách nhiệm", "buông bỏ bớt gánh nặng, sụp đổ", "hãy san sẻ công việc, đừng ôm đồm tất cả"),
        "Page": ("tin tức mới, sự tò mò khám phá", "tin xấu, thiếu nhiệt huyết", "hãy giữ tâm thế của người mới bắt đầu"),
        "Knight": ("hành động bốc đồng, phiêu lưu", "hung hăng, thiếu kiên nhẫn", "hãy dồn năng lượng vào mục tiêu cụ thể"),
        "Queen": ("tự tin, quyến rũ, ấm áp", "ghen tuông, hống hách", "hãy tỏa sáng bằng sự tự tin của chính mình"),
        "King": ("lãnh đạo, tầm nhìn xa", "độc đoán, đặt kỳ vọng quá cao", "hãy dẫn dắt bằng tầm nhìn, không phải bằng quyền lực")
    }),
    "Cups": ("Nước - Cảm xúc", {
        "Ace": ("tình cảm mới chớm nở", "cảm xúc bị kìm nén, buồn bã", "hãy mở lòng để đón nhận yêu thương"),
        "Two": ("kết nối đôi lứa, hòa hợp", "chia rẽ, mất kết nối", "sự đồng điệu là chìa khóa của mối quan hệ"),
        "Three": ("tụ tập, vui vẻ với bạn bè", "chuyện ngồi lê đôi mách, tiệc tàn", "hãy tận hưởng niềm vui cùng cộng đồng"),
        "Four": ("chán nản, thờ ơ cơ hội", "bỏ lỡ cơ hội, thức tỉnh", "đừng mải nhìn vào cái ly rỗng mà quên cái ly đầy"),
        "Five": ("tiếc nuối quá khứ, mất mát", "chấp nhận mất mát, chữa lành", "đừng khóc vì những gì đã mất, hãy nhìn những gì còn lại"),
        "Six": ("hoài niệm, người cũ, kỷ niệm", "dính mắc quá khứ, không sống thực tại", "quá khứ là kỷ niệm đẹp, không phải nơi để sống"),
        "Seven": ("ảo tưởng, quá nhiều lựa chọn", "vỡ mộng, nhìn ra sự thật", "hãy chọn một mục tiêu thực tế và theo đuổi nó"),
        "Eight": ("bỏ lại tất cả để tìm ý nghĩa", "sợ thay đổi, đi lang thang", "đôi khi phải buông bỏ cái tốt để tìm cái vĩ đại"),
        "Nine": ("ước mơ thành hiện thực, thỏa mãn", "tham lam, chưa hài lòng", "hạnh phúc là biết đủ"),
        "Ten": ("viên mãn, gia đình hạnh phúc", "xung đột gia đình, tan vỡ", "gia đình là nơi bão dừng sau cánh cửa"),
        "Page": ("tin nhắn tình cảm, mơ mộng", "nhạy cảm thái quá, tin buồn", "hãy lắng nghe trực giác mách bảo"),
        "Knight": ("lãng mạn, lời đề nghị tình yêu", "ảo tưởng, lừa dối tình cảm", "hãy lãng mạn nhưng đừng xa rời thực tế"),
        "Queen": ("thấu cảm, chữa lành, dịu dàng", "phụ thuộc cảm xúc, u uất", "hãy dùng lòng trắc ẩn để hóa giải hận thù"),
        "King": ("kiểm soát cảm xúc, trưởng thành", "lạnh lùng, thao túng cảm xúc", "cân bằng giữa trái tim và lý trí")
    }),
    "Swords": ("Khí - Tư duy", {
        "Ace": ("sự thật, trí tuệ sắc bén", "rối trí, sự thật gây đau lòng", "sự thật dù đau lòng vẫn tốt hơn lời nói dối"),
        "Two": ("bế tắc, do dự, che giấu", "nhìn ra sự thật, đưa ra quyết định", "đừng trốn tránh, hãy đối mặt để giải quyết"),
        "Three": ("đau lòng, tổn thương sâu sắc", "chữa lành, buông bỏ nỗi đau", "nỗi đau là cần thiết để trưởng thành"),
        "Four": ("nghỉ ngơi, hồi phục, tĩnh lặng", "kiệt sức, không chịu nghỉ ngơi", "hãy cho tâm trí một khoảng lặng"),
        "Five": ("chiến thắng rỗng tuếch, mâu thuẫn", "giải quyết mâu thuẫn, hối hận", "đừng thắng cuộc tranh luận mà thua một mối quan hệ"),
        "Six": ("rời bỏ rắc rối, bình yên", "khó khăn khi thay đổi, mang theo hành lý cảm xúc", "hãy để lại nỗi buồn ở bến bờ cũ"),
        "Seven": ("lén lút, chiến thuật, trốn tránh", "bị phát hiện, thú nhận", "sự trung thực là chính sách tốt nhất"),
        "Eight": ("tự trói buộc, bế tắc tâm lý", "giải thoát, tìm ra lối thoát", "nhà tù lớn nhất là suy nghĩ của chính bạn"),
        "Nine": ("lo âu, mất ngủ, ác mộng", "giải tỏa lo âu, đối mặt sợ hãi", "nỗi sợ chỉ là cái bóng của trí tưởng tượng"),
        "Ten": ("kết thúc đau đớn, chạm đáy", "hồi phục, bắt đầu lại", "khi chạm đáy, lối đi duy nhất là đi lên"),
        "Page": ("tò mò, quan sát, tin tức", "thị phi, soi mói, nói xấu", "hãy dùng trí tuệ để quan sát, đừng phán xét"),
        "Knight": ("hành động vội vã, thẳng thắn", "hung hăng, lời nói sát thương", "uốn lưỡi bảy lần trước khi nói"),
        "Queen": ("sắc sảo, độc lập, công bằng", "cay nghiệt, lạnh lùng, cô độc", "hãy dùng trí tuệ để bảo vệ, đừng để tấn công"),
        "King": ("quyền lực trí tuệ, nghiêm khắc", "độc tài, lạm dụng quyền lực", "sử dụng logic và công lý để dẫn dắt")
    }),
    "Pentacles": ("Đất - Tiền bạc", {
        "Ace": ("cơ hội tài chính mới, thịnh vượng", "bỏ lỡ cơ hội, tham lam", "hãy gieo hạt giống thịnh vượng ngay hôm nay"),
        "Two": ("cân bằng, linh hoạt xoay sở", "mất cân bằng, rối ren tài chính", "hãy giữ thăng bằng giữa các khía cạnh cuộc sống"),
        "Three": ("hợp tác, làm việc nhóm, chuyên môn", "thiếu hợp tác, làm việc cẩu thả", "muốn đi xa hãy đi cùng nhau"),
        "Four": ("giữ của, ổn định, an toàn", "keo kiệt, sợ mất mát", "tiền bạc cần lưu thông mới sinh sôi"),
        "Five": ("thiếu thốn, khó khăn, bị bỏ rơi", "hồi phục tài chính, tìm thấy hy vọng", "đừng ngại nhờ giúp đỡ khi sa cơ lỡ vận"),
        "Six": ("cho và nhận, hào phóng", "lợi dụng, nợ nần", "cho đi là còn mãi"),
        "Seven": ("kiên nhẫn chờ đợi, đánh giá đầu tư", "thiếu kiên nhẫn, đầu tư thất bại", "kiên nhẫn là chìa khóa của thành công"),
        "Eight": ("chăm chỉ, rèn luyện kỹ năng", "lười biếng, thiếu tập trung", "thành công đến từ sự nỗ lực không ngừng"),
        "Nine": ("độc lập tài chính, tận hưởng", "phụ thuộc, khoe khoang", "hãy tự hào về những gì mình làm ra"),
        "Ten": ("giàu có bền vững, di sản", "tranh chấp tài sản, gia đình lục đục", "sự thịnh vượng thực sự bao gồm cả hạnh phúc gia đình"),
        "Page": ("học hỏi, tin tốt về tiền", "thiếu thực tế, lãng phí", "hãy bắt đầu học cách quản lý tài chính"),
        "Knight": ("cần cù, đáng tin, chậm mà chắc", "trì trệ, cứng nhắc", "chậm mà chắc còn hơn nhanh mà ẩu"),
        "Queen": ("thực tế, chăm sóc, quản lý giỏi", "thực dụng, bỏ bê bản thân", "hãy chăm sóc bản thân như chăm sóc khu vườn của bạn"),
        "King": ("đỉnh cao thành công vật chất", "tham lam, chỉ biết đến tiền", "hãy dùng tiền để tạo ra giá trị cho cộng đồng")
    })
}

# --- BÀI TÂY FULL DATA ---
PLAYING_CARDS_FULL = {
    "Hearts": { # CƠ - CẢM XÚC
        "A": {"core": "một khởi đầu mới đầy ắp tình cảm", "shadow": "thực ra có thể bạn đang quá khao khát yêu thương nên dễ ngộ nhận", "advice": "hãy mở lòng nhưng đừng vội vàng trao hết"},
        "2": {"core": "sự kết nối sâu sắc giữa hai tâm hồn", "shadow": "nhưng cẩn thận kẻo bạn đang phụ thuộc cảm xúc vào người kia quá nhiều", "advice": "yêu thương cần đi kèm sự tự chủ"},
        "3": {"core": "sự phân vân hoặc người thứ 3", "shadow": "thực tế là chính bạn đang không rõ mình muốn gì, hoặc đang đứng núi này trông núi nọ", "advice": "hãy thành thật với cảm xúc của mình trước"},
        "4": {"core": "sự ổn định, cam kết", "shadow": "đôi khi nó lại là sự tẻ nhạt, bạn đang duy trì nó vì thói quen hơn là vì rung động", "advice": "hãy hâm nóng lại cảm xúc hoặc tìm niềm vui mới"},
        "5": {"core": "nỗi buồn, sự hụt hẫng", "shadow": "tao nghĩ không hẳn là ai làm mày buồn, mà là mày đang tiếc nuối những chuyện cũ chưa buông bỏ được", "advice": "đừng để quá khứ ám ảnh hiện tại nữa"},
        "6": {"core": "người cũ, kỷ niệm cũ", "shadow": "có vẻ như bạn đang lý tưởng hóa quá khứ và so sánh nó với hiện tại", "advice": "quá khứ chỉ nên là kỷ niệm, đừng để nó là rào cản"},
        "7": {"core": "ghen tuông, ảo tưởng", "shadow": "thực ra là bạn đang tự ti, sợ mình không đủ tốt nên mới sinh nghi ngờ", "advice": "nâng cao giá trị bản thân thay vì kiểm soát người khác"},
        "8": {"core": "gặp gỡ, giao lưu vui vẻ", "shadow": "nhưng coi chừng chỉ là những mối quan hệ xã giao hời hợt, vui đấy nhưng xong rồi thôi", "advice": "hãy tìm kiếm những kết nối chất lượng hơn"},
        "9": {"core": "ước nguyện thành hiện thực", "shadow": "nhưng coi chừng 'cầu được ước thấy' rồi lại nhận ra đó không phải thứ mình thực sự cần", "advice": "hãy cẩn trọng với những gì mình mong cầu"},
        "10": {"core": "hạnh phúc viên mãn", "shadow": "có thể bạn đang cố diễn vai hạnh phúc để che đậy những vết nứt nhỏ bên trong", "advice": "hạnh phúc thật sự đến từ sự bình yên, không phải sự hoàn hảo"},
        "J": {"core": "người trẻ tuổi, tin vui", "shadow": "một cảm xúc bồng bột, đến nhanh nhưng cũng dễ đi nhanh", "advice": "hãy tận hưởng khoảnh khắc nhưng đừng kỳ vọng quá xa"},
        "Q": {"core": "người phụ nữ dịu dàng", "shadow": "có thể bạn đang quá đa sầu đa cảm, chuyện bé xé ra to", "advice": "hãy dùng trực giác nhưng đừng quên lý trí"},
        "K": {"core": "người đàn ông chân thành", "shadow": "đôi khi sự tốt bụng này lại thiếu đi sự quyết đoán cần thiết", "advice": "cần mạnh mẽ bảo vệ cảm xúc của mình hơn"}
    },
    "Diamonds": { # RÔ - VẬT CHẤT
        "A": {"core": "tin tức về tiền bạc, giấy tờ", "shadow": "nhưng cẩn thận, cơ hội này có thể đi kèm những ràng buộc pháp lý rắc rối", "advice": "đọc kỹ mọi thứ trước khi gật đầu"},
        "2": {"core": "hợp đồng, trao đổi", "shadow": "có vẻ như bạn đang tính toán quá chi li, khiến mối quan hệ trở nên thực dụng", "advice": "đôi khi sòng phẳng quá lại mất tình cảm"},
        "3": {"core": "hợp tác làm ăn", "shadow": "nhưng coi chừng 'lắm thầy nhiều ma', chưa chắc hợp tác đã tốt hơn làm một mình", "advice": "chọn đối tác thật kỹ"},
        "4": {"core": "tiết kiệm, giữ tiền", "shadow": "thực ra là bạn đang sợ thiếu thốn, nỗi sợ này khiến bạn không dám đầu tư cho bản thân", "advice": "tiền cần được lưu thông mới sinh lời"},
        "5": {"core": "mất mát, khó khăn", "shadow": "vấn đề không phải là mất bao nhiêu tiền, mà là bạn đang cảm thấy giá trị bản thân bị sụt giảm", "advice": "bạn đáng giá hơn số dư tài khoản của bạn"},
        "6": {"core": "sự giúp đỡ, từ thiện", "shadow": "coi chừng bạn đang ban phát sự giúp đỡ để đổi lấy sự công nhận", "advice": "giúp người là tốt, nhưng đừng để bị lợi dụng"},
        "7": {"core": "rủi ro, tin đồn", "shadow": "bạn đang lo lắng thái quá về những thứ chưa xảy ra", "advice": "tập trung vào thực tế, bỏ qua tin đồn"},
        "8": {"core": "học hỏi, rèn luyện", "shadow": "bạn đang làm việc rất chăm chỉ nhưng có vẻ hơi thụ động, thiếu sự đột phá", "advice": "cần làm việc thông minh hơn là chỉ làm việc chăm chỉ"},
        "9": {"core": "tự chủ tài chính", "shadow": "bạn có tiền nhưng lại thấy cô đơn, không biết chia sẻ cùng ai", "advice": "tiền bạc là phương tiện, không phải mục đích sống"},
        "10": {"core": "đại phú, thành công lớn", "shadow": "áp lực phải duy trì sự thành công này đang đè nặng lên vai bạn", "advice": "hãy học cách hưởng thụ thành quả"},
        "J": {"core": "tin tức lợi nhuận", "shadow": "một khoản lợi nhỏ có thể làm bạn mờ mắt trước rủi ro lớn", "advice": "đừng tham bát bỏ mâm"},
        "Q": {"core": "người quản lý giỏi", "shadow": "bạn đang quá khắt khe với bản thân và người khác trong chuyện tiền nong", "advice": "hãy rộng lượng hơn một chút"},
        "K": {"core": "quyền lực tài chính", "shadow": "bạn đang dùng tiền để kiểm soát mọi thứ, kể cả tình cảm", "advice": "có những thứ tiền không mua được"}
    },
    "Clubs": { # TÉP - CÔNG VIỆC
        "A": {"core": "khởi đầu dự án mới", "shadow": "bạn hào hứng đấy, nhưng coi chừng 'cả thèm chóng chán'", "advice": "giữ vững ngọn lửa nhiệt huyết đường dài"},
        "2": {"core": "sự hỗ trợ", "shadow": "bạn đang dựa dẫm quá nhiều vào người khác mà quên mất năng lực tự thân", "advice": "hãy tự đứng trên đôi chân mình"},
        "3": {"core": "cân nhắc lựa chọn", "shadow": "thực ra bạn đã có câu trả lời rồi, chỉ là bạn sợ phải chịu trách nhiệm thôi", "advice": "quyết đoán lên, sai thì sửa"},
        "4": {"core": "nền tảng vững chắc", "shadow": "bạn đang ở trong vùng an toàn quá lâu, điều này kìm hãm sự phát triển", "advice": "đã đến lúc bước ra khỏi vỏ bọc"},
        "5": {"core": "thay đổi, thử thách", "shadow": "bạn đang chống lại sự thay đổi, chính sự kháng cự này làm bạn mệt mỏi", "advice": "thả lỏng và nương theo dòng chảy"},
        "6": {"core": "bước tiến, thành công", "shadow": "bạn đang ngủ quên trên chiến thắng và chủ quan", "advice": "khiêm tốn và tiếp tục nỗ lực"},
        "7": {"core": "tranh luận, mâu thuẫn", "shadow": "bạn đang cố chứng minh mình đúng hơn là tìm ra giải pháp chung", "advice": "lắng nghe cũng là một kỹ năng lãnh đạo"},
        "8": {"core": "bận rộn, di chuyển", "shadow": "bạn đang lao đi quá nhanh mà quên mất mục đích ban đầu là gì", "advice": "sống chậm lại một nhịp"},
        "9": {"core": "tham vọng, áp lực", "shadow": "bạn đang gồng gánh quá sức, ôm đồm việc của người khác", "advice": "hãy học cách từ chối và chia sẻ công việc"},
        "10": {"core": "đỉnh cao sự nghiệp", "shadow": "bạn đã đạt được mục tiêu nhưng lại thấy trống rỗng", "advice": "hãy tìm kiếm ý nghĩa mới cho công việc"},
        "J": {"core": "nhiệt huyết tuổi trẻ", "shadow": "sự thiếu kinh nghiệm có thể khiến bạn mắc sai lầm ngớ ngẩn", "advice": "hãy lắng nghe lời khuyên của người đi trước"},
        "Q": {"core": "giao tiếp khéo léo", "shadow": "bạn đang thảo mai hoặc thiếu chân thành trong công việc", "advice": "sự chân thật sẽ mang lại giá trị bền vững"},
        "K": {"core": "lãnh đạo quyền lực", "shadow": "bạn đang trở nên độc đoán và không chịu nghe ai", "advice": "lãnh đạo là phục vụ, không phải cai trị"}
    },
    "Spades": { # BÍCH - TÂM LÝ
        "A": {"core": "kết thúc để bắt đầu", "shadow": "bạn đang cố níu kéo những thứ đã chết, điều đó chỉ làm bạn thêm đau", "advice": "dũng cảm cắt bỏ những gì không còn phục vụ bạn"},
        "2": {"core": "mâu thuẫn, cãi vã", "shadow": "bạn đang đấu tranh với chính mình nhiều hơn là với người khác", "advice": "hòa giải nội tâm trước"},
        "3": {"core": "chia ly, rạn nứt", "shadow": "nỗi đau này đến để dạy bạn cách yêu thương bản thân mình hơn", "advice": "cho phép mình được buồn, nhưng đừng chìm đắm"},
        "4": {"core": "mệt mỏi, trì hoãn", "shadow": "cơ thể bạn đang biểu tình, bạn đã bỏ bê nó quá lâu", "advice": "nghỉ ngơi là một phần của công việc"},
        "5": {"core": "thất bại, mất mát", "shadow": "bạn đang đóng vai nạn nhân và đổ lỗi cho hoàn cảnh", "advice": "chấp nhận thất bại là bước đầu của thành công"},
        "6": {"core": "rời bỏ, đi xa", "shadow": "bạn đang trốn chạy vấn đề chứ không phải giải quyết nó", "advice": "đi đâu cũng được, miễn là tâm an"},
        "7": {"core": "phản bội, lừa dối", "shadow": "bạn đã bỏ qua những lá cờ đỏ (red flags) từ đầu vì muốn tin vào điều tốt đẹp", "advice": "tin vào trực giác của mình"},
        "8": {"core": "bế tắc, trở ngại", "shadow": "rào cản lớn nhất chính là suy nghĩ tiêu cực của bạn", "advice": "thay đổi góc nhìn, lối thoát sẽ mở ra"},
        "9": {"core": "lo âu, mất ngủ", "shadow": "bạn đang lo lắng về những thứ chưa xảy ra và có thể không bao giờ xảy ra", "advice": "sống cho hiện tại thôi"},
        "10": {"core": "gánh nặng, xui xẻo", "shadow": "mọi thứ dường như sụp đổ, nhưng đây là lúc bóng tối dày đặc nhất trước bình minh", "advice": "kiên cường lên, mọi chuyện rồi sẽ qua"},
        "J": {"core": "tiểu nhân, tin xấu", "shadow": "bạn đang thu hút những năng lượng tiêu cực này bằng sự sợ hãi của mình", "advice": "thanh lọc môi trường sống và tâm trí"},
        "Q": {"core": "sắc sảo, cô độc", "shadow": "bạn dựng lên bức tường băng giá để bảo vệ mình nhưng lại tự nhốt mình trong đó", "advice": "mở lòng ra, bạn xứng đáng được yêu thương"},
        "K": {"core": "lý trí, nghiêm khắc", "shadow": "bạn đang quá cứng nhắc và thiếu đi sự bao dung", "advice": "đôi khi cần xử lý bằng tình cảm hơn là lý lẽ"}
    }
}

SPREADS_TAROT = {
    "1": {"name": "1 Lá (Thông điệp)", "count": 1, "pos": ["Lời khuyên chính"]},
    "3": {"name": "3 Lá (QK-HT-TL)", "count": 3, "pos": ["Quá khứ", "Hiện tại", "Tương lai"]},
    "5": {"name": "5 Lá (Chi tiết)", "count": 5, "pos": ["Vấn đề hiện tại", "Thách thức", "Gốc rễ vấn đề", "Lời khuyên", "Kết quả tiềm năng"]}
}

SPREADS_PLAYING = {
    "3": {"name": "3 Lá (QK-HT-TL)", "count": 3, "pos": ["Quá khứ ảnh hưởng", "Hiện tại", "Xu hướng tương lai"]},
    "5": {"name": "5 Lá (Tổng quan)", "count": 5, "pos": ["Vấn đề chính", "Nguyên nhân sâu xa", "Yếu tố tiềm ẩn", "Lời khuyên hành động", "Kết quả dự báo"]},
    "7": {"name": "7 Lá (Tình duyên)", "count": 7, "pos": ["Năng lượng của bạn", "Năng lượng đối phương", "Cảm xúc của bạn", "Cảm xúc của họ", "Trở ngại khách quan", "Trở ngại chủ quan", "Kết quả mối quan hệ"]}
}

# ================= 6. ENGINE LOGIC (XỬ LÝ THÔNG MINH) =================

def get_natural_connector(index, total):
    if index == 0: return "Đầu tiên thì,"
    elif index == total - 1: return "Cuối cùng,"
    else: return random.choice(["Tiếp đến,", "Bên cạnh đó,", "Không chỉ vậy,", "Chưa hết đâu,", "Nhìn sang lá tiếp theo,"])

def get_funny_response(text):
    text = text.lower()
    if any(x in text for x in ["hi", "chào", "hello", "alo", "ê"]):
        return random.choice(["Chào cưng, nay rảnh ghé chơi à? 😎", "Alo nghe rõ, dây thép gai đây! 📞", "Gõ /help xem menu đi."])
    if "yêu" in text or "crush" in text:
        return random.choice(["Yêu đương gì tầm này, lo học đi má! 📚", "Crush nó không thích bạn đâu, tỉnh mộng đi. 🙄", "Vào /baitay xem quẻ tình duyên đi."])
    if "buồn" in text or "khóc" in text:
        return random.choice(["Buồn thì đi ngủ, trong mơ cái gì cũng có. 😴", "Thôi nín đi, khóc sưng mắt xấu lắm.", "Chán thì vào /kbb làm ván với tao này! 🥊"])
    if "ngu" in text or "dốt" in text:
        return random.choice(["Gương kia ngự ở trên tường... 🪞", "Chửi bot là nghiệp tụ vành môi đó nha. 🤐"])
    if "cảm ơn" in text: return "Khách sáo quá, chuyển khoản là được rồi. 💸"
    
    # Nếu không match câu nào -> Dùng AI trả lời (Hoặc Groq)
    return ask_groq(text)

def generate_tarot_deck():
    deck = []
    # Major Arcana
    for i, (name, meaning_up, meaning_rev, advice) in MAJORS_DATA.items():
        deck.append({"name": f"{name} (Ẩn Chính)", "meaning_up": meaning_up, "meaning_rev": meaning_rev, "advice": advice, "type": "Major"})
    # Minor Arcana
    for suit, (desc, ranks) in MINORS_FULL.items():
        for r_name, (up, rev, adv) in ranks.items():
            deck.append({"name": f"{r_name} of {suit}", "meaning_up": up, "meaning_rev": rev, "advice": adv, "type": "Minor"})
    return deck

def execute_tarot_reading(ctx):
    deck = generate_tarot_deck()
    random.shuffle(deck)
    spread = SPREADS_TAROT.get(ctx.get("spread_id", "3"), SPREADS_TAROT["3"])
    drawn = []
    for i in range(spread["count"]):
        if not deck: break
        c = deck.pop()
        c["pos"] = spread["pos"][i]
        c["orientation"] = random.choice(["Xuôi", "Ngược"])
        drawn.append(c)

    msg = f"🔮 **KẾT QUẢ TAROT: {ctx.get('topic').upper()}**\n"
    msg += f"👤 Querent: {ctx.get('info', 'Ẩn danh')}\n➖➖➖➖➖➖\n\n"
    msg += "🍃 **HÀNH TRÌNH CỦA BẠN:**\n\n"
    
    for i, c in enumerate(drawn):
        prefix = ["Mở đầu,", "Tiếp theo,", "Sau đó,", "Gần kết thúc,"][min(i, 3)]
        status_icon = "🔺" if c['orientation'] == "Xuôi" else "🔻"
        
        msg += f"{status_icon} **{c['pos']}: {c['name']}** ({c['orientation']})\n"
        if c['orientation'] == "Xuôi":
            msg += f"{prefix} lá bài này mang đến năng lượng tích cực về {c['meaning_up']}. Đây là tín hiệu để bạn tự tin bước tiếp.\n"
        else:
            msg += f"{prefix} ở chiều ngược, lá bài cảnh báo về {c['meaning_rev']}. Có lẽ bạn cần chậm lại để xem xét kỹ hơn.\n"
        msg += f"👉 *Lời khuyên nhỏ:* {c['advice']}\n\n"
            
    msg += "💡 **THÔNG ĐIỆP TỪ VŨ TRỤ:**\n"
    msg += "Mọi thứ diễn ra đều có lý do của nó. Hãy tin tưởng vào trực giác của bạn và dũng cảm đối diện với sự thật."
    return msg

def generate_playing_deck():
    deck = []
    suits_vn = {"Hearts": "Cơ", "Diamonds": "Rô", "Clubs": "Tép", "Spades": "Bích"}
    ranks_vn = {"A":"Át", "2":"Hai", "3":"Ba", "4":"Bốn", "5":"Năm", "6":"Sáu", "7":"Bảy", "8":"Tám", "9":"Chín", "10":"Mười", "J":"Bồi", "Q":"Đầm", "K":"Già"}
    for suit_en, ranks in PLAYING_CARDS_FULL.items():
        for rank, details in ranks.items():
            name = f"{ranks_vn[rank]} {suits_vn[suit_en]}"
            symbol = f"{rank}"
            deck.append({
                "name": name, 
                "symbol": symbol, 
                "suit": suit_en, 
                "core": details["core"], 
                "shadow": details["shadow"], 
                "advice": details["advice"]
            })
    return deck

def execute_playing_reading(ctx):
    deck = generate_playing_deck()
    random.shuffle(deck)
    spread = SPREADS_PLAYING.get(ctx.get("spread_id", "5"), SPREADS_PLAYING["5"])
    topic = ctx.get("topic", "Tổng quan").lower()
    drawn = []
    for i in range(spread["count"]):
        if not deck: break
        c = deck.pop()
        c["pos_name"] = spread["pos"][i]
        drawn.append(c)

    msg = f"🎭 **BÓI BÀI TÂY: {ctx.get('topic').upper()}**\n"
    msg += f"👤 Người hỏi: {ctx.get('info', 'Ẩn danh')}\n"
    msg += "➖➖➖➖➖➖➖➖➖➖\n\n"
    msg += "🃏 **BỘ BÀI ĐÃ BỐC:** " + " - ".join([c['symbol'] for c in drawn]) + "\n\n"
    msg += "☕ **TRÒ CHUYỆN VÀ LUẬN GIẢI:**\n\n"

    for i, c in enumerate(drawn):
        connector = get_natural_connector(i, len(drawn))
        interpretation = ""
        # Logic Context-Aware (Chuẩn V15)
        if "tình" in topic:
            if c["suit"] == "Diamonds": interpretation = f"Dù hỏi về tình cảm, nhưng lá Rô này ám chỉ **vấn đề tài chính** đang tác động. {c['core']}."
            elif c["suit"] == "Clubs": interpretation = f"Công việc bận rộn đang làm xao nhãng mối quan hệ. {c['core']}."
            elif c["suit"] == "Spades": interpretation = f"Thật tiếc khi lá Bích xuất hiện, báo hiệu thử thách tâm lý. {c['core']}."
            else: interpretation = f"Tín hiệu tốt lành cho tình yêu. {c['core']}."
        elif "tiền" in topic or "công" in topic:
            if c["suit"] == "Hearts": interpretation = f"Bạn đang để cảm xúc chi phối công việc. {c['core']}."
            elif c["suit"] == "Spades": interpretation = f"Cẩn thận rủi ro. {c['core']}."
            else: interpretation = f"Năng lượng rất tích cực. {c['core']}."
        else:
            interpretation = f"{c['core']}."

        msg += f"🔹 **{c['pos_name']}: {c['name']}**\n"
        msg += f"{connector} với lá bài này, về cơ bản nó nói về **{interpretation}**.\n"
        msg += f"👉 *Góc nhìn sâu hơn:* {c['shadow']}. "
        msg += f"Tại vị trí '{c['pos_name']}', lời khuyên là: {c['advice']}.\n\n"

    # Kết bài
    suits_count = {"Hearts": 0, "Diamonds": 0, "Clubs": 0, "Spades": 0}
    for c in drawn: suits_count[c["suit"]] += 1
    dom_suit = max(suits_count, key=suits_count.get)
    
    msg += "✅ **LỜI NHẮN NHỦ CUỐI CÙNG:**\n"
    if dom_suit == "Hearts": msg += "Cảm xúc đang dẫn lối bạn (nhiều Cơ). Hãy yêu thương nhưng đừng mù quáng."
    elif dom_suit == "Diamonds": msg += "Thực tế và vật chất đang lên ngôi (nhiều Rô). Hãy tính toán kỹ lưỡng."
    elif dom_suit == "Clubs": msg += "Hành động là chìa khóa (nhiều Tép). Đừng ngồi yên, hãy làm ngay đi."
    elif dom_suit == "Spades": msg += "Giai đoạn thử thách (nhiều Bích). Hãy kiên cường, sau cơn mưa trời lại sáng."

    return msg

# ================= 6. FLOW HỘI THOẠI =================

def handle_session_flow(user_id, text):
    s = tarot_sessions.get(user_id)
    if not s: return

    # Bước 1: Chọn chủ đề (MENU SỐ)
    if s["step"] == 1:
        topic_map = {"1": "Tình yêu", "2": "Công việc", "3": "Tiền bạc"}
        if text in topic_map:
            s["topic"] = topic_map[text]
            s["step"] = 2
            send_zalo_message(user_id, f"Bạn muốn hỏi cụ thể gì về '{s['topic']}'? (Gõ '.' để bỏ qua)")
        else:
            send_zalo_message(user_id, "⚠️ Vui lòng chỉ gõ số 1, 2 hoặc 3.")
    
    elif s["step"] == 2:
        s["question"] = text
        s["step"] = 3
        send_zalo_message(user_id, "Nhập Ngày sinh/Cung hoàng đạo:")
    
    elif s["step"] == 3:
        s["info"] = text
        s["step"] = 4
        if s["mode"] == "TAROT":
            send_zalo_message(user_id, "🔹 Chọn trải bài Tarot (Gõ số):\n1. 1 Lá (Thông điệp)\n2. 3 Lá (QK-HT-TL)\n3. 5 Lá (Chi tiết)")
        else:
            send_zalo_message(user_id, "🔹 Chọn trải bài Tây (Gõ số):\n1. 3 Lá (Thời gian)\n2. 5 Lá (Tổng quan)\n3. 7 Lá (Tình duyên)")
    
    elif s["step"] == 4:
        map_t = {"1":"1", "2":"3", "3":"5"}
        map_p = {"1":"3", "2":"5", "3":"7"}
        mapping = map_t if s["mode"] == "TAROT" else map_p
        
        if text in mapping:
            s["spread_id"] = mapping[text]
            send_zalo_message(user_id, "⏳ Đang xào bài và luận giải... (Tập trung nhé)...")
            res = execute_tarot_reading(s) if s["mode"] == "TAROT" else execute_playing_reading(s)
            send_zalo_message(user_id, res)
            del tarot_sessions[user_id]
        else: send_zalo_message(user_id, "❌ Vui lòng chỉ gõ số (1, 2, 3).")

# ================= 7. XỬ LÝ LỆNH =================

def handle_command(user_id, cmd, args):
    cmd = cmd.lower()
    
    if cmd == "/tarot":
        tarot_sessions[user_id] = {"step": 1, "mode": "TAROT"}
        send_zalo_message(user_id, "🔮 **PHÒNG TAROT ONLINE**\nChủ đề bạn quan tâm?\nGõ:\n1. Tình yêu\n2. Công việc\n3. Tiền bạc")

    elif cmd == "/baitay":
        tarot_sessions[user_id] = {"step": 1, "mode": "PLAYING"}
        send_zalo_message(user_id, "🎭 **PHÒNG BÓI BÀI TÂY**\nChủ đề bạn quan tâm?\nGõ:\n1. Tình yêu\n2. Công việc\n3. Tiền bạc")

    elif cmd == "/ai":
        if not args: send_zalo_message(user_id, "🤖 Cú pháp: /ai [câu hỏi]\nVD: /ai Viết thơ tặng vợ")
        else:
            send_zalo_message(user_id, "🧠 Đang suy nghĩ...")
            send_zalo_message(user_id, ask_chatgpt(" ".join(args)))

    elif cmd == "/ge":
        if not args: send_zalo_message(user_id, "💎 Cú pháp: /ge [câu hỏi]\nVD: /ge Tóm tắt sách")
        else:
            send_zalo_message(user_id, "💎 Gemini đang suy nghĩ...")
            send_zalo_message(user_id, ask_gemini(" ".join(args)))

    elif cmd == "/groq":
        if not args: send_zalo_message(user_id, "⚡ Cú pháp: /groq [câu hỏi]\nVD: /groq Dịch sang tiếng Anh")
        else:
            send_zalo_message(user_id, "⚡ Groq đang xử lý...")
            send_zalo_message(user_id, ask_groq(" ".join(args)))

    elif cmd == "/nhac":
        q = " ".join(args)
        send_zalo_message(user_id, f"🎧 **TÌM NHẠC:** https://www.youtube.com/results?search_query={q.replace(' ', '+')}")

    elif cmd == "/time":
        now = datetime.datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
        send_zalo_message(user_id, f"⏰ **GIỜ VN:** {now.strftime('%H:%M:%S')} - {now.strftime('%d/%m/%Y')}")

    elif cmd == "/thptqg":
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        days = (datetime.datetime(2026, 6, 12, tzinfo=tz) - datetime.datetime.now(tz)).days
        send_zalo_message(user_id, f"⏳ **ĐẾM NGƯỢC THPTQG 2026:**\n🎯 Mục tiêu: 12/06/2026\n📉 Còn lại: **{days} ngày**\nLo học đi!")

    elif cmd == "/hld":
        send_zalo_message(user_id, "🎉 **SỰ KIỆN:** Tết Nguyên Đán (29/01), Valentine (14/02).")

    elif cmd == "/wiki":
        try:
            s = wikipedia.summary(" ".join(args), sentences=3)
            send_zalo_message(user_id, f"📚 **WIKI:**\n{s}")
        except: send_zalo_message(user_id, "❌ Không tìm thấy.")

    elif cmd == "/gg":
        res = search_text_summary(" ".join(args))
        send_zalo_message(user_id, f"🔎 **KẾT QUẢ:**\n\n{res}")

    elif cmd == "/kbb":
        kbb_state[user_id] = "WAITING"
        send_zalo_message(user_id, "✊ **KÉO BÚA BAO**\nGõ: KEO, BUA hoặc BAO")

    elif cmd == "/meme":
        try:
            r = requests.get("https://meme-api.com/gimme/animememes").json()
            send_image_zalo(user_id, r.get("url"), "🤣 Meme nè:")
        except: send_zalo_message(user_id, "❌ Lỗi ảnh.")

    elif cmd == "/anime":
        send_zalo_message(user_id, f"🎬 **GỢI Ý:** {random.choice(['Naruto', 'One Piece', 'Attack on Titan', 'Frieren'])}")

    elif cmd == "/code":
        g = args[0].lower() if args else ""
        codes = GAME_CODES.get(g, ["⚠️ Chưa có code."])
        send_zalo_message(user_id, f"🎟️ **CODE {g.upper()}:**\n" + "\n".join(codes))

    elif cmd == "/updt":
        res = search_text_summary(f"{' '.join(args)} latest update patch notes")
        send_zalo_message(user_id, f"🆕 **UPDATE:**\n{res}")

    elif cmd == "/leak":
        res = search_text_summary(f"{' '.join(args)} latest leaks rumors")
        send_zalo_message(user_id, f"🕵️ **LEAK:**\n{res}")

    elif cmd == "/banner":
        if not args: send_zalo_message(user_id, "🏷️ Nhập tên game. VD: /banner genshin")
        else:
            q = " ".join(args)
            send_zalo_message(user_id, f"🔍 Đang tìm 3 banner {q} mới nhất...")
            urls = search_multiple_images(f"{q} current banner official event wish", 3)
            if urls:
                for i, u in enumerate(urls): send_image_zalo(user_id, u, f"🏷️ Banner {i+1}")
            else: send_zalo_message(user_id, "❌ Không tìm thấy ảnh.")

    elif cmd == "/sticker":
        send_zalo_message(user_id, "🖼️ Gửi ảnh vào đây để tạo sticker (Echo).")

    elif cmd in ["/help", "menu", "hi", "xin chào"]:
        menu = """✨➖ 🤖 **DANH SÁCH LỆNH BOT** 🤖➖✨
                    Tronglv📸
➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖
    🔮 **TAROT & TÂM LINH**
✨ 1./tarot : Bói bài Tarot
🎭 2./baitay : Bói bài Tây

    🤖 **TRÍ TUỆ NHÂN TẠO**
🧠 17./ai [câu hỏi] : Hỏi ChatGPT
💎 18./ge [câu hỏi] : Hỏi Gemini
⚡ 19./groq [câu hỏi] : Hỏi Groq (Siêu nhanh)

    🎵 **ÂM NHẠC**
🎧 3./nhac [tên] : Tìm nhạc Youtube

    🕒 **THỜI GIAN & SỰ KIỆN**
⏰ 4./time : Xem giờ hiện tại
⏳ 5./thptqg : Đếm ngược ngày thi
🎉 6./hld : Ngày lễ sắp tới

    📚 **TRA CỨU**
📖 7./wiki [từ] : Tra Wikipedia
🌐 8./gg [câu hỏi] : Link Google

    🎮 **GIẢI TRÍ**
✊ 9./kbb : Chơi Kéo Búa Bao
🤣 10./meme : Xem ảnh chế
🎬 11./anime : Gợi ý Anime

    🎁 **GAME**
🎟️ 12./code [game] : Giftcode game
🆕 13./updt [game] : Thông tin update
🕵️ 14./leak [game] : Tổng hợp leak
🏷️ 15./banner [game] : Banner hiện tại

    🖼️ **HÌNH ẢNH**
🖌️ 16./sticker : Gửi ảnh để tạo sticker"""
        send_zalo_message(user_id, menu)
    else:
        send_zalo_message(user_id, get_funny_response(cmd))

# ================= 8. MAIN HANDLER =================

@app.route("/", methods=['GET'])
def index(): return "Bot Zalo V31 Super Speed Live!", 200

@app.route("/webhook", methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if 'event_name' in data and data['event_name'] == 'message.text.received':
            msg = data['message']
            sender_id = msg['from']['id']
            text = msg.get('text', msg.get('content', '')).strip()
            print(f"User {sender_id}: {text}")

            if sender_id in tarot_sessions:
                if text.lower() in ["hủy", "stop", "thoát", "/help"]:
                    del tarot_sessions[sender_id]
                    if text == "/help": handle_command(sender_id, "/help", [])
                    else: send_zalo_message(sender_id, "✅ Đã hủy lệnh bói bài.")
                else: handle_session_flow(sender_id, text)
                return "ok", 200

            if sender_id in kbb_state:
                b = random.choice(["KEO", "BUA", "BAO"])
                u = text.upper()
                if u in ["KEO", "BUA", "BAO"]:
                    res = "Thắng 🎉" if (u=="KEO" and b=="BAO") or (u=="BUA" and b=="KEO") or (u=="BAO" and b=="BUA") else "Hòa 😐" if u==b else "Thua 😭"
                    send_zalo_message(sender_id, f"Bạn: {u} | Bot: {b} => {res}")
                    del kbb_state[sender_id]
                else: send_zalo_message(sender_id, "Gõ: KEO, BUA hoặc BAO")
                return "ok", 200

            if text in NUMBER_MAP:
                handle_command(sender_id, NUMBER_MAP[text], [])
                return "ok", 200

            if text.startswith("/"):
                parts = text.split()
                handle_command(sender_id, parts[0], parts[1:])
            else:
                if text.lower() in ["hi", "menu", "help"]: handle_command(sender_id, "/help", [])
                else: send_zalo_message(sender_id, get_funny_response(text))
        
        elif 'event_name' in data and data['event_name'] == 'user_send_image':
             sender_id = data['sender']['id']
             send_zalo_message(sender_id, "🖼️ Ảnh đẹp đấy! (Tính năng Sticker Echo)")

    except Exception as e: print(f"Error: {e}")
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
