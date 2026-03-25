from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import watermark
from routers import auth, posts, access

app = FastAPI(title="Secugram TDC", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(posts.router, tags=["posts"])
app.include_router(access.router, tags=["access"])
app.include_router(watermark.router, prefix="/trust", tags=["watermark"])

if __name__ == "__main__":
    import uvicorn, os
    port = int(os.environ.get("PORT", 8300))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
