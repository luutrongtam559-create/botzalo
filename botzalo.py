from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# --- CẤU HÌNH ---
# Token của bạn
ACCESS_TOKEN = "3829309327888967360:fPyGnthDWNupvADfZCeiIMmiUgprSDHzEIgHsTBPrhdfBheDVEHSeDgkMGVVwUDI"
ZALO_API_URL = "https://openapi.zalo.me/v2.0/oa/message"

@app.route('/', methods=['GET'])
def index():
    return "Bot Zalo đang chạy!", 200

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    if request.method == 'GET':
        return "Webhook OK", 200

    data = request.get_json()
    print("📩 Dữ liệu nhận được:", json.dumps(data, indent=2))

    try:
        # --- SỬA LẠI PHẦN NÀY ĐỂ KHỚP VỚI ẢNH LOG ---
        
        # 1. Kiểm tra sự kiện 'message.text.received' thay vì 'user_send_text'
        if 'event_name' in data and data['event_name'] == 'message.text.received':
            
            message_data = data['message']
            
            # 2. Lấy ID người gửi từ 'from' -> 'id'
            sender_id = message_data['from']['id']
            
            # 3. Lấy nội dung tin nhắn
            # (Thử lấy ở 'text', nếu không có thì thử 'content' vì JSON bị cắt nên mình đoán)
            user_msg = message_data.get('text') 
            if not user_msg:
                user_msg = message_data.get('content', '')

            print(f"User {sender_id} nhắn: {user_msg}")
            
            # --- LOGIC TRẢ LỜI ---
            reply_text = ""
            msg_lower = str(user_msg).lower() # Chuyển về chữ thường để so sánh

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

def send_zalo_message(user_id, text_content):
    headers = {
        "Content-Type": "application/json",
        "access_token": ACCESS_TOKEN
    }
    payload = {
        "recipient": {
            "user_id": user_id
        },
        "message": {
            "text": text_content
        }
    }
    
    try:
        response = requests.post(ZALO_API_URL, headers=headers, json=payload)
        print("Phản hồi gửi đi:", response.json())
    except Exception as e:
        print("Lỗi gửi tin nhắn:", e)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
