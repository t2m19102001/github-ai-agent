# 🤖 Code Chat Assistant - Hướng Dẫn Sử Dụng

## 🎯 Giới Thiệu

**Code Chat Assistant** là một AI-powered code helper cho phép bạn:
- 💬 **Chat trực tiếp** với AI về code của bạn
- 📚 **AI đọc và phân tích** tất cả files trong project
- 🔧 **Đề xuất cải tiến** và best practices
- 🛠️ **Chỉnh sửa files** theo yêu cầu
- 🐛 **Debug vấn đề** và giải thích code
- 📝 **Tạo code mới** cho bạn

## 📦 Cài Đặt

### 1. Cài đặt dependencies
```bash
cd /Users/minhman/Develop/github-ai-agent
pip install -r requirements.txt
```

### 2. Cấu hình `.env`
Đảm bảo file `.env` có:
```dotenv
GROQ_API_KEY=your_groq_key_here
GITHUB_TOKEN=your_github_token_here
REPO_FULL_NAME=your_username/your_repo
MODE=cloud
DEBUG=false
```

## 🚀 Chạy Code Chat

### Option 1: Web Interface (Recommended)
```bash
cd /Users/minhman/Develop/github-ai-agent
python app.py
```

Sau đó mở trình duyệt: **http://localhost:5000**

### Option 2: Terminal Interface
```bash
cd /Users/minhman/Develop/github-ai-agent
python code_chat.py
```

## 💬 Cách Sử Dụng

### Web Interface

#### Chat
- Gõ câu hỏi hoặc yêu cầu vào text box
- Ấn Enter hoặc click nút gửi
- AI sẽ trả lời dựa trên code context

#### Duyệt Files
- Click vào file trong sidebar để xem nội dung
- AI sẽ hiển thị file content

#### Tools
- **📚 Load Context**: Tải context code hiện tại
- **📋 History**: Xem lịch sử chat
- **🗑️ Clear Chat**: Xóa tất cả messages

### Terminal Interface

#### Commands
- **`list`** - Liệt kê tất cả code files
- **`read <file>`** - Đọc nội dung file
- **`context`** - Xem code context
- **`quit`** - Thoát chương trình

#### Chat
- Gõ bất kỳ câu hỏi nào về code
- AI sẽ phân tích và trả lời

## 💡 Ví Dụ Sử Dụng

### Ví dụ 1: Giải thích code
```
You: Explain my code structure
🤖 Assistant: [AI explains your project structure]
```

### Ví dụ 2: Xem file cụ thể
```
You: Show me github_agent_hybrid.py
🤖 Assistant: [AI displays file content and explains]
```

### Ví dụ 3: Yêu cầu chỉnh sửa
```
You: Add error handling to github_agent_hybrid.py
🤖 Assistant: [AI suggests improvements and creates modified version]
```

### Ví dụ 4: Debug vấn đề
```
You: Why am I getting 401 error?
🤖 Assistant: [AI analyzes code and suggests fixes]
```

### Ví dụ 5: Tạo file mới
```
You: Create a unit test file for my project
🤖 Assistant: [AI creates test file with test cases]
```

## 🎓 Advanced Features

### 1. Code Modifications
AI có thể trả lời dưới dạng JSON để tự động chỉnh sửa files:
```json
{
    "type": "code_modification",
    "file": "path/to/file.py",
    "action": "create|modify|delete",
    "content": "new code here"
}
```

### 2. Context Awareness
- AI tự động load code context từ project
- Hiểu được project structure
- Có thể liên kết giữa các files

### 3. Conversation History
- Giữ lịch sử chat
- AI nhớ context từ messages trước
- Có thể clear history khi cần

## ⚙️ Cấu Hình

### Environment Variables
```dotenv
# API Keys
GROQ_API_KEY=your_groq_key          # Bắt buộc
GITHUB_TOKEN=your_github_token      # Tuỳ chọn

# Settings
MODE=cloud                           # Chỉ hỗ trợ 'cloud'
DEBUG=false                          # Set 'true' for detailed logs
CHAT_PORT=5000                       # Port cho web interface
```

### Supported File Types
- `.py` - Python
- `.js`, `.ts` - JavaScript/TypeScript
- `.java` - Java
- `.cpp`, `.c` - C/C++
- `.go` - Go
- `.rb` - Ruby
- `.php` - PHP

## 🔒 Bảo Mật

⚠️ **Important**:
1. **Không commit `.env`** vào GitHub
2. **Giữ API keys riêng tư**
3. **Xóa sensitive data** trước khi chia sẻ code
4. **Rotate tokens** nếu bị expose

## 🐛 Troubleshooting

### Lỗi: "Connection refused"
```bash
# Kiểm tra port 5000 có bị dùng
lsof -i :5000

# Kill process nếu cần
kill -9 <PID>

# Chạy lại app
python app.py
```

### Lỗi: "GROQ API error"
1. Kiểm tra GROQ_API_KEY trong `.env`
2. Đảm bảo key còn hạn
3. Check GROQ quota

### Lỗi: "File not found"
- File phải nằm trong project directory
- Đường dẫn phải là relative path từ project root

### Lỗi: "No code files found"
- Đảm bảo có Python files trong project
- Check .gitignore không filter files cần thiết

## 📊 API Endpoints

### Web Interface APIs

#### Chat
```
POST /api/chat
Body: {
    "message": "Your question",
    "include_context": true
}
```

#### Get Files
```
GET /api/files
Response: { "files": [...], "count": N }
```

#### Read File
```
POST /api/read
Body: { "file": "path/to/file.py" }
```

#### Get Context
```
GET /api/context
```

#### Get History
```
GET /api/history
```

#### Clear History
```
POST /api/clear-history
```

## 🎯 Tips & Tricks

1. **Use specific questions** - "What does this function do?" vs "Explain everything"
2. **Reference files** - "In my github_agent_hybrid.py, why..."
3. **Ask for improvements** - "How can I improve this code?"
4. **Use chat history** - AI remembers context, nên build on previous messages
5. **Test suggestions** - Luôn test AI-generated code trước khi dùng

## 🤝 Support

- **Issues**: File GitHub issue nếu gặp bug
- **Questions**: Ask AI directly trong chat!
- **Feedback**: Góp ý cải thiện tính năng

---

**Happy coding! 🚀**
