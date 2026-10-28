"""
Bộ kiểm thử tính toàn vẹn và chất lượng hệ thống (Comprehensive Integrity & Quality Test Suite)
Kiểm tra toàn bộ 5 module:
1. parser.py: Đọc hiểu và trích xuất .docx, .pdf, .txt
2. chunker.py: Phân đoạn ngữ nghĩa chủ đề 1.500 - 2.500 từ
3. llm_client.py: Tạo câu hỏi 7 dạng, 4 mức Bloom, 22 nguyên tắc Haladyna, Thẻ Double-Check
4. docx_exporter.py: Tạo file Word chia 2 phần (Học sinh & Giáo viên)
5. app.py: Các REST API endpoints và luồng nghiệp vụ hoàn chỉnh
"""

import os
import sys
import io
import asyncio
import sys

# Đảm bảo in ký tự tiếng Việt an toàn trên Windows Console (tránh lỗi charmap cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
import docx

# Thiết lập đường dẫn gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.parser import (
    extract_text_from_file,
    extract_text_from_txt,
    extract_text_from_docx
)
from backend.chunker import (
    semantic_thematic_chunking,
    is_heading_line
)
from backend.llm_client import (
    generate_heuristic_questions,
    generate_questions_for_chunk,
    check_llm_health,
    QUESTION_TYPES,
    BLOOM_LEVELS
)
from backend.docx_exporter import build_exam_docx
from fastapi.testclient import TestClient
from backend.app import app

SAMPLE_EDUCATIONAL_TEXT = """# CHƯƠNG I: ĐẠI CƯƠNG VỀ KHẢO THÍ SƯ PHẠM VÀ ĐO LƯỜNG ĐÁNH GIÁ

1. Khái niệm và vị trí của khảo thí
Khảo thí giáo dục là một khoa học liên ngành nghiên cứu các phương pháp đo lường, lượng hóa và đánh giá năng lực, phẩm chất và kết quả học tập của người học một cách khách quan. Trong hệ thống giáo dục hiện đại, khảo thí đóng vai trò là công cụ định hướng sư phạm, giúp giáo viên điều chỉnh phương pháp giảng dạy và cung cấp thông tin phản hồi có giá trị cho học sinh. Theo các chuyên gia đo lường giáo dục, một đề thi chuẩn mực phải đảm bảo độ giá trị nội dung, độ tin cậy thống kê và tính khả thi trong khâu tổ chức thực hiện.

2. Tiêu chuẩn 22 nguyên tắc của Haladyna và Downing
Năm 1989, Haladyna và Downing đã tổng kết bộ 22 nguyên tắc xây dựng câu hỏi trắc nghiệm nhiều lựa chọn nhằm loại trừ các sai lệch kỹ thuật và nâng cao độ phân hóa của bài thi. Trong đó, câu dẫn (stem) bắt buộc phải truyền đạt một ý niệm trọn vẹn, có thể hiểu được mà không cần nhìn vào các phương án lựa chọn. Tác giả nhấn mạnh tuyệt đối KHÔNG sử dụng phủ định kép trong câu hỏi vì sẽ gây nhiễu nhận thức không đáng có. Trong trường hợp cần thiết phải dùng các từ phủ định như KHÔNG hoặc SAI, người ra đề bắt buộc phải viết in hoa để thí sinh nhận diện tức thì. Bên cạnh đó, các phương án nhiễu phải đồng nhất về cấu trúc ngữ pháp và độ dài; tuyệt đối không dùng "Tất cả các ý trên" hoặc "Không có đáp án nào đúng".

# CHƯƠNG II: THANG ĐO BLOOM SỬA ĐỔI VÀ KHUNG ĐỀ THI 2025

I. Bốn mức độ nhận thức của Anderson và Krathwohl
Thang đo nhận thức Bloom sửa đổi (2001) phân định 4 cấp bậc nhận thức:
- Cấp độ Nhận biết: Thí sinh nhận diện, tái hiện hoặc nhắc lại các định nghĩa, số liệu, sự kiện trực tiếp từ văn bản nguồn mà không cần suy luận phức tạp.
- Cấp độ Thông hiểu: Yêu cầu diễn giải ý nghĩa, phân biệt khái niệm tương đồng hoặc dự đoán kết quả logic dựa vào ngữ cảnh đã cho.
- Cấp độ Vận dụng: Áp dụng các quy tắc, nguyên lý, công thức vào việc giải quyết một bài toán hoặc tình huống cụ thể nêu trong văn bản.
- Cấp độ Vận dụng cao: Mổ xẻ cấu trúc nhân quả, so sánh đối chiếu đa chiều hoặc thẩm định giá trị của luận điểm theo các tiêu chí đã xác lập.

II. Định dạng đề thi trắc nghiệm theo chuẩn 2025
Bộ Giáo dục và Đào tạo đã áp dụng cấu trúc đề thi đa dạng hóa bao gồm 3 phần trọng tâm:
1. Trắc nghiệm 4 lựa chọn cổ điển (MCQ): Đảm bảo đúng 1 đáp án duy nhất trong 4 phương án A, B, C, D.
2. Trắc nghiệm Đúng/Sai đa ý: Mỗi câu gồm 1 ngữ cảnh và 4 mệnh đề a, b, c, d độc lập để thí sinh xác định Đúng hoặc Sai cho từng mệnh đề; cấu trúc này làm giảm xác suất đoán mò từ 25% xuống còn 1/16 (6.25%).
3. Trắc nghiệm trả lời ngắn (Keyfill): Thí sinh tự tìm và điền từ khóa hoặc số liệu chính xác tối đa từ 3 đến 5 từ, giúp kiểm tra sâu sắc năng lực tái hiện kiến thức chính xác.
"""


