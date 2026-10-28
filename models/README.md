# HƯỚNG DẪN THIẾT LẬP MÔ HÌNH SUY LUẬN CỤC BỘ (LOCAL LLM)

Thư mục này được thiết kế để chứa mô hình ngôn ngữ lớn chạy ngoại tuyến (100% Offline):
- **Tên mô hình khuyến nghị**: `qwen2.5-7b-instruct-q4_k_m.gguf`
- **Dung lượng**: ~4.68 GB
- **Yêu cầu RAM**: ~6.5 GB (tối ưu hóa cho hệ thống 16GB RAM của Core i5-14500)

---

## 1. Tải mô hình GGUF
Người dùng có thể tải file GGUF từ Hugging Face:
- Link: `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF`
- Chọn file: `qwen2.5-7b-instruct-q4_k_m.gguf` và lưu trực tiếp vào thư mục `models/` này.

---

## 2. Khởi chạy LLM Server (KoboldCPP hoặc llama.cpp)
Để tương thích hoàn hảo với cổng `http://127.0.0.1:5001/v1/chat/completions`:

### Lựa chọn A: Dùng KoboldCPP (Giao diện đơn giản, không cần Admin)
1. Tải `koboldcpp_nocuda.exe` (cho CPU) hoặc `koboldcpp.exe` từ GitHub Releases.
2. Mở KoboldCPP, chọn mô hình `models/qwen2.5-7b-instruct-q4_k_m.gguf`.
3. Cài đặt thông số tối ưu cho **Intel Core i5-14500**:
   - **Threads**: 12 luồng (tận dụng trọn vẹn 6 P-Core + P-Hyperthreads).
   - **Context Size**: 8192 tokens.
   - **Port**: 5001.
4. Nhấn **Launch**.

### Lựa chọn B: Dùng llama-server (llama.cpp)
```bash
llama-server.exe -m models/qwen2.5-7b-instruct-q4_k_m.gguf --port 5001 -c 8192 -t 12 --host 127.0.0.1
```

---

## 3. Chế độ Fallback thông minh
Nếu chưa tải mô hình hoặc chưa bật cổng `127.0.0.1:5001`, hệ thống AI Khảo Thí Antigravity sẽ **tự động kích hoạt Bộ sinh nội suy khảo thí chất lượng cao (Grounded Heuristic Engine)** dựa trực tiếp trên văn bản tài liệu đã nạp. Do đó, ứng dụng luôn sẵn sàng sử dụng 100% mà không bao giờ bị dừng gián đoạn!
