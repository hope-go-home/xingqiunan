# 配置模块：load_dotenv() 把 .env 加载到环境变量，然后用 os.getenv() 读取
from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv()

# === 数据库 ===
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/agent_workbench")

# === Redis ===
REDIS_URL = os.getenv("REDIS_URL", "redis://:123456@localhost:6380/0")

# === JWT ===
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# === LLM (通义千问 / DashScope) ===
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.7-plus")

# === 高德地图 ===
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")

# === 本地数据目录 ===
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_data"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
