import io
import os

def parse_txt_file(path_or_file) -> str:
    """支持传入文件路径或 file-like 对象，返回文本内容（仅文本文件）。"""
    if hasattr(path_or_file, 'read'):
        # file-like
        content = path_or_file.read()
        if isinstance(content, bytes):
            try:
                return content.decode('utf-8', errors='ignore')
            except Exception:
                return content.decode('gbk', errors='ignore')
        return content

    with open(path_or_file, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def parse_pdf_file(path) -> str:
    """从 PDF 文件提取文本。若未安装 `pdfminer.six`，会抛出 ImportError。"""
    try:
        from pdfminer.high_level import extract_text
    except Exception as e:
        raise ImportError('缺少 pdfminer.six：pip install pdfminer.six') from e

    return extract_text(path)


def parse_docx_file(path) -> str:
    """从 DOCX 文件提取文本。若未安装 `python-docx`，会抛出 ImportError。"""
    try:
        import docx
    except Exception as e:
        raise ImportError('缺少 python-docx：pip install python-docx') from e

    doc = docx.Document(path)
    parts = [p.text for p in doc.paragraphs]
    return '\n'.join(parts)


def parse_file(path_or_file) -> str:
    """自动根据文件后缀选择解析器，支持 txt/pdf/docx 或 file-like 对象。

    保留原 `parse_txt_file` 的行为以兼容现有调用。
    """
    # file-like with name attr
    if hasattr(path_or_file, 'read') and hasattr(path_or_file, 'name'):
        name = path_or_file.name
    elif isinstance(path_or_file, str):
        name = path_or_file
    else:
        # fallback to txt read
        return parse_txt_file(path_or_file)

    ext = os.path.splitext(name)[1].lower()
    if ext == '.pdf':
        return parse_pdf_file(path_or_file if isinstance(path_or_file, str) else name)
    if ext in ('.docx', '.doc'):
        return parse_docx_file(path_or_file if isinstance(path_or_file, str) else name)
    return parse_txt_file(path_or_file)