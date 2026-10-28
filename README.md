# AI Khảo Thí Antigravity (100% Offline)

Hệ thống AI Agent tạo câu hỏi khảo thí sư phạm đa dạng, chuẩn mực 4 trụ cột khảo thí, vận hành 100% Offline cục bộ, không gửi dữ liệu ra ngoài, không cần quyền Administrator.

---

## 🌟 Tính Năng Nổi Bật

1. **Chuẩn Mực Khảo Thí Sư Phạm & Câu Dẫn Độc Lập (Stand-alone Stem)**:
   - Câu hỏi được biên soạn theo vai trò: *"Biên soạn đề thi in ra giấy cho học sinh ngồi phòng thi độc lập"*.
   - Học sinh không cầm văn bản trên tay khi thi, câu dẫn hỏi thẳng vào bản chất kiến thức chuyên môn.
   - Cấm triệt để các tiền tố rác kiểu đọc hiểu: *"Căn cứ vào văn bản..."*, *"Theo tài liệu..."*, *"Dựa vào đoạn trích..."*.
   - Phương án nhiễu khoa học được thiết kế bằng cách biến đổi dữ kiện (thời gian, hoán đổi chủ thể, đảo ngược tính chất tự chủ), loại bỏ hoàn toàn các phương án rác (*"Tài liệu khẳng định..."*, *"Ngoài tài liệu..."*).

2. **Đủ 7 Dạng Câu Hỏi Khảo Thí Chuẩn 2025**:
   - `mcq`: Trắc nghiệm 4 lựa chọn (MCQ cổ điển).
   - `compound_tf`: Trắc nghiệm Đúng/Sai đa ý (4 mệnh đề a, b, c, d độc lập theo chuẩn Bộ GD&ĐT).
   - `short_answer`: Trắc nghiệm trả lời ngắn (Keyfill 3 - 5 từ).
   - `msq`: Trắc nghiệm nhiều lựa chọn đúng (chọn 2 hoặc 3 phương án).
   - `matching`: Trắc nghiệm ghép đôi / nối cột (Cột 1 và Cột 2).
   - `cloze`: Trắc nghiệm điền khuyết / đục lỗ (Cloze Test).
   - `sequencing`: Trắc nghiệm sắp xếp thứ tự logic / quy trình.

3. **Thẻ Kiểm Định Khảo Thí (Double-Check Card - Zero Hallucination)**:
   - Mỗi câu hỏi đều đi kèm trích dẫn nguyên văn (*verbatim citation*) từng câu từng chữ từ ngữ liệu nguồn.
   - Phân tích chi tiết tại sao từng phương án Đúng hoặc Sai.
   - Lý giải phân loại theo 4 mức độ nhận thức Bloom sửa đổi (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao).

4. **Trích Xuất Văn Bản Đa Định Dạng (Offline)**:
   - Hỗ trợ file Microsoft Word (`.docx`), PDF (`.pdf`), Text (`.txt`, `.md`).
   - Tự động phân đoạn ngữ nghĩa theo chủ đề kiến thức (Thematic Semantic Chunking).

5. **Xuất File Word (.docx) Chuẩn Khảo Thí 2 Phần**:
   - **Phần 1**: Đề thi dành riêng cho học sinh (không kèm đáp án).
   - **Phần 2**: Đáp án, hướng dẫn chấm chi tiết kèm Bảng tổng hợp đáp án nhanh và Thẻ kiểm định dành cho giáo viên.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

### Khởi động nhanh (Khuyên dùng)
Nhấp đúp chuột vào file:
```bat
Chay_Ung_Dung.bat
```
Hệ thống sẽ tự động kích hoạt môi trường ảo Python, khởi chạy máy chủ backend tại `http://127.0.0.1:8000` và tự động mở trình duyệt web.

### Khởi động thủ công qua dòng lệnh
1. Tạo môi trường ảo và cài đặt thư viện:
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Khởi chạy máy chủ:
```bash
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

3. Mở trình duyệt và truy cập: `http://127.0.0.1:8000`

---

## 📁 Cấu Trúc Dự Án

```
AI_KhaoThi_Antigravity/
├── backend/
│   ├── app.py               # REST API & FastAPI Server
│   ├── parser.py            # Trích xuất DOCX, PDF, TXT & Bộ lọc hậu xử lý (Post-Processing Filter)
│   ├── chunker.py           # Phân đoạn ngữ nghĩa chủ đề kiến thức
│   ├── llm_client.py        # Kết nối Local LLM & Heuristic Grounded Engine
│   └── docx_exporter.py     # Xuất file Word 2 phần (Học sinh + Giáo viên)
├── frontend/
│   ├── index.html           # Giao diện Single Page Application hiện đại
│   ├── app.js               # Logic điều khiển giao diện & gọi API
│   └── styles.css           # Bảng màu Indigo/Slate, Glassmorphism & Responsive
├── tests/
│   └── test_integrity.py   # Bộ kiểm thử toàn vẹn tự động 5 module
├── Chay_Ung_Dung.bat        # Script khởi chạy 1-click cho người dùng Windows
├── requirements.txt         # Danh mục thư viện phụ thuộc
└── README.md
```

---

## 🧪 Kiểm Thử Toàn Vẹn Hệ Thống
Chạy bộ kiểm thử tự động để xác nhận toàn bộ các module hoạt động 100%:
```bash
.\.venv\Scripts\python.exe tests/test_integrity.py
```

---

## 📄 Bản Quyền
Phát triển phục vụ công tác khảo thí sư phạm và đo lường đánh giá giáo dục 100% Offline.