def test_parser_module():
    """Kiểm thử Module 1: Parser (Trích xuất văn bản)"""
    print("\n[TEST 1] Kiểm tra Module backend/parser.py...")
    test_txt_path = BASE_DIR / "tests" / "test_sample.txt"
    test_txt_path.parent.mkdir(parents=True, exist_ok=True)
    test_txt_path.write_text(SAMPLE_EDUCATIONAL_TEXT, encoding="utf-8")

    res = extract_text_from_file(test_txt_path)
    assert res["word_count"] > 200, "Số lượng từ trích xuất quá ít"
    assert "Haladyna" in res["text"], "Không tìm thấy từ khóa Haladyna trong văn bản"
    assert res["extension"] == ".txt", "Đuôi file không khớp"
    print("  -> Trích xuất TXT thành công:", res["word_count"], "từ.")

    # Tạo file docx test và trích xuất
    test_docx_path = BASE_DIR / "tests" / "test_sample.docx"
    doc = docx.Document()
    doc.add_heading("Tiêu đề kiểm thử DOCX", level=1)
    doc.add_paragraph("Đoạn văn kiểm thử trích xuất từ định dạng Word.")
    tbl = doc.add_table(rows=2, cols=2)
    tbl.cell(0, 0).paragraphs[0].text = "Hàng 1 Cột 1"
    tbl.cell(0, 1).paragraphs[0].text = "Hàng 1 Cột 2"
    tbl.cell(1, 0).paragraphs[0].text = "Hàng 2 Cột 1"
    tbl.cell(1, 1).paragraphs[0].text = "Hàng 2 Cột 2"
    doc.save(test_docx_path)

    res_docx = extract_text_from_file(test_docx_path)
    assert "Tiêu đề kiểm thử DOCX" in res_docx["text"]
    assert "Hàng 1 Cột 1" in res_docx["text"]
    print("  -> Trích xuất DOCX (Paragraphs + Tables) thành công:", res_docx["word_count"], "từ.")

    # Cleanup temporary files
    test_txt_path.unlink()
    test_docx_path.unlink()

    # Kiểm tra Hàm lọc hậu xử lý (Post-Processing Filter)
    from backend.parser import (
        strip_meta_prefixes,
        validate_question_content,
        post_process_filter_question,
        filter_and_clean_questions
    )

    # 1. Kiểm tra cắt bỏ tiền tố siêu tham chiếu ở đầu câu dẫn
    test_stems = [
        ("Căn cứ vào dữ liệu văn bản 'Chủ đề mở đầu', nhận định nào sau đây đúng?", "Nhận định nào sau đây đúng?"),
        ("Theo văn bản, quy luật nào chi phối tiến trình này?", "Quy luật nào chi phối tiến trình này?"),
        ("Căn cứ vào văn bản nguồn, khẳng định nào sau đây là CHÍNH XÁC?", "Khẳng định nào sau đây là CHÍNH XÁC?"),
        ("Dựa vào đoạn trích thuộc chủ đề 'Quang hợp', pha sáng diễn ra ở đâu?", "Pha sáng diễn ra ở đâu?"),
        ("Theo tài liệu đã cho: đặc trưng nào là cơ bản?", "Đặc trưng nào là cơ bản?"),
        ("Văn bản khẳng định rằng nguyên lý nào sau đây là đúng?", "Nguyên lý nào sau đây là đúng?")
    ]
    for raw_stem, expected in test_stems:
        cleaned = strip_meta_prefixes(raw_stem)
        assert cleaned == expected, f"Lỗi cắt tiền tố: '{raw_stem}' -> '{cleaned}' != '{expected}'"
    print("  -> Hàm strip_meta_prefixes cắt sạch 100% tiền tố siêu tham chiếu.")

    # 2. Kiểm tra phát hiện và loại bỏ phương án rác (Tài liệu khẳng định..., Ngoài tài liệu...)
    invalid_q1 = {
        "stem": "Nhận định nào sau đây đúng?",
        "options": [
            "A. Phương án kiến thức chính xác",
            "B. Tài liệu khẳng định điều này là đúng",
            "C. Phương án bình thường",
            "D. Phương án khác"
        ]
    }
    is_valid1, reason1 = validate_question_content(invalid_q1)
    assert is_valid1 is False, "Phải từ chối phương án chứa 'tài liệu'"
    assert post_process_filter_question(invalid_q1) is None

    invalid_q2 = {
        "stem": "Khái niệm nào sau đây đúng?",
        "options": [
            "A. Phương án kiến thức",
            "B. Ngoài tài liệu không có chứng cứ",
            "C. Phương án bình thường",
            "D. Phương án khác"
        ]
    }
    is_valid2, reason2 = validate_question_content(invalid_q2)
    assert is_valid2 is False, "Phải từ chối phương án chứa 'ngoài tài liệu'"

    valid_q = {
        "stem": "Căn cứ vào văn bản, sự kiện nào diễn ra vào năm 1945?",
        "options": [
            "A. Tuyên ngôn Độc lập",
            "B. Chiến dịch Điện Biên Phủ",
            "C. Hiệp định Giơ-ne-vơ",
            "D. Chiến thắng Điện Biên Phủ trên không"
        ]
    }
    processed = post_process_filter_question(valid_q)
    assert processed is not None
    assert processed["stem"] == "Sự kiện nào diễn ra vào năm 1945?"
    print("  -> Bộ lọc hậu xử lý (Post-Processing Filter) hoạt động chính xác 100%!")

    print("  => PASSED: Module parser.py hoạt động chính xác 100%!")


