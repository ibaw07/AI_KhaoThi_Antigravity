# TÀI LIỆU ĐẶC TẢ KIẾN TRÚC VÀ YÊU CẦU HỆ THỐNG AI KHẢO THÍ ĐA DẠNG (OFFLINE)

Tài liệu này tổng hợp toàn bộ các yêu cầu nghiệp vụ, tiêu chuẩn khảo thí đối chiếu và cấu trúc kỹ thuật của hệ thống AI Agent hỗ trợ tạo câu hỏi thi trắc nghiệm ngoại tuyến, tối ưu cho máy trạm **Intel Core i5-14500 (14 nhân, 20 luồng), 16GB RAM**, vận hành trên môi trường Windows không có quyền Administrator.

---

## I. TỔNG QUAN HỆ THỐNG VÀ BỐI CẢNH VẬN HÀNH

* **Mục tiêu**: Xây dựng một ứng dụng AI cục bộ độc lập (100% Offline) có khả năng đọc hiểu tài liệu dài (.docx, .pdf, .txt), tự động phân đoạn theo chủ đề kiến thức, tạo các dạng câu hỏi trắc nghiệm chuẩn mực khảo thí, cung cấp thẻ kiểm định chéo và cho phép giáo viên tích chọn câu hỏi để xuất đề thi Word (.docx).
* **Môi trường phần cứng**: Intel Core i5-14500 (6 P-Core + 8 E-Core), 16GB RAM DDR4/DDR5, không yêu cầu GPU rời.
* **Quyền hạn hệ thống**: Tài khoản Standard User (Non-Admin), không có quyền can thiệp registry, không cài service hệ thống, chạy loopback `127.0.0.1` để không bị kích hoạt Windows Firewall.
* **Mô hình suy luận nền tảng**: Qwen2.5-7B-Instruct (định dạng GGUF Q4_K_M, dung lượng ~4.7GB, Context 8192 tokens, chiếm khoảng 6.5GB RAM).

---

## II. BỘ QUY CHUẨN KHẢO THÍ VÀ CHỐNG SUY DIỄN (GROUND TRUTH)

Hệ thống bắt buộc phải đối chiếu nghiêm ngặt theo 4 trụ cột khảo thí:

### 1. Trọn bộ 7 dạng câu hỏi trắc nghiệm phổ biến
1. **Trắc nghiệm 4 lựa chọn (MCQ)**: 1 câu dẫn, 4 phương án A, B, C, D độc lập; đúng duy nhất 1 phương án; phương án đúng không được dài vượt trội; các phương án nhiễu đồng nhất ngữ pháp và độ dài; không dùng "Tất cả các ý trên" hoặc "Không có đáp án nào đúng".
2. **Trắc nghiệm Đúng/Sai đa ý (Compound True/False)**: 1 ngữ cảnh/câu dẫn chung và 4 mệnh đề a, b, c, d độc lập để thí sinh xác định Đúng hoặc Sai cho từng mệnh đề; các mệnh đề không được phụ thuộc nhân quả lẫn nhau.
3. **Trắc nghiệm trả lời ngắn (Short Answer / Keyfill)**: Yêu cầu điền một số liệu chính xác, thuật ngữ khoa học hoặc từ khóa đơn nhất lấy trực tiếp từ dữ liệu bài đọc (tối đa 3 - 5 từ).
4. **Trắc nghiệm nhiều đáp án đúng (Multiple-Response / MSQ)**: Cho 5 - 6 phương án, yêu cầu chọn đúng 2 hoặc 3 phương án (ví dụ: "Chọn 3 biểu hiện đúng sau đây").
5. **Trắc nghiệm ghép đôi / Nối cột (Matching Items)**: Cột 1 (sự kiện, khái niệm) ghép với Cột 2 (định nghĩa, bản chất); số lượng mục Cột 2 luôn nhiều hơn Cột 1 ít nhất 1 mục để tránh đoán mò loại trừ.
6. **Trắc nghiệm điền khuyết / Đục lỗ (Cloze Test)**: Trích đoạn một đoạn văn bản và đục lỗ các vị trí trọng yếu (1), (2), (3) để thí sinh chọn từ thích hợp điền vào chỗ trống.
7. **Trắc nghiệm sắp xếp thứ tự (Sequencing / Ordering)**: Cung cấp các bước trong quy trình thực nghiệm hoặc sự kiện lịch sử bị xáo trộn, yêu cầu xác định trình tự chuẩn xác.

### 2. Nguyên tắc 22 điểm của Haladyna & Downing
* Phần dẫn (Stem) phải thể hiện trọn vẹn câu hỏi; không dùng câu phủ định kép; nếu có từ phủ định bắt buộc viết IN HOA.
* Phương án đúng (Key) đơn nhất, không mang tính tranh cãi.
* Phương án nhiễu (Distractors) hợp lý với người chưa học kỹ nhưng sai dứt khoát theo tài liệu; không dùng các từ tuyệt đối ("luôn luôn", "không bao giờ").

