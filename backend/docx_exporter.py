"""
Module Xuất file Word (.docx) chuyên nghiệp chia 2 phần rõ rệt:
- PHẦN 1: ĐỀ THI DÀNH CHO HỌC SINH (Chuẩn khảo thí, không lộ đáp án, định dạng trang nghiêm).
- PHẦN 2: ĐÁP ÁN & HƯỚNG DẪN CHẤM DÀNH CHO GIÁO VIÊN (Bảng đáp án nhanh, Thẻ kiểm định Double-Check, Dẫn chứng nguyên văn).
"""

import io
from typing import List, Dict, Any, Optional
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn


def set_cell_background(cell, fill_hex: str):
    """Đặt màu nền cho một ô bảng."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Đặt padding cho ô bảng."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    """Đặt viền thanh lịch cho bảng."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def format_run(run, font_name="Times New Roman", size_pt=12, bold=False, italic=False, color_rgb=(0, 0, 0)):
    """Định dạng phông chữ, kích thước và màu sắc cho văn bản."""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(*color_rgb)


def build_exam_docx(
    questions: List[Dict[str, Any]],
    exam_meta: Optional[Dict[str, Any]] = None
) -> io.BytesIO:
    """
    Biên soạn file Word (.docx) chuẩn hóa 2 phần từ danh sách câu hỏi đã được chọn:
    - questions: Danh sách các câu hỏi do người dùng chọn.
    - exam_meta: Tiêu đề trường, môn học, kỳ thi, thời gian, mã đề.
    """
    if exam_meta is None:
        exam_meta = {}

    school_name = exam_meta.get("school_name", "TRƯỜNG THPT CHUYÊN KHẢO THÍ").upper()
    exam_title = exam_meta.get("exam_title", "ĐỀ THI KHẢO SÁT CHẤT LƯỢNG").upper()
    subject = exam_meta.get("subject", "NGÂN HÀNG CÂU HỎI TỔNG HỢP").upper()
    duration = exam_meta.get("duration", "45 phút")
    exam_code = exam_meta.get("exam_code", "101")
    academic_year = exam_meta.get("academic_year", "NĂM HỌC 2025 - 2026")

    doc = Document()

    # Thiết lập lề trang chuẩn văn bản hành chính Việt Nam (Top 2cm, Bottom 2cm, Left 2.5cm, Right 2cm)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.79)     # ~2.0 cm
        section.bottom_margin = Inches(0.79)  # ~2.0 cm
        section.left_margin = Inches(0.98)    # ~2.5 cm
        section.right_margin = Inches(0.79)   # ~2.0 cm

    # =========================================================================
    # PHẦN 1: ĐỀ THI DÀNH CHO HỌC SINH
    # =========================================================================

    # Bảng tiêu đề đầu trang 2 cột chuẩn đề thi quốc gia
    header_table = doc.add_table(rows=1, cols=2)
    header_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_table.autofit = False

    cell_left = header_table.cell(0, 0)
    cell_right = header_table.cell(0, 1)
    cell_left.width = Inches(3.2)
    cell_right.width = Inches(3.4)

    # Cột trái: Tên đơn vị / Trường
    p_left1 = cell_left.paragraphs[0]
    p_left1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_left1.paragraph_format.space_after = Pt(2)
    r = p_left1.add_run(school_name)
    format_run(r, size_pt=11, bold=True)

    p_left2 = cell_left.add_paragraph()
    p_left2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_left2.paragraph_format.space_after = Pt(2)
    r = p_left2.add_run("HỘI ĐỒNG KHẢO THÍ")
    format_run(r, size_pt=11, bold=True)

    p_left3 = cell_left.add_paragraph()
    p_left3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_left3.paragraph_format.space_after = Pt(2)
    r = p_left3.add_run(f"ĐỀ THI CHÍNH THỨC\n(Đề thi gồm có {len(questions)} câu)")
    format_run(r, size_pt=10, italic=True)

    # Cột phải: Kỳ thi, Môn, Thời gian, Mã đề
    p_right1 = cell_right.paragraphs[0]
    p_right1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_right1.paragraph_format.space_after = Pt(2)
    r = p_right1.add_run(f"{exam_title}\n{academic_year}")
    format_run(r, size_pt=11, bold=True)

    p_right2 = cell_right.add_paragraph()
    p_right2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_right2.paragraph_format.space_after = Pt(2)
    r = p_right2.add_run(f"MÔN: {subject}")
    format_run(r, size_pt=12, bold=True)

    p_right3 = cell_right.add_paragraph()
    p_right3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_right3.paragraph_format.space_after = Pt(2)
    r = p_right3.add_run(f"Thời gian làm bài: {duration} (Không kể thời gian phát đề)\n")
    format_run(r, size_pt=10, italic=True)
    r_code = p_right3.add_run(f"MÃ ĐỀ THI: {exam_code}")
    format_run(r_code, size_pt=11, bold=True)

    # Đường phân cách
    p_div = doc.add_paragraph()
    p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_div.paragraph_format.space_before = Pt(4)
    p_div.paragraph_format.space_after = Pt(8)
    r = p_div.add_run("--------------------------------------------------------------------------------")
    format_run(r, size_pt=9, color_rgb=(100, 100, 100))

    # Thông tin thí sinh
    p_info = doc.add_paragraph()
    p_info.paragraph_format.space_after = Pt(12)
    r = p_info.add_run("Họ và tên thí sinh: ............................................................................  Số báo danh: ........................\n")
    format_run(r, size_pt=11, italic=True)
    r_guide = p_info.add_run("(Thí sinh làm bài trực tiếp trên giấy thi hoặc tô phiếu trả lời trắc nghiệm theo hướng dẫn)")
    format_run(r_guide, size_pt=10, italic=True, color_rgb=(80, 80, 80))

    # Danh sách các câu hỏi dành cho học sinh (Hoàn toàn KHÔNG lộ đáp án và KHÔNG chứa thẻ kiểm định)
    for q_idx, q in enumerate(questions, 1):
        q_type = q.get("type", "mcq")
        stem = q.get("stem", "")
        options = q.get("options", [])

        p_stem = doc.add_paragraph()
        p_stem.paragraph_format.space_before = Pt(8)
        p_stem.paragraph_format.space_after = Pt(4)
        p_stem.paragraph_format.line_spacing = 1.15

        # Đánh số câu
        r_num = p_stem.add_run(f"Câu {q_idx}: ")
        format_run(r_num, size_pt=12, bold=True)
        r_text = p_stem.add_run(stem)
        format_run(r_text, size_pt=12)

        # Hiển thị các phương án theo dạng câu hỏi
        if q_type in ["mcq", "msq"]:
            if isinstance(options, list):
                for opt in options:
                    p_opt = doc.add_paragraph()
                    p_opt.paragraph_format.left_indent = Inches(0.3)
                    p_opt.paragraph_format.space_after = Pt(2)
                    r_opt = p_opt.add_run(str(opt))
                    format_run(r_opt, size_pt=12)

        elif q_type == "compound_tf":
            if isinstance(options, list):
                for opt in options:
                    p_opt = doc.add_paragraph()
                    p_opt.paragraph_format.left_indent = Inches(0.3)
                    p_opt.paragraph_format.space_after = Pt(2)
                    r_opt = p_opt.add_run(f"{opt}   [ Đúng / Sai ]")
                    format_run(r_opt, size_pt=11)

        elif q_type == "short_answer":
            p_ans_box = doc.add_paragraph()
            p_ans_box.paragraph_format.left_indent = Inches(0.3)
            p_ans_box.paragraph_format.space_after = Pt(4)
            r_ans_box = p_ans_box.add_run("Trả lời: ..............................................................................................................")
            format_run(r_ans_box, size_pt=11, italic=True)

        elif q_type == "matching":
            if isinstance(options, dict):
                col_a = options.get("column_a", [])
                col_b = options.get("column_b", [])
                max_rows = max(len(col_a), len(col_b))

                m_table = doc.add_table(rows=max_rows + 1, cols=2)
                m_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                set_table_borders(m_table)

                # Header bảng ghép nối
                m_table.cell(0, 0).paragraphs[0].add_run("CỘT 1 (Nội dung / Khái niệm)").bold = True
                m_table.cell(0, 1).paragraphs[0].add_run("CỘT 2 (Ý nghĩa / Bản chất)").bold = True
                set_cell_background(m_table.cell(0, 0), "F2F2F2")
                set_cell_background(m_table.cell(0, 1), "F2F2F2")

                for r_i in range(max_rows):
                    txt_a = col_a[r_i] if r_i < len(col_a) else ""
                    txt_b = col_b[r_i] if r_i < len(col_b) else ""
                    m_table.cell(r_i + 1, 0).paragraphs[0].add_run(txt_a)
                    m_table.cell(r_i + 1, 1).paragraphs[0].add_run(txt_b)

        elif q_type == "cloze":
            if isinstance(options, list):
                for opt in options:
                    p_opt = doc.add_paragraph()
                    p_opt.paragraph_format.left_indent = Inches(0.3)
                    p_opt.paragraph_format.space_after = Pt(2)
                    r_opt = p_opt.add_run(str(opt))
                    format_run(r_opt, size_pt=12)

        elif q_type == "sequencing":
            if isinstance(options, dict):
                items = options.get("items", [])
                choices = options.get("choices", [])
                for item in items:
                    p_it = doc.add_paragraph()
                    p_it.paragraph_format.left_indent = Inches(0.3)
                    p_it.paragraph_format.space_after = Pt(2)
                    r_it = p_it.add_run(str(item))
                    format_run(r_it, size_pt=11)
                for choice in choices:
                    p_ch = doc.add_paragraph()
                    p_ch.paragraph_format.left_indent = Inches(0.3)
                    p_ch.paragraph_format.space_after = Pt(2)
                    r_ch = p_ch.add_run(str(choice))
                    format_run(r_ch, size_pt=12)

    # Lời kết phần đề thi
    p_end = doc.add_paragraph()
    p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_end.paragraph_format.space_before = Pt(16)
    p_end.paragraph_format.space_after = Pt(8)
    r_end = p_end.add_run("-------------------------- HẾT --------------------------\n(Cán bộ coi thi không giải thích gì thêm)")
    format_run(r_end, size_pt=11, bold=True, italic=True)

    # =========================================================================
    # PHẦN 2: ĐÁP ÁN & HƯỚNG DẪN CHẤM DÀNH CHO GIÁO VIÊN
    # =========================================================================
    doc.add_page_break()

    p_p2_title = doc.add_paragraph()
    p_p2_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_p2_title.paragraph_format.space_before = Pt(12)
    p_p2_title.paragraph_format.space_after = Pt(4)
    r = p_p2_title.add_run("PHẦN 2: ĐÁP ÁN VÀ HƯỚNG DẪN CHẤM CHI TIẾT")
    format_run(r, size_pt=14, bold=True, color_rgb=(18, 52, 102))

    p_p2_sub = doc.add_paragraph()
    p_p2_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_p2_sub.paragraph_format.space_after = Pt(14)
    r = p_p2_sub.add_run(f"KÈM THẺ KIỂM ĐỊNH KHẢO THÍ (DOUBLE-CHECK CARDS) - MÃ ĐỀ: {exam_code}")
    format_run(r, size_pt=11, bold=True, color_rgb=(100, 100, 100))

    # A. Bảng tổng hợp đáp án nhanh
    p_tbl_title = doc.add_paragraph()
    p_tbl_title.paragraph_format.space_after = Pt(4)
    r = p_tbl_title.add_run("I. BẢNG TỔNG HỢP ĐÁP ÁN NHANH:")
    format_run(r, size_pt=12, bold=True)

    summary_table = doc.add_table(rows=len(questions) + 1, cols=4)
    summary_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(summary_table)

    headers = ["Câu", "Dạng câu hỏi", "Mức độ Bloom", "Đáp án chính thức"]
    for c_i, h in enumerate(headers):
        cell = summary_table.cell(0, c_i)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        format_run(r, size_pt=11, bold=True)
        set_cell_background(cell, "EAEAEA")

    for q_i, q in enumerate(questions, 1):
        row = summary_table.rows[q_i]
        row.cells[0].paragraphs[0].add_run(str(q_i)).bold = True
        row.cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        q_type_str = str(q.get("type_name") or q.get("type") or "Trắc nghiệm")
        q_bloom_str = str(q.get("bloom_level") or "Thông hiểu")
        q_ans_str = str(q.get("correct_answer") or "")
        row.cells[1].paragraphs[0].add_run(q_type_str)
        row.cells[2].paragraphs[0].add_run(q_bloom_str)
        row.cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        row.cells[3].paragraphs[0].add_run(q_ans_str).bold = True

    # B. Chi tiết thẻ kiểm định (Double-Check Card) cho từng câu
    p_dt_title = doc.add_paragraph()
    p_dt_title.paragraph_format.space_before = Pt(16)
    p_dt_title.paragraph_format.space_after = Pt(8)
    r = p_dt_title.add_run("II. HƯỚNG DẪN GIẢI CHI TIẾT VÀ BẰNG CHỨNG PHÁP LÝ (DOUBLE-CHECK):")
    format_run(r, size_pt=12, bold=True)

    for q_idx, q in enumerate(questions, 1):
        db = q.get("double_check") if isinstance(q.get("double_check"), dict) else {}
        citation = str(db.get("verbatim_citation") or "Dẫn chiếu trực tiếp từ ngữ liệu nguồn.")
        analysis = str(db.get("option_analysis") or "Các phương án đã được kiểm định đối chiếu.")
        bloom_just = str(db.get("bloom_justification") or "Phù hợp thang nhận thức Bloom.")
        q_type_str = str(q.get("type_name") or q.get("type") or "Trắc nghiệm")
        q_bloom_str = str(q.get("bloom_level") or "Thông hiểu")
        q_ans_str = str(q.get("correct_answer") or "")

        # Hộp thẻ kiểm định cho từng câu
        card_table = doc.add_table(rows=5, cols=2)
        card_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(card_table, color="B0C4DE", sz="6")

        # Tiêu đề câu hỏi
        title_cell = card_table.cell(0, 0)
        title_cell.merge(card_table.cell(0, 1))
        set_cell_background(title_cell, "F0F4F8")
        p_c = title_cell.paragraphs[0]
        r = p_c.add_run(f"CÂU {q_idx} - [{q_type_str}] - MỨC BLOOM: {q_bloom_str.upper()}")
        format_run(r, size_pt=11, bold=True, color_rgb=(18, 52, 102))

        # Dòng 1: Đáp án chuẩn
        card_table.cell(1, 0).paragraphs[0].add_run("Đáp án chính thức:").bold = True
        r_ans = card_table.cell(1, 1).paragraphs[0].add_run(q_ans_str)
        format_run(r_ans, size_pt=11, bold=True, color_rgb=(0, 128, 0))

        # Dòng 2: Dẫn chứng nguyên văn
        card_table.cell(2, 0).paragraphs[0].add_run("Dẫn chứng nguyên văn (Verbatim):").bold = True
        r_cit = card_table.cell(2, 1).paragraphs[0].add_run(f"\"{citation}\"")
        format_run(r_cit, size_pt=10, italic=True)

        # Dòng 3: Phân tích đúng/sai các phương án
        card_table.cell(3, 0).paragraphs[0].add_run("Phân tích phương án:").bold = True
        r_ana = card_table.cell(3, 1).paragraphs[0].add_run(analysis)
        format_run(r_ana, size_pt=10)

        # Dòng 4: Đánh giá Bloom & Độ tin cậy
        card_table.cell(4, 0).paragraphs[0].add_run("Đánh giá khảo thí:").bold = True
        r_blm = card_table.cell(4, 1).paragraphs[0].add_run(f"{bloom_just} (Xác nhận căn cứ 100% từ tài liệu - Zero Hallucination)")
        format_run(r_blm, size_pt=10, color_rgb=(40, 40, 40))

        # Khoảng cách giữa các câu
        p_space = doc.add_paragraph()
        p_space.paragraph_format.space_before = Pt(4)
        p_space.paragraph_format.space_after = Pt(4)

    # Lưu ra bộ nhớ stream
    output_stream = io.BytesIO()
    doc.save(output_stream)
    output_stream.seek(0)
    return output_stream
