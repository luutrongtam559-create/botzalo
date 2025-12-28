from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# --- CẤU HÌNH ---
# Token mới nhất bạn vừa gửi
ACCESS_TOKEN = "3829309327888967360:pbdpnfxQdCOoTHEqPdnSPIoWkwatLMuUOCcmokIwjBtygqsAMhFDyDcwFuohadlr"

@app.route('/', methods=['GET'])
def index():
    return "Bot Zalo Platform đang chạy!", 200

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook OK", 200

    data = request.get_json()
    # In log để kiểm tra nếu cần
    print("📩 Dữ liệu nhận được:", json.dumps(data, indent=2))

    try:
        # Xử lý tin nhắn đến
        if 'event_name' in data and data['event_name'] == 'message.text.received':
            message_data = data['message']
            
            # 1. Lấy ID người gửi (Dùng làm chat_id để trả lời)
            sender_id = message_data['from']['id']
            
            # 2. Lấy nội dung tin nhắn (thử lấy text, nếu không có lấy content)
            user_msg = message_data.get('text')
            if not user_msg:
                user_msg = message_data.get('content', '')

            print(f"User {sender_id} nhắn: {user_msg}")
            
            # --- LOGIC TRẢ LỜI ---
            reply_text = ""
            msg_lower = str(user_msg).lower()

            if "xin chào" in msg_lower or "hi" in msg_lower:
                reply_text = "Chào bạn! Mình là Bot Zalo cá nhân."
            elif "/help" in msg_lower:
                reply_text = "Gõ 'xin chào' hoặc 'giá' để xem nhé."
            elif "giá" in msg_lower:
                reply_text = "Sản phẩm này giá 100k ạ."
            else:
                reply_text = f"Bạn vừa nói: {user_msg}"

            # Gửi tin nhắn phản hồi
            send_zalo_message(sender_id, reply_text)

    except Exception as e:
        print(f"⚠️ Lỗi xử lý webhook: {e}")

    return "OK", 200

def send_zalo_message(chat_id, text_content):
    # --- QUAN TRỌNG: CẬP NHẬT API THEO ẢNH BẠN GỬI ---
    # URL này dành riêng cho Bot Cá nhân (Platform)
    api_url = f"https://bot-api.zaloplatforms.com/bot{ACCESS_TOKEN}/sendMessage"
    
    # Cấu trúc gửi tin đúng chuẩn Platform
    payload = {
        "chat_id": chat_id, # ID người nhận
        "text": text_content # Nội dung tin nhắn
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        
        # In kết quả gửi tin ra Log để kiểm tra
        print(f"Phản hồi gửi đi: {response.status_code} - {response.text}")
        
    except Exception as e:
        print("Lỗi gửi tin nhắn:", e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
