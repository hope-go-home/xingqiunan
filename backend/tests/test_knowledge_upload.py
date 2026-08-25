# 知识库文件上传文本提取测试

import pytest
from app.services.knowledge_service import extract_text


class TestExtractText:
    def test_txt(self):
        text = extract_text("a.txt", "你好世界".encode("utf-8"))
        assert "你好世界" in text

    def test_md(self):
        text = extract_text("a.md", "# 标题\n内容".encode("utf-8"))
        assert "标题" in text

    def test_csv(self):
        text = extract_text("a.csv", "a,b,c\n1,2,3".encode("utf-8"))
        assert "1,2,3" in text

    def test_json(self):
        text = extract_text("a.json", '{"k": "v"}'.encode("utf-8"))
        assert "v" in text

    def test_html(self):
        text = extract_text("a.html", "<p>段落</p>".encode("utf-8"))
        assert "段落" in text

    def test_unsupported_ext(self):
        with pytest.raises(ValueError):
            extract_text("a.xyz", b"data")

    def test_doc_old_format(self):
        with pytest.raises(ValueError):
            extract_text("a.doc", b"data")
