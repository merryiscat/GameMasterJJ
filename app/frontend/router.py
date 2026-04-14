"""
사용자 프론트엔드 라우터

모바일 앱 스타일의 웹 UI를 제공합니다.
홈, 보드게임 목록, 게임 상세 페이지를 포함합니다.
"""

import os
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.frontend import service

router = APIRouter(tags=["frontend"])

# 프론트엔드 전용 템플릿 디렉토리
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


import re
import markupsafe

def md_to_html(text: str) -> str:
    """간단한 마크다운 → HTML 변환"""
    if not text:
        return ""
    lines = text.split("\n")
    result = []
    in_list = False

    for line in lines:
        stripped = line.strip()

        # 빈 줄 (연속 빈 줄 무시)
        if not stripped:
            if in_list:
                result.append("</ul>")
                in_list = False
            continue

        # 헤더
        if stripped.startswith("### "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f"<h3>{stripped[4:]}</h3>")
            continue
        if stripped.startswith("## "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f"<h2>{stripped[3:]}</h2>")
            continue

        # 리스트 항목
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                result.append("<ul>")
                in_list = True
            content = stripped[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            result.append(f"<li>{content}</li>")
            continue

        # 번호 리스트
        num_match = re.match(r'^(\d+)\.\s+(.+)', stripped)
        if num_match:
            if not in_list:
                result.append("<ul>")
                in_list = True
            content = num_match.group(2)
            content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
            result.append(f"<li>{content}</li>")
            continue

        # 일반 텍스트
        if in_list:
            result.append("</ul>")
            in_list = False
        stripped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', stripped)
        result.append(f"<p>{stripped}</p>")

    if in_list:
        result.append("</ul>")

    return "\n".join(result)


templates.env.filters["md"] = lambda text: markupsafe.Markup(md_to_html(text))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """홈 화면 - 보드게임 / TRPG 진입"""
    return templates.TemplateResponse("home.html", {
        "request": request,
        "active_nav": "home",
        "nav_mode": "main",
    })


@router.get("/mygame", response_class=HTMLResponse)
async def mygame(request: Request):
    """Mygame - 즐겨찾기한 게임 목록"""
    return templates.TemplateResponse("mygame.html", {
        "request": request,
        "active_nav": "mygame",
        "nav_mode": "mygame",
    })


@router.get("/api/mygames", response_class=JSONResponse)
async def api_mygames(ids: str = Query("")):
    """즐겨찾기 게임 데이터 조회 API (ids=1,2,3 형태)"""
    if not ids:
        return []
    try:
        game_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        return []
    games = service.get_games_by_ids(game_ids)
    return games


@router.get("/games", response_class=HTMLResponse)
async def games_list(
    request: Request,
    page: int = Query(1, ge=1),
    search: str = Query(""),
    tab: str = Query("all"),
):
    """보드게임 목록 (검색 + 페이지네이션)"""
    try:
        result = service.list_games_with_images(
            page=page,
            search=search,
            per_page=20,
        )
        error = None
    except Exception as e:
        result = {"games": [], "total": 0, "page": 1, "total_pages": 1}
        error = str(e)

    return templates.TemplateResponse("games.html", {
        "request": request,
        "active_nav": "home",
        "nav_mode": "game",
        "games": result["games"],
        "total": result["total"],
        "page": result["page"],
        "total_pages": result["total_pages"],
        "search": search,
        "tab": tab,
        "error": error,
    })


@router.get("/games/{game_id}", response_class=HTMLResponse)
async def game_detail(request: Request, game_id: int):
    """게임 상세 페이지"""
    from_page = request.query_params.get("from", "games")
    game = service.get_game_detail(game_id)
    if not game:
        return HTMLResponse("<h1>게임을 찾을 수 없습니다</h1>", status_code=404)

    return templates.TemplateResponse("game_detail.html", {
        "request": request,
        "active_nav": "mygame" if from_page == "mygame" else "home",
        "nav_mode": "mygame" if from_page == "mygame" else "game",
        "game": game,
        "from_page": from_page,
    })


@router.get("/games/{game_id}/chat", response_class=HTMLResponse)
async def game_chat(request: Request, game_id: int):
    """게임마스터 안내 - 룰 채팅 페이지"""
    from_page = request.query_params.get("from", "games")
    game = service.get_game_detail(game_id)
    if not game:
        return HTMLResponse("<h1>게임을 찾을 수 없습니다</h1>", status_code=404)

    rules = service.get_game_rules(game_id)

    return templates.TemplateResponse("game_chat.html", {
        "request": request,
        "active_nav": "mygame" if from_page == "mygame" else "home",
        "nav_mode": "mygame" if from_page == "mygame" else "game",
        "game": game,
        "rules": rules,
        "from_page": from_page,
    })


@router.get("/games/{game_id}/play", response_class=HTMLResponse)
async def game_play(request: Request, game_id: int):
    """게임 진행 페이지 - 에이전트와 함께 플레이"""
    from_page = request.query_params.get("from", "games")
    game = service.get_game_detail(game_id)
    if not game:
        return HTMLResponse("<h1>게임을 찾을 수 없습니다</h1>", status_code=404)

    rules = service.get_game_rules(game_id)

    return templates.TemplateResponse("game_play.html", {
        "request": request,
        "active_nav": "home",
        "nav_mode": "game",
        "game": game,
        "rules": rules,
        "from_page": from_page,
    })


class ChatMessage(BaseModel):
    game_id: int
    message: str
    history: list[dict] = []


@router.post("/api/chat")
async def api_chat(msg: ChatMessage):
    """게임 룰 Q&A 채팅 API (OpenAI)"""
    import openai
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return JSONResponse({"reply": "OpenAI API 키가 설정되지 않았습니다."})

    # 게임 정보 + 룰 데이터로 시스템 프롬프트 구성
    game = service.get_game_detail(msg.game_id)
    rules = service.get_game_rules(msg.game_id)

    system_parts = [
        f"당신은 보드게임 '{game['name_ko']}'의 룰 안내 전문가 게임마스터 JJ입니다.",
        "플레이어의 질문에 친절하고 정확하게 답변해주세요.",
        "룰에 없는 내용은 추측하지 말고, 모르면 모른다고 답하세요.",
    ]

    if game.get("description_ko"):
        system_parts.append(f"\n## 게임 설명\n{game['description_ko']}")

    if rules:
        section_names = {
            "intro": "게임 소개", "components": "구성품",
            "setup": "게임 준비", "gameplay": "게임 진행",
            "end_condition": "종료 조건", "scoring": "점수 계산",
            "win_condition": "승리 조건", "special_rules": "특수 규칙",
            "faq": "FAQ",
        }
        for key, label in section_names.items():
            content = rules.get(key)
            if content:
                system_parts.append(f"\n## {label}\n{content}")

    system_prompt = "\n".join(system_parts)

    # 대화 히스토리 구성
    messages = [{"role": "system", "content": system_prompt}]
    for h in msg.history[-10:]:  # 최근 10개만
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": msg.message})

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    return JSONResponse({"reply": reply})
