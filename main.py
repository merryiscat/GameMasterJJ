"""
GMJJ 메인 서버

FastAPI 앱을 실행합니다.
어드민 페이지: http://localhost:8000/admin/

사용법:
    uv run uvicorn main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.admin.router import router as admin_router

# ============================================================
# FastAPI 앱 생성
# ============================================================
app = FastAPI(title="GMJJ", description="보드게임 룰 안내/TRPG GM 애플리케이션")

# 이미지 static 파일 서빙 (data/images → /static/images)
images_dir = Path(__file__).parent / "data" / "images"
images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="images")

# 어드민 라우터 등록
app.include_router(admin_router)


@app.get("/")
async def root():
    """루트 페이지 - 헬스체크 겸용"""
    return {"message": "GMJJ 서버 실행 중", "admin": "/admin/"}


# ============================================================
# 직접 실행 시
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
