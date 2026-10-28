"""
Module Phân đoạn Ngữ nghĩa theo Chủ đề Kiến thức (Semantic Thematic Chunking Engine).
Tự động bóc tách cấu trúc tài liệu (.docx, .pdf, .txt), nhận diện tiêu đề chương mục,
gom nội dung thành các phân đoạn 1.500 - 2.500 từ đảm bảo tính trọn vẹn ngữ liệu.
"""

import re
from typing import List, Dict, Any


# Biểu thức chính quy nhận diện tiêu đề cấu trúc trong tài liệu tiếng Việt / chuẩn khoa học
HEADING_PATTERNS = [
    # Tiêu đề Markdown: # Tiêu đề, ## Tiêu đề
    r"^(#{1,6})\s+(.+)$",
    # Tiêu đề Chương, Bài, Phần, Mục, Tiết
    r"^(CHƯƠNG|Chương|BÀI|Bài|PHẦN|Phần|MỤC|Mục|TIẾT|Tiết)\s+([0-9IVXLCDMivxlcdm]+)?[:.\-\s]*(.*)$",
    # Số La Mã đứng đầu dòng: I. Tổng quan, II. Phương pháp
    r"^([IVXLCDMivxlcdm]{1,6})[\.\:\)]\s+(.+)$",
    # Số thứ tự mục: 1. Giới thiệu, 1.1 Khái niệm, 1.2.3 Bản chất
    r"^([0-9]+(?:\.[0-9]+)*)[\.\:\)]\s+(.+)$",
    # Ký tự chữ cái đứng đầu: A. Đại cương, B. Chi tiết
    r"^([A-Z])[\.\:\)]\s+([A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ].+)$",
]

COMPILED_HEADING_REGEX = [re.compile(p, re.IGNORECASE) for p in HEADING_PATTERNS]


