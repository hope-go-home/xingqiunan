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

    # 集合缓存：user_id -> collection（避免每次请求都 get_or_create）
    _collections: dict[int, object] = {}

    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id

    @classmethod
    def _get_collection(cls, user_id: int):
        if user_id not in cls._collections:
            import chromadb
            client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            cls._collections[user_id] = client.get_or_create_collection(
                name=f"user_{user_id}",
                metadata={"hnsw:space": "cosine"},
            )
        return cls._collections[user_id]

    @property
    def collection(self):
        return self._get_collection(self.user_id)

    async def add_document(self, text: str, metadata: dict | None = None) -> list[str]:
        """将文本分块后添加到知识库，所有块共享同一个 group 标识（便于整篇删除）"""
        chunks = _chunk_text(text)
        group = uuid.uuid4().hex[:12]
        base_meta = {"user_id": self.user_id, "group": group}
        if metadata:
            base_meta.update(metadata)
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
        """按文档分组列出知识库（一个文档 = 多个分块，聚合为一条）"""
        results = self.collection.get()
        groups: dict[str, dict] = {}
        ids = results.get("ids") or []
        metadatas = results.get("metadatas") or []
        documents = results.get("documents") or []
        for i, cid in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            content = documents[i] if i < len(documents) and documents[i] else ""
            gid = meta.get("group") or cid  # 旧数据无 group 标识 → 每块独立成组
            if gid not in groups:
                title = meta.get("filename") or content[:60] or "（无标题）"
                groups[gid] = {"id": gid, "title": title, "chunks": 0, "preview": content[:100]}
            groups[gid]["chunks"] += 1
        return list(groups.values())

    async def delete_document(self, doc_id: str):
        """按文档删除：优先按 group 删除全部分块；旧数据无 group 时按块 ID 兜底"""
        before = self.collection.count()
        self.collection.delete(where={"group": doc_id})
        if self.collection.count() == before:
            self.collection.delete(ids=[doc_id])
