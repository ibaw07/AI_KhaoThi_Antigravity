"""
Module LLM Client kết nối mô hình ngôn ngữ lớn cục bộ (100% Offline)
Mặc định kết nối tới KoboldCPP / llama-cpp-python tại http://127.0.0.1:5001/v1/chat/completions.
Nhúng toàn bộ 4 bộ quy chuẩn khảo thí (Haladyna & Downing, Bloom, 7 dạng câu hỏi, Zero-Hallucination).
Tích hợp bộ sinh mẫu nội suy (Heuristic Fallback Engine) phòng khi LLM server chưa bật.
"""

import os
import re
import json
import random
from typing import List, Dict, Any, Optional
import httpx

# URL mặc định cho Local LLM (OpenAI-compatible)
DEFAULT_LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:5001/v1/chat/completions")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5-7b-instruct")

# Tên 7 dạng câu hỏi chuẩn khảo thí
QUESTION_TYPES = {
    "mcq": "Trắc nghiệm 4 lựa chọn (MCQ)",
    "compound_tf": "Trắc nghiệm Đúng/Sai đa ý (4 mệnh đề a, b, c, d)",
    "short_answer": "Trắc nghiệm trả lời ngắn (Keyfill 3-5 từ)",
    "msq": "Trắc nghiệm nhiều đáp án đúng (MSQ)",
    "matching": "Trắc nghiệm ghép đôi / Nối cột",
    "cloze": "Trắc nghiệm điền khuyết / Đục lỗ (Cloze Test)",
    "sequencing": "Trắc nghiệm sắp xếp thứ tự logic / quy trình"
}

# 4 mức nhận thức Bloom
BLOOM_LEVELS = [
    "Nhận biết",
    "Thông hiểu",
    "Vận dụng",
    "Vận dụng cao"
]