def is_heading_line(line: str) -> bool:
    """
    Kiểm tra xem một dòng có phải là tiêu đề chương mục hay không.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 200:
        return False

    # Kiểm tra qua các Regex tiêu chuẩn
    for regex in COMPILED_HEADING_REGEX:
        if regex.match(stripped):
            return True

    # Kiểm tra dòng chữ in hoa hoàn toàn (chiều dài từ 2 đến 15 từ, không kết thúc bằng dấu chấm)
    words = stripped.split()
    if 2 <= len(words) <= 15:
        # Nếu trên 80% chữ cái là IN HOA và không có dấu câu kết thúc thông thường (chấm, hỏi, phẩy)
        letters = [c for c in stripped if c.isalpha()]
        if letters:
            upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
            if upper_ratio > 0.85 and not stripped.endswith((".", ",", ";", ":", "?", "!")):
                return True

    return False


def clean_title(title: str) -> str:
    """
    Làm sạch tiêu đề, bỏ các ký tự Markdown (#) hoặc khoảng trắng thừa.
    """
    cleaned = re.sub(r"^#+\s*", "", title).strip()
    return cleaned if cleaned else "Chủ đề kiến thức"


def split_into_paragraphs(text: str) -> List[str]:
    """
    Tách văn bản thành các đoạn văn (paragraphs) tự nhiên.
    """
    raw_paras = re.split(r"\n\s*\n", text)
    cleaned_paras = []
    for p in raw_paras:
        p_clean = p.strip()
        if p_clean:
            cleaned_paras.append(p_clean)
    return cleaned_paras


def semantic_thematic_chunking(
    text: str,
    target_words: int = 1800,
    min_words: int = 1200,
    max_words: int = 2500
) -> List[Dict[str, Any]]:
    """
    Thuật toán phân đoạn ngữ nghĩa theo chủ đề kiến thức:
    - Bóc tách theo tiêu đề chương mục.
    - Gom nhóm các đoạn văn thuộc cùng chủ đề kiến thức.
    - Duy trì kích thước mục tiêu từ 1.500 - 2.500 từ.
    - Đảm bảo tính trọn vẹn ngữ liệu, không bao giờ ngắt ngang câu văn.
    """
    if not text or not text.strip():
        return []

    paragraphs = split_into_paragraphs(text)
    total_words = len(text.split())

    # Nếu toàn bộ tài liệu ngắn hơn ngưỡng mục tiêu, giữ trọn 1 chunk
    if total_words <= max_words:
        first_line = paragraphs[0].splitlines()[0] if paragraphs else "Toàn bộ tài liệu"
        title = clean_title(first_line) if is_heading_line(first_line) else "Chủ đề tổng hợp"
        return [{
            "chunk_id": 1,
            "title": title[:100],
            "text": text.strip(),
            "word_count": total_words,
            "char_count": len(text.strip()),
            "heading": title[:100]
        }]

    # Xây dựng các khối sơ cấp (sections) dựa trên tiêu đề
    sections = []
    current_title = "Chủ đề mở đầu"
    current_paras: List[str] = []

    for para in paragraphs:
        first_line = para.splitlines()[0].strip()
        if is_heading_line(first_line):
            # Nếu đã có nội dung tích lũy, đẩy section trước đó vào
            if current_paras:
                sec_text = "\n\n".join(current_paras)
                sections.append({
                    "title": current_title,
                    "text": sec_text,
                    "words": len(sec_text.split())
                })
                current_paras = []
            current_title = clean_title(first_line)
            current_paras.append(para)
        else:
            current_paras.append(para)

    if current_paras:
        sec_text = "\n\n".join(current_paras)
        sections.append({
            "title": current_title,
            "text": sec_text,
            "words": len(sec_text.split())
        })

    # Gom các sections thành các chunks đạt khoảng target_words (1500 - 2500 từ)
    chunks = []
    accum_paras = []
    accum_words = 0
    chunk_title = ""

    for sec in sections:
        sec_words = sec["words"]

        # Nếu một section đơn lẻ đã quá dài (> max_words), tách nhỏ theo các paragraph trọn vẹn
        if sec_words > max_words:
            # Trước hết đẩy những gì đang tích lũy ra chunk mới
            if accum_paras:
                c_text = "\n\n".join(accum_paras)
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": chunk_title or "Chủ đề kiến thức",
                    "text": c_text,
                    "word_count": len(c_text.split()),
                    "char_count": len(c_text)
                })
                accum_paras = []
                accum_words = 0
                chunk_title = ""

            # Chia nhỏ section dài theo paragraphs
            sub_paras = sec["text"].split("\n\n")
            sub_accum = []
            sub_words = 0
            sub_idx = 1

            for sp in sub_paras:
                sp_w = len(sp.split())
                if sub_words + sp_w > max_words and sub_accum:
                    sc_text = "\n\n".join(sub_accum)
                    chunks.append({
                        "chunk_id": len(chunks) + 1,
                        "title": f"{sec['title']} (Phần {sub_idx})",
                        "text": sc_text,
                        "word_count": len(sc_text.split()),
                        "char_count": len(sc_text)
                    })
                    sub_idx += 1
                    sub_accum = [sp]
                    sub_words = sp_w
                else:
                    sub_accum.append(sp)
                    sub_words += sp_w

            if sub_accum:
                sc_text = "\n\n".join(sub_accum)
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": f"{sec['title']} (Phần {sub_idx})" if sub_idx > 1 else sec["title"],
                    "text": sc_text,
                    "word_count": len(sc_text.split()),
                    "char_count": len(sc_text)
                })

        # Trường hợp section có thể gộp
        elif accum_words + sec_words <= max_words:
            if not accum_paras:
                chunk_title = sec["title"]
            accum_paras.append(sec["text"])
            accum_words += sec_words

            # Nếu đã đạt ngưỡng tối thiểu hợp lý, đóng chunk
            if accum_words >= target_words:
                c_text = "\n\n".join(accum_paras)
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": chunk_title or sec["title"],
                    "text": c_text,
                    "word_count": len(c_text.split()),
                    "char_count": len(c_text)
                })
                accum_paras = []
                accum_words = 0
                chunk_title = ""

        else:
            # Vượt quá max_words, xuất chunk hiện tại và bắt đầu chunk mới
            if accum_paras:
                c_text = "\n\n".join(accum_paras)
                chunks.append({
                    "chunk_id": len(chunks) + 1,
                    "title": chunk_title or "Chủ đề kiến thức",
                    "text": c_text,
                    "word_count": len(c_text.split()),
                    "char_count": len(c_text)
                })
            accum_paras = [sec["text"]]
            accum_words = sec_words
            chunk_title = sec["title"]

    # Đẩy chunk còn lại
    if accum_paras:
        c_text = "\n\n".join(accum_paras)
        # Nếu chunk cuối quá ngắn và đã có chunk trước đó, gộp vào chunk trước nếu không vượt quá max_words * 1.2
        if chunks and len(c_text.split()) < min_words / 2:
            prev = chunks[-1]
            combined_text = prev["text"] + "\n\n" + c_text
            prev["text"] = combined_text
            prev["word_count"] = len(combined_text.split())
            prev["char_count"] = len(combined_text)
        else:
            chunks.append({
                "chunk_id": len(chunks) + 1,
                "title": chunk_title or "Chủ đề kiến thức",
                "text": c_text,
                "word_count": len(c_text.split()),
                "char_count": len(c_text)
            })

    # Cập nhật lại chunk_id liên tục
    for idx, c in enumerate(chunks, 1):
        c["chunk_id"] = idx

    return chunks