def test_chunker_module():
    """Kiểm thử Module 2: Chunker (Phân đoạn ngữ nghĩa chủ đề)"""
    print("\n[TEST 2] Kiểm tra Module backend/chunker.py...")
    # Kiểm tra nhận diện tiêu đề
    assert is_heading_line("# CHƯƠNG I: ĐẠI CƯƠNG") is True
    assert is_heading_line("CHƯƠNG II: THANG ĐO BLOOM") is True
    assert is_heading_line("I. Bốn mức độ nhận thức") is True
    assert is_heading_line("1. Khái niệm và vị trí") is True
    assert is_heading_line("Đây là một đoạn văn bản bình thường không phải tiêu đề.") is False
    print("  -> Regex nhận diện tiêu đề cấu trúc hoạt động chính xác.")

    # Phân đoạn ngữ liệu
    chunks = semantic_thematic_chunking(SAMPLE_EDUCATIONAL_TEXT, target_words=200, min_words=100, max_words=400)
    assert len(chunks) >= 1, "Phải sinh ra ít nhất 1 chunk"
    for c in chunks:
        assert c["chunk_id"] >= 1
        assert len(c["text"]) > 50
        assert c["word_count"] > 0
        print(f"  -> Chunk {c['chunk_id']}: '{c['title']}' ({c['word_count']} từ)")
    print("  => PASSED: Module chunker.py hoạt động chính xác 100%!")