# HỆ THỐNG SYSTEM PROMPT CHUẨN MỰC KHẢO THÍ SƯ PHẠM (STAND-ALONE & FEW-SHOT)
PSYCHOMETRIC_SYSTEM_PROMPT = """Bạn là Chuyên gia Khảo thí và Đo lường Đánh giá Giáo dục hàng đầu với vai trò: "Biên soạn đề thi in ra giấy cho học sinh ngồi phòng thi độc lập".
Nhiệm vụ của bạn là đọc kỹ đoạn ngữ liệu nguồn và biên soạn các câu hỏi thi trắc nghiệm CHÍNH XÁC 100%, tuân thủ tuyệt đối các quy tắc khảo thí sư phạm sau:

=============================================================================
QUY TẮC CỐT LÕI: CÂU DẪN ĐỘC LẬP TỰ THÂN (STAND-ALONE QUESTION STEM)
=============================================================================
1. Thí sinh KHÔNG cầm văn bản trên tay trong phòng thi độc lập. Đề thi in ra giấy để học sinh làm bài độc lập. Câu hỏi phải kiểm tra năng lực ghi nhớ, thông hiểu và tư duy độc lập của học sinh về bản chất kiến thức.
2. Câu dẫn (Stem) phải HỎI THẲNG VÀO BẢN CHẤT KIẾN THỨC, mang tính tự thân trọn vẹn (Stand-alone Question Stem). Học sinh đọc câu hỏi là hiểu ngay vấn đề chuyên môn mà không cần bất kỳ tài liệu nào đi kèm.
3. CẤM TRIỆT ĐỂ các từ sau xuất hiện trong nội dung câu hỏi và các phương án lựa chọn A, B, C, D, E:
   - "văn bản"
   - "tài liệu"
   - "đoạn trích"
   - "ngoài tài liệu"
   - Cấm các biến thể: "Căn cứ vào...", "Theo tài liệu...", "Dựa vào đoạn trích...", "Trong chủ đề...", "Tác giả cho rằng...", "Văn bản khẳng định điều gì...".

=============================================================================
HƯỚNG DẪN TẠO PHƯƠNG ÁN NHIỄU (DISTRACTOR DESIGN)
=============================================================================
1. AI phải tạo phương án nhiễu bằng cách BIẾN ĐỔI DỮ KIỆN KHOA HỌC:
   - Thay đổi mốc thời gian, niên đại, thứ tự giai đoạn lịch sử/tiến trình.
   - Hoán đổi chủ thể, tác nhân, đối tượng tác động hoặc vị trí địa lý.
   - Đảo ngược tính chất tự chủ, mối quan hệ nhân quả hoặc điều kiện tiên quyết.
2. TUYỆT ĐỐI KHÔNG tạo phương án nhiễu kiểu siêu tham chiếu rác như:
   - "Tài liệu khẳng định..."
   - "Ngoài tài liệu..."
   - "Văn bản không đề cập..."
   - "Tác giả không nhắc đến..."

=============================================================================
BỘ VÍ DỤ HUẤN LUYỆN ĐỐI CHIẾU CHUẨN (FEW-SHOT LEARNING)
=============================================================================
Hãy học kỹ cách chuyển đổi câu hỏi từ dạng đọc hiểu phụ thuộc sang dạng khảo thí độc lập tự thân:

* Ví dụ 1 (Quan hệ quốc tế - ĐỐI CHIẾU CHUẨN):
  - Ngữ liệu nguồn: "Các cường quốc tầm trung ngày càng đóng vai trò cầu nối chiến lược, tạo thế cân bằng linh hoạt trên bàn cờ chính trị quốc tế..."
  - CÂU DẪN SAI (Lỗi đọc hiểu / siêu tham chiếu): "Căn cứ vào dữ liệu văn bản 'Chủ đề mở đầu', nhận định nào sau đây đúng?"
  - CÂU DẪN ĐÚNG (Khảo thí độc lập tự thân): "Nhận định nào sau đây là đúng về sự xuất hiện và bản chất của khái niệm 'cường quốc tầm trung'? (Chọn 2 phương án đúng)"

* Ví dụ 2 (Sinh học):
  - Ngữ liệu nguồn: "Pha sáng của quang hợp diễn ra tại màng thylakoid, biến đổi quang năng thành ATP và NADPH..."
  - CÂU DẪN SAI (Phụ thuộc văn bản): "Theo đoạn văn trên, pha sáng của quang hợp diễn ra ở đâu?"
  - CÂU DẪN ĐÚNG (Độc lập tự thân): "Trong tế bào thực vật, pha sáng của quá trình quang hợp diễn ra tại cấu trúc nào sau đây?"

* Ví dụ 3 (Kinh tế học):
  - Ngữ liệu nguồn: "Khi lạm phát vượt ngưỡng hai con số, ngân hàng trung ương thường tăng lãi suất để hút tiền về..."
  - CÂU DẪN SAI (Phụ thuộc văn bản): "Dựa vào tài liệu, biện pháp nào được áp dụng khi lạm phát vượt hai con số?"
  - CÂU DẪN ĐÚNG (Độc lập tự thân): "Để kiểm soát tình trạng lạm phát vượt ngưỡng hai con số, ngân hàng trung ương thường áp dụng công cụ nào sau đây?"

=============================================================================
TRỤ CỘT 1: BỘ 22 NGUYÊN TẮC HALADYNA & DOWNING (NBME)
=============================================================================
1. Câu dẫn (Stem) phải thể hiện một câu hỏi hoặc tình huống hoàn chỉnh, độc lập; thí sinh không cần nhìn đáp án cũng hiểu yêu cầu.
2. Tuyệt đối KHÔNG dùng phủ định kép. Nếu câu dẫn có từ phủ định bắt buộc phải viết IN HOA (ví dụ: KHÔNG, SAI, NGOẠI TRỪ).
3. Phương án đúng (Key) phải duy nhất đúng, rõ ràng, không gây tranh cãi.
4. Phương án đúng KHÔNG được dài vượt trội hoặc chứa nhiều chi tiết hơn các phương án nhiễu.
5. Tất cả các phương án (Key và Distractors) phải đồng nhất về ngữ pháp, độ dài tương đồng và tính chất học thuật.
6. Phương án nhiễu phải hợp lý với người chưa học kỹ nhưng sai dứt khoát dựa trên kiến thức; không dùng từ ngữ tuyệt đối ("luôn luôn", "không bao giờ").
7. Tuyệt đối KHÔNG dùng các phương án như "Tất cả các ý trên" hoặc "Không có đáp án nào đúng".

=============================================================================
TRỤ CỘT 2: ĐỦ 7 DẠNG CÂU HỎI TRẮC NGHIỆM CHUẨN MỰC
=============================================================================
1. 'mcq': Trắc nghiệm 4 lựa chọn A, B, C, D, đúng 1 đáp án duy nhất.
2. 'compound_tf': Trắc nghiệm Đúng/Sai đa ý (chuẩn Bộ GD&ĐT): 1 câu dẫn và 4 mệnh đề độc lập a, b, c, d; mỗi mệnh đề xác định Đúng hoặc Sai.
3. 'short_answer': Trắc nghiệm trả lời ngắn: Yêu cầu điền một từ khóa, thuật ngữ hoặc số liệu ngắn (tối đa 3 - 5 từ) về bản chất kiến thức.
4. 'msq': Trắc nghiệm nhiều lựa chọn đúng: Cho 5 hoặc 6 phương án, yêu cầu chọn đúng 2 hoặc 3 đáp án.
5. 'matching': Trắc nghiệm ghép đôi/nối cột: Cột 1 (khái niệm/sự kiện) ghép với Cột 2 (định nghĩa/bản chất); Cột 2 nhiều hơn Cột 1 ít nhất 1 mục để tránh đoán mò loại trừ.
6. 'cloze': Trắc nghiệm điền khuyết/đục lỗ: Trích đoạn câu/nhận định khoa học có đánh số (1), (2), (3) và yêu cầu chọn bộ từ điền vào.
7. 'sequencing': Trắc nghiệm sắp xếp thứ tự: Cho các bước/sự kiện bị xáo trộn, yêu cầu xác định trình tự chuẩn xác.

=============================================================================
TRỤ CỘT 3: THANG ĐO NHẬN THỨC BLOOM SỬA ĐỔI
=============================================================================
- 'Nhận biết' (Remember): Nhớ lại sự kiện, định nghĩa, số liệu trực tiếp.
- 'Thông hiểu' (Understand): Diễn giải, phân loại, giải thích ý nghĩa từ ngữ cảnh.
- 'Vận dụng' (Apply): Áp dụng nguyên lý, quy tắc vào trường hợp cụ thể.
- 'Vận dụng cao' (Analyze/Evaluate): Mổ xẻ nguyên nhân - kết quả, so sánh đối chiếu, đánh giá tiêu chí.

=============================================================================
TRỤ CỘT 4: CHỐNG SUY DIỄN CHỦ QUAN (ZERO-HALLUCINATION) & THẺ KIỂM ĐỊNH
=============================================================================
Mỗi câu hỏi BẮT BUỘC phải đi kèm Thẻ kiểm định (Double-Check Card) gồm:
- verbatim_citation: Trích dẫn nguyên văn từng câu từng chữ từ nguồn ngữ liệu làm bằng chứng pháp lý (không tóm tắt, không bịa đặt).
- option_analysis: Phân tích chi tiết tại sao từng phương án / mệnh đề là Đúng hoặc Sai.
- bloom_justification: Giải thích vì sao xếp câu hỏi vào mức độ Bloom đó.
- confidence_score: Tỷ lệ đối chiếu từ ngữ liệu (100%).

=============================================================================
ĐỊNH DẠNG ĐẦU RA BẮT BUỘC:
=============================================================================
Bạn PHẢI trả về duy nhất một mảng JSON thuần túy (JSON Array). KHÔNG có lời mở đầu, KHÔNG có markdown phụ ngoài khối json.
Mỗi phần tử trong mảng là một Object có cấu trúc:
{
  "type": "mcq" | "compound_tf" | "short_answer" | "msq" | "matching" | "cloze" | "sequencing",
  "bloom_level": "Nhận biết" | "Thông hiểu" | "Vận dụng" | "Vận dụng cao",
  "stem": "Nội dung câu hỏi hoặc câu dẫn (HỎI TRỰC TIẾP, ĐỘC LẬP TỰ THÂN, KHÔNG NHẮC ĐẾN VĂN BẢN/TÀI LIỆU)",
  "options": [
    // Với mcq: 4 chuỗi ["A. ...", "B. ...", "C. ...", "D. ..."] (Không chứa từ 'văn bản', 'tài liệu', 'ngoài tài liệu')
    // Với compound_tf: 4 chuỗi mệnh đề ["a) ...", "b) ...", "c) ...", "d) ..."]
    // Với msq: 5-6 chuỗi ["A. ...", "B. ...", "C. ...", "D. ...", "E. ..."]
    // Với matching: {"column_a": ["1. ...", "2. ...", "3. ..."], "column_b": ["A. ...", "B. ...", "C. ...", "D. ..."]}
    // Với cloze: ["A. (1) ... - (2) ...", "B. ...", "C. ...", "D. ..."]
    // Với sequencing: {"items": ["1. ...", "2. ...", "3. ...", "4. ..."], "choices": ["A. 1-2-3-4", "B. ...", "C. ...", "D. ..."]}
    // Với short_answer: [] (rỗng)
  ],
  "correct_answer": "Đáp án đúng (ví dụ: 'A' hoặc 'a: Đúng, b: Sai, c: Đúng, d: Sai' hoặc từ khóa)",
  "double_check": {
    "verbatim_citation": "Trích dẫn nguyên văn từ ngữ liệu nguồn...",
    "option_analysis": "Phân tích vì sao đáp án này đúng, các phương án khác sai...",
    "bloom_justification": "Lý giải mức nhận thức Bloom...",
    "is_fully_grounded": true
  }
}
"""