### 3. Thang đo nhận thức Bloom sửa đổi (Anderson & Krathwohl, 2001)
* **Nhận biết (Remember)**: Nhận diện, nêu lại sự kiện, số liệu trực tiếp.
* **Thông hiểu (Understand)**: Diễn giải, phân loại, so sánh ý nghĩa dựa trên ngữ cảnh.
* **Vận dụng (Apply)**: Áp dụng nguyên lý vào tình huống cụ thể nêu trong văn bản.
* **Vận dụng cao (Analyze/Evaluate)**: Mổ xẻ cấu trúc nhân quả, phản biện hoặc đánh giá tiêu chí.

### 4. Cơ chế chống suy diễn chủ quan (Zero-Hallucination)
* Tuyệt đối không đưa kiến thức ngoài vào câu hỏi.
* Bắt buộc trích dẫn nguyên văn (Verbatim Citation) từng câu từng chữ làm bằng chứng pháp lý cho mỗi câu hỏi.
* Mỗi câu hỏi bắt buộc đính kèm **Thẻ kiểm định khảo thí (Double-Check Card)** gồm: Dẫn chứng nguyên văn, Phân tích tính đúng/sai của từng phương án, Đánh giá mức Bloom và Xác nhận độ tin cậy 100% từ tài liệu.

---

## III. CÁC TÍNH NĂNG VÀ LUỒNG TƯƠNG TÁC NGƯỜI DÙNG

1. **Xử lý tài liệu đầu vào (Input Ingestion)**:
   * Cho phép kéo thả trực tiếp file Word (`.docx`), PDF (`.pdf`) hoặc Text (`.txt`).
   * Tự động trích xuất nội dung văn bản và bóc tách cấu trúc tiêu đề.
2. **Cấu hình ma trận đề thi (Matrix Configurator)**:
   * Nhập tổng số câu hỏi cần tạo.
   * Cài đặt tỷ lệ 4 mức Bloom (ví dụ: 40% Nhận biết, 30% Thông hiểu, 20% Vận dụng, 10% Vận dụng cao).
   * Lựa chọn các dạng câu hỏi mong muốn trong 7 dạng.
3. **Phân đoạn ngữ nghĩa theo chủ đề kiến thức (Semantic Thematic Chunking)**:
   * Nhận diện các tiêu đề chương, mục (`#`, `Chương`, `Bài`, `Phần`, `I.`, `1.`, chữ in hoa).
   * Gom nội dung thành các phân đoạn chủ đề trọn vẹn (1.500 – 2.500 từ), gửi tuần tự đến mô hình để bảo vệ bộ nhớ.
4. **Duyệt đề tối giản bằng Checkbox**:
   * Mỗi câu hỏi hiển thị kèm Thẻ kiểm định (Double-Check) và một **Hộp kiểm (Checkbox)**.
   * Người ra đề rà soát nhanh dẫn chứng và tích chọn những câu đạt chuẩn.
5. **Xuất đề thi Word (.docx) chuyên nghiệp**:
   * Người dùng nhấn nút "Khởi tạo đề thi chính thức".
   * Hệ thống tự động biên soạn và tải về file Word chia làm 2 phần rõ rệt:
     - **Phần 1 - Đề thi dành cho học sinh**: Trình bày đẹp mắt, chuẩn font chữ khảo thí, không lộ đáp án.
     - **Phần 2 - Đáp án & Hướng dẫn chấm dành cho giáo viên**: Bảng đáp án, dẫn chứng nguyên văn và giải thích chi tiết.

---

## IV. KIẾN TRÚC KỸ THUẬT PHẦN MỀM (FULL-STACK LOCAL)

* **Cấu trúc thư mục dự án**:
  ```text
  AI_KhaoThi_Antigravity/
  ├── backend/
  │   ├── app.py                # FastAPI main application
  │   ├── chunker.py            # Thematic Semantic Chunking engine
  │   ├── document_parser.py    # DOCX, PDF, TXT text extractor
  │   ├── llm_client.py         # Local HTTP Client kết nối LLM (KoboldCPP/llama-cpp)
  │   └── docx_exporter.py      # Module tạo file Word chia 2 phần (Đề thi & Đáp án)
  ├── frontend/
  │   ├── index.html            # Giao diện chính (Tailwind CSS, Drag & Drop, Checkboxes)
  │   ├── style.css             # Phong cách khảo thí tinh gọn
  │   └── app.js                # Quản lý luồng tương tác, gọi API backend, cập nhật tiến độ
  ├── models/                   # Thư mục chứa qwen2.5-7b-instruct-q4_k_m.gguf
  ├── requirements.txt          # fastapi, uvicorn, python-docx, pypdfium2
  └── Chay_Ung_Dung.bat         # File thực thi khởi chạy 1-click không cần quyền Admin
  ```
* **Cơ chế chạy không cần Admin**:
  - Backend FastAPI chạy trên cổng `127.0.0.1:8000`.
  - LLM Inference chạy trên cổng `127.0.0.1:5001`.
  - File `.bat` tự động kích hoạt cả hai dịch vụ và mở trình duyệt mặc định vào `http://127.0.0.1:8000`.
