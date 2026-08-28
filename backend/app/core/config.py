# 配置模块：load_dotenv() 把 .env 加载到环境变量，然后用 os.getenv() 读取
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv()

# === 运行环境 ===
ENV = os.getenv("ENV", "dev")  # dev / prod

# === 数据库 ===
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/agent_workbench")

# === Redis ===
REDIS_URL = os.getenv("REDIS_URL", "redis://:123456@localhost:6380/0")

# === JWT ===
# 生产环境必须显式设置 SECRET_KEY，否则拒绝启动
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
if ENV != "dev" and SECRET_KEY == "change-this-in-production":
    raise RuntimeError("生产环境必须设置 SECRET_KEY 环境变量（backend/.env）")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

# === CORS ===
# 逗号分隔的允许来源列表，默认开发环境（Vite）
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

# === LLM (通义千问 / DashScope) ===
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.7-plus")

# === 视觉模型 ===
VISION_MODEL = os.getenv("VISION_MODEL", "qwen-vl-plus")

# === 备用 LLM（故障转移）===
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "deepseek-v4-flash")
LLM_FALLBACK_API_KEY = os.getenv("LLM_FALLBACK_API_KEY", "")

# === 高德地图 ===
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")

# === 成本熔断：每日费用预算（元，按用户，超限拒绝新的 Agent 请求）===
COST_DAILY_BUDGET = float(os.getenv("COST_DAILY_BUDGET", "10"))

# === 博查（联网搜索）===
BOCHA_API_KEY = os.getenv("BOCHA_API_KEY", "")

# === 工作区（Agent 文件操作授权根目录）===
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", str(BASE_DIR / "workspace"))

# === 本地数据目录 ===
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_data"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))
