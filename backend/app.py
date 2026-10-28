"""
Ứng dụng FastAPI chính - Hệ thống AI Khảo Thí Đa Dạng (100% Offline).
Vận hành trên 127.0.0.1:8000, không cần quyền Administrator, không can thiệp UAC/Firewall.
"""

import os
import sys
import tempfile
import urllib.parse
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Bổ sung thư mục hiện tại vào sys.path để import nội bộ mượt mà
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.parser import extract_text_from_file, filter_and_clean_questions
from backend.chunker import semantic_thematic_chunking
from backend.llm_client import (
    check_llm_health,
    generate_questions_for_chunk,
    QUESTION_TYPES,
    BLOOM_LEVELS,
    DEFAULT_LLM_ENDPOINT
)
from backend.docx_exporter import build_exam_docx

app = FastAPI(
    title="AI Khảo Thí Antigravity (100% Offline)",
    description="Hệ thống AI Agent tạo câu hỏi khảo thí sư phạm đa dạng, chuẩn 4 trụ cột khảo thí",
    version="1.0.0"
)

# Cho phép CORS cục bộ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# Pydantic Schemas
# =========================================================================

class TextPayload(BaseModel):
    text: str = Field(..., description="Nội dung văn bản trực tiếp")
    filename: Optional[str] = "van_ban_nhap_tay.txt"


class ChunkRequest(BaseModel):
    text: str
    target_words: int = 1800
    min_words: int = 1200
    max_words: int = 2500


class GenerateRequest(BaseModel):
    chunks: List[Dict[str, Any]]
    total_questions: int = 10
    bloom_distribution: Dict[str, int] = {
        "Nhận biết": 40,
        "Thông hiểu": 30,
        "Vận dụng": 20,
        "Vận dụng cao": 10
    }
    selected_types: List[str] = ["mcq", "compound_tf", "short_answer", "msq", "matching", "cloze", "sequencing"]
    llm_endpoint: str = DEFAULT_LLM_ENDPOINT


class ExportRequest(BaseModel):
    questions: List[Dict[str, Any]]
    exam_meta: Optional[Dict[str, Any]] = None


# =========================================================================
# API Endpoints
# =========================================================================

@app.get("/api/health")
async def health_check():
    """Kiểm tra tình trạng hệ thống và kết nối Local LLM 127.0.0.1:5001."""
    llm_status = await check_llm_health()
    return {
        "status": "online",
        "system": {
            "mode": "100% Offline Local Loopback",
            "host": "127.0.0.1:8000",
            "target_cpu": "Intel Core i5-14500 (14 nhân, 20 luồng)",
            "memory_profile": "16GB RAM Optimized"
        },
        "llm": llm_status,
        "question_types": QUESTION_TYPES,
        "bloom_levels": BLOOM_LEVELS
    }


