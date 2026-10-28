# MISSION: BUILD A 100% OFFLINE PSYCHOMETRIC EXAM GENERATOR SYSTEM

Bạn là một Kiến trúc sư Hệ thống AI & Full-Stack Engineer hàng đầu. Hãy xây dựng một ứng dụng hoàn chỉnh mang tên "AI_KhaoThi_Antigravity" chạy hoàn toàn cục bộ (100% Offline) trên Windows, không yêu cầu quyền Administrator, tối ưu hóa cho cấu hình Intel Core i5-14500 (14 nhân, 20 luồng) và 16GB RAM.

---

## 1. THÔNG SỐ VẬN HÀNH & PHẦN CỨNG
- Môi trường: Windows 10/11 (Tài khoản Standard User - Non-Admin).
- Kết nối: 100% Offline (chỉ dùng loopback localhost 127.0.0.1 để tránh kích hoạt Windows Firewall UAC).
- Mô hình suy luận cục bộ: Qwen2.5-7B-Instruct (GGUF Q4_K_M) chạy ngầm qua KoboldCPP hoặc llama-cpp-python tại `http://127.0.0.1:5001/v1/chat/completions` với Context 8192 tokens và 12 CPU Threads.
- Không dùng database phức tạp bên ngoài: Toàn bộ lưu trữ tạm thời trong memory session hoặc file cục bộ.

---

## 2. BỘ QUY CHUẨN KHẢO THÍ ĐỐI CHIẾU (BẮT BUỘC NHÚNG VÀO SYSTEM PROMPT)
Hệ thống phải tuân thủ nghiêm ngặt 4 bộ tiêu chuẩn khảo thí sư phạm sau:
1. Đủ 7 dạng câu hỏi trắc nghiệm phổ biến:
   - Dạng 1: Trắc nghiệm 4 lựa chọn (MCQ A, B, C, D; đúng duy nhất 1 đáp án).
   - Dạng 2: Trắc nghiệm Đúng/Sai đa ý (Chuẩn Bộ GD&ĐT 2025: 1 câu dẫn và 4 mệnh đề a, b, c, d độc lập xác định Đúng/Sai).
   - Dạng 3: Trắc nghiệm trả lời ngắn (Điền số hoặc cụm từ ngắn tối đa 3-5 từ lấy trực tiếp từ bài đọc).
   - Dạng 4: Trắc nghiệm nhiều đáp án đúng (MSQ: Chọn 2 hoặc 3 phương án đúng trong 5-6 lựa chọn).
   - Dạng 5: Trắc nghiệm ghép đôi / nối cột (Cột 1 ghép với Cột 2; Cột 2 có nhiều hơn Cột 1 ít nhất 1 mục).
   - Dạng 6: Trắc nghiệm điền khuyết / đục lỗ (Cloze Test vào các vị trí từ khóa bản chất).
   - Dạng 7: Trắc nghiệm sắp xếp thứ tự logic / quy trình.
2. Bộ 22 nguyên tắc Haladyna & Downing (NBME):
   - Stem nêu rõ vấn đề trọn vẹn, không dùng phủ định kép. Nếu có từ phủ định bắt buộc viết IN HOA.
   - Phương án đúng không dài vượt trội. Các phương án nhiễu đồng nhất ngữ pháp và độ dài.
   - Tuyệt đối không dùng "Tất cả các ý trên" hoặc "Không có đáp án nào đúng".
3. Thang nhận thức Bloom sửa đổi (Anderson & Krathwohl):
   - Nhận biết (Remember)
   - Thông hiểu (Understand)
   - Vận dụng (Apply)
   - Vận dụng cao (Analyze/Evaluate)
4. Chống suy diễn chủ quan (Zero-Hallucination & Double-Check):
   - Mọi câu hỏi BẮT BUỘC trích dẫn nguyên văn (Verbatim Citation) từng câu từng chữ từ văn bản nguồn.
   - Mỗi câu hỏi đi kèm Thẻ kiểm định (Double-Check): Dẫn chứng nguyên văn, Phân tích đúng/sai của từng phương án, Đánh giá mức Bloom và Xác nhận không suy diễn.

---

## 3. CẤU TRÚC THƯ MỤC CẦN SINH RA
Hãy tạo dự án với cấu trúc thư mục sau:
AI_KhaoThi_Antigravity/
├── backend/
│   ├── app.py                # FastAPI server chính (REST API)
│   ├── parser.py             # Trích xuất văn bản từ DOCX, PDF, TXT
│   ├── chunker.py            # Thuật toán Semantic Thematic Chunking
│   ├── llm_client.py         # Client gọi API local LLM (127.0.0.1:5001)
│   └── docx_exporter.py      # Module xuất file Word chia 2 phần (Đề thi & Đáp án)
├── frontend/
│   ├── index.html            # Giao diện người dùng hiện đại, tinh gọn
│   ├── style.css             # CSS tùy chỉnh
│   └── app.js                # Quản lý giao diện, gọi API, hiển thị tiến độ
├── requirements.txt          # fastapi, uvicorn, python-docx, pypdfium2
└── Chay_Ung_Dung.bat         # Kịch bản khởi chạy 1-click không cần quyền Admin

