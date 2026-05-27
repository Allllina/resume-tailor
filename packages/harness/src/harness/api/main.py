"""FastAPI app entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .health import router as health_router
from .knowledge import router as knowledge_router
from .runs import router as runs_router
from .tier1_tailor import router as tier1_router
from .users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Gate 2: warm the LLM provider singleton so its circuit breaker exists
    # from the first request (avoids a cold-start window where a flaky LLM
    # call would silently not update the monitor).
    from harness.llm.factory import get_llm_provider
    try:
        get_llm_provider()
        logger.info("LLM provider singleton initialised at startup")
    except Exception as e:
        logger.warning(f"LLM provider init failed at startup (will retry on first request): {e}")
    yield


app = FastAPI(title="Harness Layer", version="0.6.2", lifespan=lifespan)

# Allow the local UI dev server (Vite default + alternates) to call us.
# Tighten in prod via HARNESS_CORS_ORIGINS env var override.
app.add_middleware(
    CORSMiddleware,
    # Dev origins — vite/tanstack assigns ports dynamically (5173, 4173, 4174,
    # 5183, 8080 all observed). Allow any localhost / 127.0.0.1 origin via regex.
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(knowledge_router)
app.include_router(tier1_router)
app.include_router(runs_router)
app.include_router(users_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
