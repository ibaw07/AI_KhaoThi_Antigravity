"""
Alias chuyển tiếp sang parser.py để tương thích hoàn toàn cả hai tên gọi
(document_parser.py và parser.py) theo đặc tả kiến trúc.
"""

from .parser import (
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_text_from_file,
    strip_meta_prefixes,
    validate_question_content,
    post_process_filter_question,
    filter_and_clean_questions
)

__all__ = [
    "extract_text_from_docx",
    "extract_text_from_pdf",
    "extract_text_from_txt",
    "extract_text_from_file",
    "strip_meta_prefixes",
    "validate_question_content",
    "post_process_filter_question",
    "filter_and_clean_questions"
]
