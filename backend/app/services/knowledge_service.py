# 知识库业务逻辑：使用 Chroma 存储文档向量，支持语义检索
# 文本分块：长文档自动切分，每块约 500 字，块间重叠 50 字

import io
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import CHROMA_PERSIST_DIR

CHUNK_SIZE = 500        # 每块字符数
CHUNK_OVERLAP = 50      # 块间重叠字符数

# 可直接按文本读取的格式
TEXT_EXTS = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".toml", ".cfg",
             ".ini", ".csv", ".log", ".env", ".xml", ".html"}


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """将长文本按固定大小分块，块间有重叠"""
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def extract_text(filename: str, content: bytes) -> str:
    """从上传文件的字节内容中提取纯文本（支持 txt/md/pdf/docx/json/csv 等）"""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    # 文本类格式：直接解码
    if ext in TEXT_EXTS:
        return content.decode("utf-8", errors="ignore")

    # PDF：PyMuPDF 从内存解析
    if ext == ".pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(stream=content, filetype="pdf")
        try:
            text_parts = [page.get_text() for page in doc]
        finally:
            doc.close()
        result = "\n".join(text_parts)
        if not result.strip():
            raise ValueError("PDF 中未提取到文字（可能是扫描件或图片型 PDF）")
        return result

    # Word：python-docx 从内存解析
    if ext in (".docx", ".doc"):
        if ext == ".doc":
            raise ValueError("旧版 .doc 格式不支持，请转换为 .docx")
        from docx import Document
        doc = Document(io.BytesIO(content))
        text_parts = [p.text for p in doc.paragraphs if p.text.strip()]
        if not text_parts:
            raise ValueError("Word 文档为空")
        return "\n".join(text_parts)

    raise ValueError(f"不支持的文件类型: {ext or '未知'}（支持 txt/md/pdf/docx/json/csv/html 等）")


class KnowledgeService:
    """知识库服务，基于 Chroma 实现文档向量化存储和检索。"""

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self._collection = None

    @property
    def collection(self):
        """延迟加载 Chroma 集合"""
        if self._collection is None:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self._collection = client.get_or_create_collection(
                name=f"user_{self.user_id}",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add_document(self, text: str, metadata: dict | None = None) -> list[str]:
        """将文本分块后添加到知识库，返回块 ID 列表"""
        chunks = _chunk_text(text)
        base_meta = metadata or {"user_id": self.user_id}
        doc_ids = []
        metadatas = []
        documents = []

        for i, chunk in enumerate(chunks):
            cid = uuid.uuid4().hex[:16]
            doc_ids.append(cid)
            metadatas.append({**base_meta, "chunk": i, "total_chunks": len(chunks)})
            documents.append(chunk)

        self.collection.add(documents=documents, metadatas=metadatas, ids=doc_ids)
        return doc_ids

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """语义搜索知识库，返回最相关的文档片段"""
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                docs.append({
                    "content": doc,
                    "score": results["distances"][0][i] if results.get("distances") else 0,
                })
        return docs

    async def list_documents(self) -> list[dict]:
        """列出知识库中的文档（限制前 50 条，避免全量加载内存）"""
        results = self.collection.get(limit=50)
        docs = []
        for i, doc_id in enumerate(results["ids"]):
            content = results["documents"][i] if results["documents"] else ""
            docs.append({
                "id": doc_id,
                "content": content[:100] + "..." if len(content) > 100 else content,
            })
        return docs

    async def delete_document(self, doc_id: str):
        """根据文档 ID 删除"""
        self.collection.delete(ids=[doc_id])
