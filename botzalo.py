from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# --- CẤU HÌNH ---
# Token bạn đã cung cấp
ACCESS_TOKEN = "3829309327888967360:fPyGnthDWNupvADfZCeiIMmiUgprSDHzEIgHsTBPrhdfBheDVEHSeDgkMGVVwUDI"

# URL gửi tin nhắn của Zalo (Dành cho Zalo Platform/OA)
# Nếu bot cá nhân dùng endpoint khác, bạn xem trong log lỗi để điều chỉnh
ZALO_API_URL = "https://openapi.zalo.me/v2.0/oa/message"

@app.route('/', methods=['GET'])
def index():
    return "Bot Zalo (botzalo.py) đang chạy!", 200

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    # Zalo đôi khi gửi yêu cầu GET để xác thực webhook (tùy phiên bản)
    if request.method == 'GET':
        return "Webhook OK", 200

    # Xử lý tin nhắn đến (POST)
    data = request.get_json()
    
    # In toàn bộ dữ liệu nhận được ra Log của Render để debug
    # Bạn vào tab "Logs" trên Render để xem cấu trúc tin nhắn chuẩn nếu code lỗi
    print("📩 Dữ liệu nhận được:", json.dumps(data, indent=2))

    try:
        # --- PHÂN TÍCH TIN NHẮN ---
        # Cấu trúc JSON có thể thay đổi tùy loại bot, đây là cấu trúc phổ biến nhất
        if 'event_name' in data and data['event_name'] == 'user_send_text':
            sender_id = data['sender']['id']
            user_msg = data['message']['text']
            
            print(f"User {sender_id} nhắn: {user_msg}")
            
            # --- LOGIC TRẢ LỜI ---
            reply_text = ""
            msg_lower = user_msg.lower()

            if "xin chào" in msg_lower or "hi" in msg_lower:
                reply_text = "Chào bạn! Mình là Bot Zalo cá nhân."
            elif "/help" in msg_lower:
                reply_text = "Gõ 'xin chào' hoặc 'giá' để xem nhé."
            elif "giá" in msg_lower:
                reply_text = "Sản phẩm này giá 100k ạ."
            else:
                # Bot nhại lại lời nói (Echo)
                reply_text = f"Bạn vừa nói: {user_msg}"

            # Gửi tin nhắn phản hồi
            send_zalo_message(sender_id, reply_text)

    except Exception as e:
        print(f"⚠️ Lỗi xử lý webhook: {e}")

    # Luôn trả về 200 để Zalo không gửi lại tin nhắn cũ
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
        resp_json = response.json()
        
        # Check xem gửi thành công không
        if response.status_code == 200 and resp_json.get('error') == 0:
            print(f"✅ Đã gửi trả lời cho {user_id}")
        else:
            print(f"❌ Lỗi gửi tin (Zalo trả về): {resp_json}")
            
    except Exception as e:
        print(f"❌ Lỗi kết nối gửi tin: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)