def test_llm_client_module():
    """Kiểm thử Module 3: LLM Client & Heuristic Grounded Generator"""
    print("\n[TEST 3] Kiểm tra Module backend/llm_client.py...")
    # Kiểm tra health check
    health = asyncio.run(check_llm_health())
    print("  -> Kết quả kiểm tra LLM Health:", health["message"])

    # Kiểm tra bộ sinh câu hỏi cho đủ 7 dạng câu hỏi
    all_7_types = ["mcq", "compound_tf", "short_answer", "msq", "matching", "cloze", "sequencing"]
    bloom_dist = {"Nhận biết": 40, "Thông hiểu": 30, "Vận dụng": 20, "Vận dụng cao": 10}

    chunk = {
        "chunk_id": 1,
        "title": "Nguyên lý khảo thí sư phạm",
        "text": SAMPLE_EDUCATIONAL_TEXT
    }

    questions = asyncio.run(generate_questions_for_chunk(
        chunk=chunk,
        requested_types=all_7_types,
        bloom_distribution=bloom_dist,
        num_questions=7
    ))

    assert len(questions) == 7, f"Kỳ vọng 7 câu hỏi, nhận được {len(questions)}"

    types_generated = set(q["type"] for q in questions)
    print("  -> Các dạng câu hỏi đã sinh ra:", types_generated)
    assert len(types_generated) == 7, "Phải sinh đủ cả 7 dạng câu hỏi"

    # Kiểm tra từng câu hỏi có đầy đủ Thẻ kiểm định Double-Check
    for q in questions:
        assert "stem" in q and len(q["stem"]) > 10, "Stem không hợp lệ"
        assert "double_check" in q, "Thiếu Thẻ kiểm định (double_check)"
        db = q["double_check"]
        assert "verbatim_citation" in db and len(db["verbatim_citation"]) > 5, "Thiếu dẫn chứng nguyên văn"
        assert "option_analysis" in db and len(db["option_analysis"]) > 5, "Thiếu phân tích phương án"
        assert "bloom_justification" in db, "Thiếu lý giải mức Bloom"
        assert db.get("is_fully_grounded") is True, "Xác nhận đối chiếu không đạt 100%"

        # Kiểm tra CẤM TUYỆT ĐỐI các cụm từ phụ thuộc văn bản (Quy tắc Stand-alone Stem)
        prohibited_phrases = [
            "căn cứ vào văn bản",
            "theo tài liệu",
            "dựa vào đoạn trích",
            "trong chủ đề",
            "tác giả cho rằng",
            "văn bản khẳng định"
        ]
        stem_lower = q["stem"].lower()
        for phrase in prohibited_phrases:
            assert phrase not in stem_lower, f"Vi phạm quy tắc Stand-alone Stem: Câu hỏi chứa cụm từ cấm '{phrase}'! Stem: {q['stem']}"

        # Kiểm tra nguyên tắc Haladyna và cấm từ rác trong options
        if q["type"] in ["mcq", "msq"] and isinstance(q.get("options"), list):
            for opt in q["options"]:
                assert "Tất cả các ý trên" not in opt, "Vi phạm Haladyna: chứa 'Tất cả các ý trên'"
                assert "Không có đáp án nào đúng" not in opt, "Vi phạm Haladyna: chứa 'Không có đáp án nào đúng'"
                opt_l = opt.lower()
                for junk in ["tài liệu", "văn bản", "ngoài tài liệu", "đoạn trích"]:
                    assert junk not in opt_l, f"Phương án chứa cụm từ rác: '{junk}' in '{opt}'"

    # Kiểm tra cấu trúc PSYCHOMETRIC_SYSTEM_PROMPT chuẩn 3 yêu cầu cốt lõi
    from backend.llm_client import PSYCHOMETRIC_SYSTEM_PROMPT
    prompt_lower = PSYCHOMETRIC_SYSTEM_PROMPT.lower()
    assert "biên soạn đề thi in ra giấy cho học sinh ngồi phòng thi độc lập" in prompt_lower
    assert "ngoài tài liệu" in prompt_lower
    assert "thay đổi mốc thời gian" in prompt_lower
    assert "cường quốc tầm trung" in prompt_lower
    print("  -> System Prompt đã tái cấu trúc chuẩn vai trò phòng thi độc lập và hướng dẫn tạo nhiễu.")

    print("  => PASSED: Module llm_client.py đáp ứng toàn diện 4 trụ cột khảo thí & Stand-alone Stem 100%!")
    return questions