@app.get("/api/presets")
async def get_matrix_presets():
    """Lấy danh sách ma trận đề thi mẫu chuẩn khảo thí sư phạm."""
    return {
        "presets": [
            {
                "id": "bo_gddt_2025",
                "name": "Chuẩn Ma trận Bộ GD&ĐT 2025 (40 - 30 - 20 - 10)",
                "description": "Cân bằng tối ưu cho kỳ thi tốt nghiệp và kiểm tra định kỳ",
                "bloom": {"Nhận biết": 40, "Thông hiểu": 30, "Vận dụng": 20, "Vận dụng cao": 10},
                "recommended_types": ["mcq", "compound_tf", "short_answer"]
            },
            {
                "id": "on_tap_co_ban",
                "name": "Ôn tập củng cố kiến thức (50 - 35 - 15 - 0)",
                "description": "Tập trung nhận biết và thông hiểu cho học sinh nắm vững cốt lõi",
                "bloom": {"Nhận biết": 50, "Thông hiểu": 35, "Vận dụng": 15, "Vận dụng cao": 0},
                "recommended_types": ["mcq", "short_answer", "cloze"]
            },
            {
                "id": "danh_gia_nang_luc",
                "name": "Đánh giá năng lực & Phân hóa cao (20 - 30 - 30 - 20)",
                "description": "Tăng cường tỷ lệ vận dụng và phân tích giải quyết vấn đề",
                "bloom": {"Nhận biết": 20, "Thông hiểu": 30, "Vận dụng": 30, "Vận dụng cao": 20},
                "recommended_types": ["mcq", "compound_tf", "msq", "matching", "sequencing"]
            }
        ]
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Tải lên tệp tài liệu (.docx, .pdf, .txt) và trích xuất nội dung."""
    suffix = Path(file.filename or "temp.txt").suffix.lower()
    if suffix not in [".docx", ".pdf", ".txt", ".md"]:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng tệp '{suffix}' không được hỗ trợ. Vui lòng tải file .docx, .pdf hoặc .txt."
        )

    # Lưu tệp tạm thời không can thiệp hệ thống
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        parsed_data = extract_text_from_file(tmp_path)
        parsed_data["filename"] = file.filename

        # Phân đoạn sơ bộ để người dùng có cái nhìn tổng quan
        preview_chunks = semantic_thematic_chunking(parsed_data["text"])
        parsed_data["chunks_count"] = len(preview_chunks)
        parsed_data["preview_headings"] = [c.get("title") for c in preview_chunks]

        return parsed_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi trích xuất tài liệu: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.post("/api/upload-text")
async def upload_raw_text(payload: TextPayload):
    """Tiếp nhận văn bản dán trực tiếp vào giao diện."""
    cleaned = payload.text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Văn bản không được để trống.")

    words = len(cleaned.split())
    preview_chunks = semantic_thematic_chunking(cleaned)

    return {
        "filename": payload.filename,
        "extension": ".txt",
        "text": cleaned,
        "word_count": words,
        "char_count": len(cleaned),
        "chunks_count": len(preview_chunks),
        "preview_headings": [c.get("title") for c in preview_chunks]
    }


@app.post("/api/chunk")
async def chunk_document(req: ChunkRequest):
    """Thực hiện thuật toán phân đoạn ngữ nghĩa theo chủ đề kiến thức."""
    try:
        chunks = semantic_thematic_chunking(
            text=req.text,
            target_words=req.target_words,
            min_words=req.min_words,
            max_words=req.max_words
        )
        return {
            "total_chunks": len(chunks),
            "chunks": chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi phân đoạn ngữ nghĩa: {str(e)}")


@app.post("/api/generate")
async def generate_exam(req: GenerateRequest):
    """
    Sinh câu hỏi khảo thí kèm Thẻ kiểm định (Double-Check Cards)
    cho từng phân đoạn kiến thức theo ma trận đã cấu hình.
    """
    if not req.chunks:
        raise HTTPException(status_code=400, detail="Danh sách phân đoạn ngữ liệu không được để trống.")

    total_chunks = len(req.chunks)
    total_q = max(1, req.total_questions)

    # Phân bổ số câu hỏi đều cho các chunks
    base_per_chunk = total_q // total_chunks
    remainder = total_q % total_chunks

    all_generated_questions = []

    for idx, chunk in enumerate(req.chunks):
        q_count = base_per_chunk + (1 if idx < remainder else 0)
        if q_count <= 0:
            continue

        chunk_questions = await generate_questions_for_chunk(
            chunk=chunk,
            requested_types=req.selected_types,
            bloom_distribution=req.bloom_distribution,
            num_questions=q_count,
            endpoint=req.llm_endpoint
        )
        all_generated_questions.extend(chunk_questions)

    # Lọc hậu xử lý bổ sung đảm bảo 100% câu hỏi sạch tiền tố và không có phương án rác
    all_generated_questions = filter_and_clean_questions(all_generated_questions)

    # Đánh số lại thứ tự id liên tục
    for i, q in enumerate(all_generated_questions, 1):
        q["index"] = i

    return {
        "total_generated": len(all_generated_questions),
        "questions": all_generated_questions
    }


import unicodedata

def to_safe_ascii(text: str) -> str:
    """Chuyển đổi chuỗi tiếng Việt thành ký tự ASCII an toàn cho HTTP headers."""
    nfkd = unicodedata.normalize('NFKD', str(text))
    no_accents = "".join(c for c in nfkd if not unicodedata.combining(c)).replace('đ', 'd').replace('Đ', 'D')
    cleaned = "".join(c for c in no_accents if c.isalnum() or c in " _-").strip()
    return cleaned.replace(' ', '_') or "Khao_Thi"


@app.post("/api/export-docx")
async def export_exam_docx(req: ExportRequest):
    """
    Biên soạn và xuất file Word (.docx) chuẩn sư phạm gồm 2 phần riêng biệt:
    Phần 1: Đề thi dành cho học sinh (không đáp án).
    Phần 2: Đáp án & Hướng dẫn chấm kèm Thẻ kiểm định dành cho giáo viên.
    """
    if not req.questions:
        raise HTTPException(status_code=400, detail="Không có câu hỏi nào được chọn để xuất file Word.")

    try:
        docx_stream = build_exam_docx(
            questions=req.questions,
            exam_meta=req.exam_meta
        )

        subj_name = (req.exam_meta.get("subject") or "Tong_Hop") if req.exam_meta else "Tong_Hop"
        safe_ascii_subj = to_safe_ascii(subj_name)
        safe_ascii_filename = f"De_Thi_{safe_ascii_subj}.docx"

        # Encode filename RFC 5987 để hỗ trợ tiếng Việt trên mọi trình duyệt
        raw_unicode_filename = f"De_Thi_{subj_name.strip().replace(' ', '_')}.docx"
        encoded_filename = urllib.parse.quote(raw_unicode_filename)

        return StreamingResponse(
            docx_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=\"{safe_ascii_filename}\"; filename*=UTF-8''{encoded_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi khởi tạo file Word: {str(e)}")


# =========================================================================
# Static Files & Frontend SPA Serving
# =========================================================================

FRONTEND_DIR = BASE_DIR / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return JSONResponse({"message": "Frontend chưa được khởi tạo hoàn chỉnh"})