---

## 4. CHI TIẾT CÁC MODULE CHỨC NĂNG CẦN LẬP TRÌNH

### A. Module backend/parser.py
- Viết hàm `extract_text_from_file(file_path)`:
  - Nếu là file `.docx`: Sử dụng thư viện `python-docx` để đọc toàn bộ paragraphs và tables.
  - Nếu là file `.pdf`: Sử dụng `pypdfium2` để trích xuất text từng trang một cách nhanh chóng.
  - Nếu là file `.txt`: Đọc với encoding `utf-8` (fallback `utf-8-sig` hoặc `cp1258`).

### B. Module backend/chunker.py
- Viết hàm `semantic_thematic_chunking(text, target_words=1800)`:
  - Phân tích cấu trúc văn bản theo tiêu đề (`#`, `Chương`, `Bài`, `Phần`, `I.`, `1.`, chữ in hoa).
  - Gom các đoạn văn thuộc cùng chủ đề kiến thức thành các phân đoạn từ 1.500 đến 2.500 từ.
  - Đảm bảo tính trọn vẹn của ngữ liệu, không cắt ngang câu.

### C. Module backend/llm_client.py
- Kết nối tới `http://127.0.0.1:5001/v1/chat/completions`.
- Tích hợp System Prompt chứa toàn bộ 4 bộ quy chuẩn khảo thí ở Mục 2.
- Nhận cấu hình ma trận đề (Tỷ lệ Bloom, các dạng câu hỏi được chọn) và sinh câu hỏi kèm Thẻ kiểm định (Double-Check).

### D. Module backend/docx_exporter.py
- Nhận danh sách các câu hỏi đã được người dùng tích chọn (selected questions).
- Tạo file Word (`.docx`) bằng `python-docx` với bố cục chuẩn sư phạm gồm 2 phần riêng biệt:
  - **PHẦN 1: ĐỀ THI DÀNH CHO HỌC SINH**: Bố cục trang bìa/tiêu đề trường, môn thi, thời gian. Liệt kê các câu hỏi kèm các phương án lựa chọn (KHÔNG chứa đáp án và KHÔNG chứa thẻ kiểm định).
  - **PHẦN 2: ĐÁP ÁN & HƯỚNG DẪN CHẤM DÀNH CHO GIÁO VIÊN**: Bảng đáp án nhanh, kèm chi tiết từng câu: Đáp án đúng, Dẫn chứng nguyên văn, Giải thích tính đúng/sai, và Phân tích mức độ Bloom.

### E. Giao diện frontend/index.html & frontend/app.js
- Thiết kế giao diện hiện đại (dùng Tailwind CSS qua CDN offline hoặc CSS thuần đẹp mắt).
- Vùng tải tệp: Hỗ trợ Kéo & Thả (Drag & Drop) file `.docx`, `.pdf`, `.txt` hoặc ô dán văn bản.
- Bảng cấu hình ma trận:
  - Ô nhập: Tổng số câu hỏi cần tạo.
  - Thanh trượt hoặc ô %: Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao.
  - Các hộp kiểm (Checkboxes) chọn trong 7 dạng câu hỏi.
- Thanh tiến trình: Hiển thị trạng thái xử lý từng phân đoạn (ví dụ: "Đang phân tích chủ đề 2/5...").
- Bảng hiển thị câu hỏi: Mỗi câu hiển thị nội dung và Thẻ kiểm định Double-Check, kèm một **Checkbox** chọn câu đạt chuẩn. Có nút "Chọn tất cả" / "Bỏ chọn tất cả".
- Nút bấm: "Khởi tạo đề thi chính thức (.docx)" -> Gửi danh sách các câu đã chọn về backend và tải ngay file Word hoàn chỉnh.

### F. File Chay_Ung_Dung.bat
- Kịch bản tự động kiểm tra môi trường Python có sẵn, khởi chạy Uvicorn server tại `127.0.0.1:8000` và tự động mở trình duyệt mặc định vào giao diện.

---

Hãy tiến hành viết toàn bộ mã nguồn chi tiết cho từng file trên, đảm bảo chạy trơn tru, không có lỗi cú pháp và đáp ứng tuyệt đối các tiêu chuẩn khảo thí đã đề ra!
```