def test_docx_exporter_module(sample_questions):
    """Kiểm thử Module 4: DOCX Exporter (Xuất đề thi Word 2 phần)"""
    print("\n[TEST 4] Kiểm tra Module backend/docx_exporter.py...")
    meta = {
        "school_name": "TRƯỜNG THPT CHUYÊN KHẢO THÍ",
        "exam_title": "KỲ THI ĐÁNH GIÁ CHẤT LƯỢNG HỌC KỲ",
        "subject": "NGÂN HÀNG CÂU HỎI SƯ PHẠM",
        "duration": "45 phút",
        "exam_code": "205",
        "academic_year": "NĂM HỌC 2025 - 2026"
    }

    docx_stream = build_exam_docx(sample_questions, meta)
    assert docx_stream is not None
    docx_bytes = docx_stream.getvalue()
    assert len(docx_bytes) > 5000, "Kích thước file DOCX quá nhỏ"

    # Đọc lại file docx để kiểm tra tính toàn vẹn 2 phần (cả paragraphs và tables)
    doc = docx.Document(io.BytesIO(docx_bytes))
    para_text = "\n".join([p.text for p in doc.paragraphs])
    table_text = "\n".join([cell.text for tbl in doc.tables for row in tbl.rows for cell in row.cells])
    full_text = para_text + "\n" + table_text

    # Kiểm tra Phần 1: Có tên trường, môn học, các câu hỏi
    assert "TRƯỜNG THPT CHUYÊN KHẢO THÍ" in full_text
    assert "NGÂN HÀNG CÂU HỎI SƯ PHẠM" in full_text
    assert "Câu 1:" in full_text
    assert "Câu 7:" in full_text
    assert "HẾT" in full_text

    # Kiểm tra Phần 2: Có tiêu đề đáp án và thẻ kiểm định
    assert "PHẦN 2: ĐÁP ÁN VÀ HƯỚNG DẪN CHẤM CHI TIẾT" in full_text
    assert "BẢNG TỔNG HỢP ĐÁP ÁN NHANH" in full_text
    assert "THẺ KIỂM ĐỊNH KHẢO THÍ" in full_text

    print(f"  -> Sinh file DOCX thành công ({len(docx_bytes)} bytes, {len(doc.paragraphs)} đoạn văn, {len(doc.tables)} bảng).")
    print("  => PASSED: Module docx_exporter.py tạo đề thi 2 phần hoàn hảo!")


def test_fastapi_endpoints():
    """Kiểm thử Module 5: FastAPI REST API & Endpoints"""
    print("\n[TEST 5] Kiểm tra Hệ thống REST API (backend/app.py)...")
    client = TestClient(app)

    # 1. Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "online"
    assert "question_types" in data_health
    print("  -> Endpoint GET /api/health: OK (200)")

    # 2. Presets
    res_presets = client.get("/api/presets")
    assert res_presets.status_code == 200
    assert len(res_presets.json()["presets"]) >= 3
    print("  -> Endpoint GET /api/presets: OK (200)")

    # 3. Upload raw text
    res_text = client.post("/api/upload-text", json={"text": SAMPLE_EDUCATIONAL_TEXT})
    assert res_text.status_code == 200
    doc_data = res_text.json()
    assert doc_data["word_count"] > 100
    print(f"  -> Endpoint POST /api/upload-text: OK ({doc_data['word_count']} từ)")

    # 4. Chunking endpoint
    res_chunk = client.post("/api/chunk", json={"text": SAMPLE_EDUCATIONAL_TEXT})
    assert res_chunk.status_code == 200
    chunk_data = res_chunk.json()
    chunks = chunk_data["chunks"]
    assert len(chunks) >= 1
    print(f"  -> Endpoint POST /api/chunk: OK ({len(chunks)} chunks)")

    # 5. Generate endpoint
    res_gen = client.post("/api/generate", json={
        "chunks": chunks,
        "total_questions": 4,
        "bloom_distribution": {"Nhận biết": 50, "Thông hiểu": 50, "Vận dụng": 0, "Vận dụng cao": 0},
        "selected_types": ["mcq", "compound_tf", "short_answer"]
    })
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["total_generated"] == 4
    print(f"  -> Endpoint POST /api/generate: OK ({gen_data['total_generated']} câu)")

    # 6. Export DOCX endpoint
    res_exp = client.post("/api/export-docx", json={
        "questions": gen_data["questions"],
        "exam_meta": {"subject": "Khao_Thi_Tu_Dong"}
    })
    assert res_exp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in res_exp.headers["content-type"]
    assert len(res_exp.content) > 3000
    print(f"  -> Endpoint POST /api/export-docx: OK ({len(res_exp.content)} bytes stream)")

    # 7. Frontend index serving
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "AI KHẢO THÍ" in res_index.text
    print("  -> Endpoint GET / (SPA Frontend): OK (200)")

    print("  => PASSED: Tất cả các Endpoint API hoạt động mượt mà và an toàn!")


if __name__ == "__main__":
    print("===============================================================================")
    print("      KIỂM TRA TÍNH TOÀN VẸN HỆ THỐNG AI KHẢO THÍ ANTIGRAVITY (100% OFFLINE)   ")
    print("===============================================================================")

    test_parser_module()
    test_chunker_module()
    sample_questions = test_llm_client_module()
    test_docx_exporter_module(sample_questions)
    test_fastapi_endpoints()

    print("\n===============================================================================")
    print("  🎉 TẤT CẢ CÁC MODULE VÀ TÍNH TOÀN VẸN CỦA DỰ ÁN ĐỀU ĐẠT CHUẨN 100%!  ")
    print("===============================================================================\n")