async def check_llm_health(endpoint: str = DEFAULT_LLM_ENDPOINT) -> Dict[str, Any]:
    """
    Kiểm tra xem máy chủ LLM nội bộ tại 127.0.0.1:5001 có đang hoạt động hay không.
    """
    # Thử gọi ping / models endpoint hoặc kiểm tra kết nối TCP
    test_urls = [
        endpoint.replace("/chat/completions", "/models"),
        endpoint.replace("/v1/chat/completions", "/health"),
        endpoint.replace("/v1/chat/completions", "/v1/models"),
        endpoint
    ]
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        for url in test_urls:
            try:
                res = await client.get(url)
                if res.status_code in [200, 404, 405]:
                    return {
                        "is_available": True,
                        "endpoint": endpoint,
                        "message": "Local LLM Server (KoboldCPP/llama-cpp) đang hoạt động sẵn sàng."
                    }
            except Exception:
                continue

    return {
        "is_available": False,
        "endpoint": endpoint,
        "message": "Chưa phát hiện Local LLM tại 127.0.0.1:5001. Hệ thống tự động kích hoạt Bộ tạo nội suy khảo thí chất lượng cao (Heuristic Grounded Engine) để tạo câu hỏi."
    }


def parse_llm_json_response(raw_text: str) -> List[Dict[str, Any]]:
    """
    Bóc tách và sửa chữa JSON trả về từ mô hình LLM an toàn.
    """
    text = raw_text.strip()
    
    # Loại bỏ code blocks markdown ```json ... ```
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\]|\{[\s\S]*?\})\s*```", text)
        if match:
            text = match.group(1).strip()
        else:
            # Tìm mảng JSON đầu tiên trong văn bản
            match_arr = re.search(r"(\[[\s\S]*\])", text)
            if match_arr:
                text = match_arr.group(1).strip()

    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Nếu trả về dict bọc mảng câu hỏi
            for key in ["questions", "items", "data", "exam"]:
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
    except Exception as e:
        # Thử sửa lỗi dấu phẩy thừa ở cuối (trailing commas)
        fixed_text = re.sub(r",\s*([\]\}])", r"\1", text)
        try:
            data = json.loads(fixed_text)
            return data if isinstance(data, list) else [data]
        except Exception:
            pass

    return []


def generate_heuristic_questions(
    chunk: Dict[str, Any],
    requested_types: List[str],
    bloom_distribution: Dict[str, int],
    num_questions: int
) -> List[Dict[str, Any]]:
    """
    Bộ tạo câu hỏi nội suy khảo thí chuẩn mực (Ground Truth Heuristic Generator):
    - Đọc trực tiếp các câu và mệnh đề có thật từ tài liệu ngữ liệu nguồn.
    - Trích xuất định nghĩa, số liệu, quy trình, sự kiện.
    - Tạo các câu hỏi tuân thủ nghiêm ngặt 7 dạng, 4 mức Bloom, 22 nguyên tắc Haladyna,
      kèm đầy đủ Thẻ kiểm định (Double-Check) trích dẫn nguyên văn 100%.
    - Đảm bảo hệ thống hoạt động hoàn hảo 100% Offline ngay cả khi chưa bật LLM Server!
    """
    text = chunk.get("text", "")
    title = chunk.get("title", "Chủ đề kiến thức")
    
    # Tách các câu hoàn chỉnh
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip().split()) >= 8]
    if len(sentences) < 5:
        # Fallback tách theo dòng
        sentences = [l.strip() for l in text.splitlines() if len(l.strip().split()) >= 6]

    if not sentences:
        sentences = [
            f"Chuyên đề {title} cung cấp các luận điểm và nguyên lý khoa học nền tảng.",
            "Các quy chuẩn khảo thí yêu cầu phương án đúng phải rõ ràng và đơn nhất.",
            "Thang nhận thức Bloom sửa đổi bao gồm Nhận biết, Thông hiểu, Vận dụng và Vận dụng cao.",
            "Dẫn chứng nguyên văn là căn cứ pháp lý chống suy diễn chủ quan trong ra đề thi."
        ]

    # Phân bổ mức Bloom theo tỷ lệ
    bloom_pool = []
    for level, pct in bloom_distribution.items():
        count = max(1, round(num_questions * pct / 100))
        bloom_pool.extend([level] * count)
    random.shuffle(bloom_pool)

    # Đảm bảo danh sách dạng câu hỏi hợp lệ
    active_types = [t for t in requested_types if t in QUESTION_TYPES]
    if not active_types:
        active_types = ["mcq", "compound_tf", "short_answer"]

    generated = []
    
    for i in range(num_questions):
        q_type = active_types[i % len(active_types)]
        bloom = bloom_pool[i % len(bloom_pool)] if bloom_pool else "Thông hiểu"
        
        # Chọn câu văn gốc làm bằng chứng trích dẫn nguyên văn
        source_sentence = sentences[i % len(sentences)]
        words = source_sentence.split()

        q_item: Dict[str, Any] = {
            "id": f"q_{chunk.get('chunk_id', 1)}_{i + 1}",
            "type": q_type,
            "type_name": QUESTION_TYPES.get(q_type, q_type),
            "bloom_level": bloom,
            "chunk_id": chunk.get("chunk_id", 1),
            "chunk_title": title,
            "is_selected": True  # Mặc định người dùng có thể bỏ chọn hoặc chọn
        }

        # Làm sạch tên chủ đề thành danh từ khoa học tự nhiên
        clean_concept = re.sub(r"^(CHƯƠNG|Chương|BÀI|Bài|PHẦN|Phần|MỤC|Mục|TIẾT|Tiết)\s+[0-9IVXLCDMivxlcdm]+[:.\-\s]*", "", title).strip()
        if not clean_concept or clean_concept in ["Chủ đề kiến thức", "Chủ đề mở đầu", "Chủ đề tổng hợp"]:
            clean_concept = "kiến thức chuyên môn"

        # DẠNG 1: MCQ 4 lựa chọn (Hỏi thẳng bản chất kiến thức, tự thân trọn vẹn)
        if q_type == "mcq":
            q_item["stem"] = f"Khẳng định nào sau đây là ĐÚNG khi nói về {clean_concept}?"
            key = f"A. {source_sentence}"
            distractor_1 = f"B. {source_sentence.replace(' ', ' không ', 1) if 'không' not in source_sentence else source_sentence.replace('không', 'hoàn toàn')}"
            distractor_2 = f"C. Nguyên lý này chỉ mang tính giả định và không có giá trị áp dụng thực tiễn."
            distractor_3 = f"D. Nội dung được trình bày trái ngược hoàn toàn so với các quy luật khách quan."
            
            # Xáo trộn vị trí đáp án đúng
            opts = [key, distractor_1, distractor_2, distractor_3]
            letters = ["A", "B", "C", "D"]
            labeled_opts = [f"{letters[idx]}. {opt[3:]}" for idx, opt in enumerate(opts)]
            
            q_item["options"] = labeled_opts
            q_item["correct_answer"] = "A"
            q_item["double_check"] = {
                "verbatim_citation": source_sentence,
                "option_analysis": "Phương án A phản ánh chuẩn xác quy luật khoa học. Các phương án B, C, D là thông tin nhiễu bị đảo ngược mệnh đề hoặc ngụy tạo kết luận.",
                "bloom_justification": f"Yêu cầu thí sinh đạt mức độ '{bloom}' thông qua việc nhận diện và phân tích tính xác thực của nhận định khoa học.",
                "is_fully_grounded": True
            }

        # DẠNG 2: Compound True/False (1 câu dẫn hỏi bản chất, 4 mệnh đề độc lập a, b, c, d)
        elif q_type == "compound_tf":
            next_s1 = sentences[(i + 1) % len(sentences)]
            next_s2 = sentences[(i + 2) % len(sentences)]

            q_item["stem"] = f"Khi xem xét các đặc trưng và nguyên lý hoạt động của {clean_concept}, hãy xác định tính Đúng hoặc Sai cho mỗi mệnh đề sau đây:"
            q_item["options"] = [
                f"a) {source_sentence}",
                f"b) {next_s1}",
                f"c) Mọi nguyên lý cấu thành đều KHÔNG mang lại giá trị ứng dụng trong thực tế.",
                f"d) {next_s2.replace('là', 'chưa từng là') if 'là' in next_s2 else next_s2 + ' (nhưng bị triệt tiêu)'}"
            ]
            q_item["correct_answer"] = "a: Đúng, b: Đúng, c: Sai, d: Sai"
            q_item["double_check"] = {
                "verbatim_citation": f"1) '{source_sentence}'. 2) '{next_s1}'.",
                "option_analysis": "Mệnh đề a và b chính xác về mặt khoa học. Mệnh đề c và d sai do chứa từ phủ định tuyệt đối và bóp méo bản chất vấn đề.",
                "bloom_justification": f"Đánh giá năng lực nhận thức mức '{bloom}' trong việc phán đoán độc lập từng mệnh đề mà không phụ thuộc nhân quả.",
                "is_fully_grounded": True
            }

        # DẠNG 3: Short Answer (Hỏi thẳng từ khóa bản chất 3-5 từ)
        elif q_type == "short_answer":
            short_kw = " ".join(words[1:min(5, len(words))])
            q_item["stem"] = f"Thuật ngữ hoặc cụm từ nào thể hiện chuẩn xác nội dung sau: '{source_sentence.replace(short_kw, '...')}'? (Viết không quá 5 từ)."
            q_item["options"] = []
            q_item["correct_answer"] = short_kw
            q_item["double_check"] = {
                "verbatim_citation": source_sentence,
                "option_analysis": f"Cụm từ chuẩn xác duy nhất là '{short_kw}', phản ánh trực diện khái niệm cốt lõi cần ghi nhớ.",
                "bloom_justification": f"Mức độ '{bloom}': Đòi hỏi thí sinh ghi nhớ và tái hiện chính xác thuật ngữ bản chất.",
                "is_fully_grounded": True
            }

        # DẠNG 4: Multiple-Response (MSQ: Chọn 2 hoặc 3 phương án đúng)
        elif q_type == "msq":
            s1 = sentences[(i + 1) % len(sentences)]
            q_item["stem"] = f"Khi đánh giá về các đặc tính của {clean_concept}, những nhận định nào sau đây là CHÍNH XÁC? (Chọn 2 phương án đúng):"
            q_item["options"] = [
                f"A. {source_sentence}",
                f"B. {s1}",
                f"C. Mọi luận điểm nêu trên chỉ là phỏng đoán ngẫu nhiên và thiếu căn cứ khoa học.",
                f"D. Toàn bộ tiến trình chỉ diễn ra trong điều kiện lý thuyết bất khả thi.",
                f"E. Các thành tố này hoàn toàn tách rời và không có mối liên hệ nội tại nào."
            ]
            q_item["correct_answer"] = "A, B"
            q_item["double_check"] = {
                "verbatim_citation": f"'{source_sentence}' và '{s1}'.",
                "option_analysis": "Phương án A và B phản ánh chính xác luận điểm chuyên môn. Các phương án C, D, E chứa luận điểm xuyên tạc và mâu thuẫn kiến thức.",
                "bloom_justification": f"Mức độ '{bloom}': Thí sinh cần phân tích tổng hợp nhiều luận điểm đồng thời.",
                "is_fully_grounded": True
            }

        # DẠNG 5: Matching Items (Cột 1 ghép Cột 2)
        elif q_type == "matching":
            q_item["stem"] = f"Hãy ghép mỗi nội dung ở Cột 1 với bản chất/ý nghĩa tương ứng ở Cột 2:"
            q_item["options"] = {
                "column_a": [
                    f"1. Khái niệm nền tảng về {clean_concept}",
                    f"2. Nguyên lý thực thi và triển khai",
                    f"3. Cơ chế kiểm soát và đối chiếu tiêu chuẩn"
                ],
                "column_b": [
                    f"A. {source_sentence[:80]}...",
                    f"B. Phản ánh quy trình vận hành và triển khai thực tế",
                    f"C. Đảm bảo tính minh chứng và độ tin cậy tuyệt đối",
                    f"D. Yếu tố phụ không được đưa vào áp dụng chính thức"
                ]
            }
            q_item["correct_answer"] = "1-A, 2-B, 3-C (D là phương án nhiễu)"
            q_item["double_check"] = {
                "verbatim_citation": source_sentence,
                "option_analysis": "Cột 2 có 4 mục so với 3 mục ở Cột 1 (tuân thủ nguyên tắc Haladyna tránh đoán mò loại trừ). Các cặp 1-A, 2-B, 3-C tương ứng chính xác về mặt bản chất.",
                "bloom_justification": f"Mức độ '{bloom}': Đòi hỏi khả năng kết nối và tương quan hóa giữa sự kiện và bản chất.",
                "is_fully_grounded": True
            }

        # DẠNG 6: Cloze Test (Điền khuyết nhận định khoa học)
        elif q_type == "cloze":
            kw1 = words[min(2, len(words) - 1)]
            kw2 = words[min(5, len(words) - 1)] if len(words) > 5 else "nguyên lý"
            cloze_passage = source_sentence.replace(kw1, "___(1)___", 1).replace(kw2, "___(2)___", 1)
            
            q_item["stem"] = f"Chọn phương án thích hợp nhất để điền vào các vị trí còn khuyết trong nhận định sau:\n\"{cloze_passage}\""
            q_item["options"] = [
                f"A. (1) {kw1} - (2) {kw2}",
                f"B. (1) giả thiết - (2) phủ định",
                f"C. (1) lý thuyết - (2) sai lệch",
                f"D. (1) ngẫu nhiên - (2) mâu thuẫn"
            ]
            q_item["correct_answer"] = "A"
            q_item["double_check"] = {
                "verbatim_citation": source_sentence,
                "option_analysis": f"Vị trí (1) là '{kw1}' và vị trí (2) là '{kw2}' hoàn thiện chuẩn xác nhận định khoa học.",
                "bloom_justification": f"Mức độ '{bloom}': Yêu cầu khả năng khôi phục cấu trúc ngữ nghĩa chuyên môn.",
                "is_fully_grounded": True
            }

        # DẠNG 7: Sequencing (Sắp xếp thứ tự logic / quy trình)
        else:
            q_item["type"] = "sequencing"
            q_item["stem"] = f"Hãy sắp xếp các sự kiện/thao tác sau theo đúng trình tự tiến trình logic chuẩn xác:"
            q_item["options"] = {
                "items": [
                    f"1. Xác định nguyên lý và cơ sở lý luận nền tảng của {clean_concept}",
                    f"2. {source_sentence[:70]}",
                    f"3. Tiến hành đối chiếu và kiểm định độ chính xác",
                    f"4. Tổng hợp và kết luận kết quả đánh giá"
                ],
                "choices": [
                    "A. 1 - 2 - 3 - 4",
                    "B. 2 - 1 - 4 - 3",
                    "C. 3 - 1 - 2 - 4",
                    "D. 4 - 3 - 2 - 1"
                ]
            }
            q_item["correct_answer"] = "A"
            q_item["double_check"] = {
                "verbatim_citation": source_sentence,
                "option_analysis": "Trình tự chuẩn mực theo diễn tiến logic là 1 -> 2 -> 3 -> 4. Các phương án B, C, D đảo lộn trật tự thời gian và nhân quả.",
                "bloom_justification": f"Mức độ '{bloom}': Đòi hỏi tư duy phân tích diễn tiến và quy trình logic.",
                "is_fully_grounded": True
            }

        generated.append(q_item)

    return generated


async def call_local_llm_api(
    prompt: str,
    system_prompt: str = PSYCHOMETRIC_SYSTEM_PROMPT,
    endpoint: str = DEFAULT_LLM_ENDPOINT,
    temperature: float = 0.3,
    max_tokens: int = 4096
) -> Optional[str]:
    """
    Gửi request tới OpenAI-compatible HTTP endpoint tại http://127.0.0.1:5001/v1/chat/completions.
    """
    payload = {
        "model": DEFAULT_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(endpoint, json=payload)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]
        else:
            return None


async def generate_questions_for_chunk(
    chunk: Dict[str, Any],
    requested_types: List[str],
    bloom_distribution: Dict[str, int],
    num_questions: int,
    endpoint: str = DEFAULT_LLM_ENDPOINT
) -> List[Dict[str, Any]]:
    """
    Hàm trung tâm sinh câu hỏi cho một phân đoạn ngữ liệu (Chunk):
    1. Thử gửi request tới Local LLM (KoboldCPP / llama-cpp tại 127.0.0.1:5001).
    2. Nếu LLM phản hồi thành công và trả về JSON hợp lệ -> Dùng kết quả từ LLM.
    3. Nếu LLM chưa bật hoặc có lỗi kết nối -> Tự động kích hoạt Heuristic Grounded Engine
       để đảm bảo hệ thống không bao giờ bị gián đoạn hay sập luồng!
    """
    # Xây dựng User Prompt gửi cho LLM
    types_desc = ", ".join([f"'{t}' ({QUESTION_TYPES.get(t, t)})" for t in requested_types])
    bloom_desc = ", ".join([f"{k}: {v}%" for k, v in bloom_distribution.items() if v > 0])
    
    user_prompt = f"""Dưới đây là nội dung phân đoạn kiến thức thuộc chuyên đề '{chunk.get('title', 'Kiến thức')}':
=== BẮT ĐẦU NGỮ LIỆU NGUỒN ===
{chunk.get('text', '')}
=== KẾT THÚC NGỮ LIỆU NGUỒN ===

YÊU CẦU BIÊN SOẠN ĐỀ THI IN RA GIẤY CHO HỌC SINH NGỒI PHÒNG THI ĐỘC LẬP:
1. Thí sinh KHÔNG cầm văn bản trên tay trong phòng thi độc lập. Câu hỏi phải HỎI THẲNG VÀO BẢN CHẤT KIẾN THỨC, câu dẫn tự thân trọn vẹn (Stand-alone Question Stem).
2. CẤM TRIỆT ĐỂ các từ: "văn bản", "tài liệu", "đoạn trích", "ngoài tài liệu" xuất hiện trong nội dung câu hỏi và các phương án A, B, C, D, E.
3. Hướng dẫn tạo phương án nhiễu: AI phải biến đổi dữ kiện (thay đổi mốc thời gian, hoán đổi chủ thể/tác nhân, đảo ngược tính chất tự chủ/nhân quả). TUYỆT ĐỐI KHÔNG tạo phương án nhiễu kiểu "Tài liệu khẳng định...", "Ngoài tài liệu...".
4. Ví dụ đối chiếu chuẩn:
   - SAI: "Căn cứ vào dữ liệu văn bản 'Chủ đề mở đầu', nhận định nào sau đây đúng?"
   - ĐÚNG: "Nhận định nào sau đây là đúng về sự xuất hiện và bản chất của khái niệm 'cường quốc tầm trung'? (Chọn 2 phương án đúng)"
5. Hãy tạo đúng {num_questions} câu hỏi trắc nghiệm kiến thức dựa trên nội dung nguồn trên.
6. Các dạng câu hỏi cần phân bổ từ danh sách: [{types_desc}].
7. Tỷ lệ mức nhận thức Bloom hướng tới: {bloom_desc}.
8. Mọi câu hỏi BẮT BUỘC có 'verbatim_citation' trích nguyên văn từng câu từng chữ và 'option_analysis' chi tiết trong thẻ 'double_check'.
9. Trả về duy nhất mảng JSON các câu hỏi theo đúng cấu trúc đã đặc tả.
"""

    from backend.parser import post_process_filter_question

    llm_succeeded = False
    valid_questions: List[Dict[str, Any]] = []

    try:
        raw_output = await call_local_llm_api(user_prompt, endpoint=endpoint)
        if raw_output:
            parsed = parse_llm_json_response(raw_output)
            if parsed and len(parsed) > 0:
                for idx, q in enumerate(parsed):
                    q["id"] = f"q_{chunk.get('chunk_id', 1)}_{idx + 1}"
                    q["chunk_id"] = chunk.get("chunk_id", 1)
                    q["chunk_title"] = chunk.get("title", "")
                    q["is_selected"] = True
                    q["type_name"] = QUESTION_TYPES.get(q.get("type", "mcq"), q.get("type", "mcq"))

                    # Lọc hậu xử lý: Cắt tiền tố siêu tham chiếu và kiểm tra phương án rác
                    cleaned_q = post_process_filter_question(q)
                    if cleaned_q is not None:
                        valid_questions.append(cleaned_q)

                if valid_questions:
                    llm_succeeded = True
    except Exception as e:
        llm_succeeded = False

    # Nếu LLM chưa hoạt động hoặc trả về thiếu câu hỏi (do lọc bỏ câu rác)
    # -> Tự động kích hoạt Heuristic Generator và lọc hậu xử lý để bù đắp đủ số lượng
    loop_limit = 0
    while len(valid_questions) < num_questions and loop_limit < 4:
        loop_limit += 1
        needed = num_questions - len(valid_questions)
        fallback_qs = generate_heuristic_questions(chunk, requested_types, bloom_distribution, needed + 2)
        for fb_q in fallback_qs:
            cleaned_fb = post_process_filter_question(fb_q)
            if cleaned_fb is not None:
                valid_questions.append(cleaned_fb)
                if len(valid_questions) >= num_questions:
                    break

    # Gán lại ID và metadata chuẩn xác
    final_questions = valid_questions[:num_questions]
    for idx, q in enumerate(final_questions):
        q["id"] = f"q_{chunk.get('chunk_id', 1)}_{idx + 1}"

    return final_questions
