"""Doc cau hinh tu file .env (thuan stdlib, khong can python-dotenv)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path = ROOT / ".env") -> dict:
    """Doc .env dang KEY=VALUE (neu co). Container khong co .env -> chi dung os.environ."""
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


class Config:
    def __init__(self, env: dict | None = None):
        file_env = env if env is not None else load_env()
        # os.environ LUON uu tien hon .env (quan trong cho container: config qua ENV/-e)
        def g(key, default=""):
            return os.environ.get(key, file_env.get(key, default))
        self.env = {**file_env, **dict(os.environ)}
        # Typesense
        self.ts_host = g("TYPESENSE_HOST", "localhost")
        self.ts_port = int(g("TYPESENSE_PORT", "8108"))
        self.ts_protocol = g("TYPESENSE_PROTOCOL", "http")
        self.ts_api_key = g("TYPESENSE_API_KEY", "")
        self.collection = g("TYPESENSE_COLLECTION", "legal_articles")
        # Embedding proxy
        self.embed_base_url = g("EMBED_BASE_URL", "").rstrip("/")
        self.embed_api_key = g("EMBED_API_KEY", "")
        self.embed_model = g("EMBED_MODEL", "Qwen3-Embedding-4B")
        self.embed_dim = int(g("EMBED_DIM", "2560"))
        self.embed_batch = int(g("EMBED_BATCH_SIZE", "16"))
        # Reranker
        self.rerank_model = g("RERANK_MODEL", "")
        self.rerank_enable = g("RERANK_ENABLE", "true").lower() in ("1", "true", "yes")
        # Ingest
        self.subchunk_threshold = int(g("SUBCHUNK_CHAR_THRESHOLD", "4000"))
        # MCP server
        self.mcp_host = g("MCP_HOST", "0.0.0.0")
        self.mcp_port = int(g("MCP_PORT", "8000"))
        self.search_alpha = float(g("SEARCH_ALPHA", "0.7"))

    @property
    def ts_base(self) -> str:
        return f"{self.ts_protocol}://{self.ts_host}:{self.ts_port}"
