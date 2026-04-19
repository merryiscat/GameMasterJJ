"""
사용자 프론트엔드 라우터

모바일 앱 스타일의 웹 UI를 제공합니다.
홈, 보드게임 목록, 게임 상세 페이지를 포함합니다.
"""

import io
import os

from fastapi import APIRouter, Request, Query, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from web.frontend import service

router = APIRouter(tags=["frontend"])

# 프론트엔드 전용 템플릿 디렉토리
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


import re
import markupsafe

def md_to_html(text: str) -> str:
    """간단한 마크다운 → HTML 변환 (헤더, 리스트, 테이블, 볼드 지원)"""
    if not text:
        return ""
    lines = text.split("\n")
    result = []
    in_list = False
    in_table = False
    table_has_header = False

    for line in lines:
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            if in_list:
                result.append("</ul>")
                in_list = False
            if in_table:
                result.append("</tbody></table>")
                in_table = False
                table_has_header = False
            continue

        # 구분선 (--- 만 있는 줄은 무시, 테이블 구분선은 아래에서 처리)
        if re.match(r'^-{3,}$', stripped):
            continue

        # 테이블 행 (| 로 시작하고 | 로 끝나는 줄)
        if stripped.startswith("|") and stripped.endswith("|"):
            # 테이블 구분선 (|---|---|) 은 건너뛰되, 헤더 완료 표시
            if re.match(r'^\|[\s\-:]+\|$', stripped.replace("|", "").strip().replace("-", "").replace(":", "").replace(" ", "")) or \
               all(c in "-|: " for c in stripped):
                if in_table and not table_has_header:
                    # 헤더 행 닫기 → tbody 시작
                    result.append("</thead><tbody>")
                    table_has_header = True
                continue

            # 셀 추출
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            cells = [re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', c) for c in cells]

            if not in_table:
                # 테이블 시작 (첫 행 = 헤더)
                if in_list:
                    result.append("</ul>")
                    in_list = False
                result.append('<table class="rule-table"><thead>')
                result.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
                in_table = True
                table_has_header = False
            else:
                # 데이터 행
                result.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            continue

        # 테이블 중이면 닫기
        if in_table:
            result.append("</tbody></table>")
            in_table = False
            table_has_header = False

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
        if stripped.startswith("# "):
            if in_list:
                result.append("</ul>")
                in_list = False
            result.append(f"<h2>{stripped[2:]}</h2>")
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
    if in_table:
        result.append("</tbody></table>")

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


class PlayMessage(BaseModel):
    game_id: int
    message: str
    history: list[dict] = []
    player_count: int | None = None  # 인원수 (첫 응답 시 설정)


@router.post("/api/play")
async def api_play(msg: PlayMessage):
    """
    게임 진행 채팅 API

    룰 Q&A와 달리, 실제 GM처럼 한 단계씩 게임을 진행한다.
    - 짧고 구어체로 답변 (음성 모드 대응)
    - 한 번에 한 단계만 안내
    - 플레이어 행동을 기다린 후 다음 안내
    """
    import openai
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return JSONResponse({"reply": "OpenAI API 키가 설정되지 않았습니다."})

    game = service.get_game_detail(msg.game_id)
    rules = service.get_game_rules(msg.game_id)
    playbook = service.get_game_playbook(msg.game_id)

    # 플레이북을 텍스트로 구성
    playbook_text = ""
    if playbook:
        for step in playbook:
            playbook_text += f"\n### {step['step_order']}. [{step['phase']}] {step['title']}\n"
            playbook_text += step.get("content", "") + "\n"
            # 인원별 변형이 있고, 인원수가 지정되어 있으면 해당 정보 추가
            variants = step.get("player_variants") or {}
            if variants and msg.player_count:
                key = f"{msg.player_count}p"
                if key in variants:
                    playbook_text += f"\n({msg.player_count}인 전용: {variants[key]})\n"
            if step.get("tips"):
                playbook_text += f"\n(팁: {step['tips']})\n"

    # 인원별 세팅 정보
    setup_by_player = ""
    if rules:
        extra = rules.get("extra_sections") or {}
        setup_by_player = extra.get("setup_by_player", "") or rules.get("setup_by_player", "")

    # 시스템 프롬프트: GM 진행 모드
    system_parts = [
        f"당신은 보드게임 '{game['name_ko']}'의 게임마스터 JJ입니다.",
        "",
        "## 역할",
        "실제 보드게임 카페의 GM처럼 게임을 한 단계씩 진행합니다.",
        "",
        "## 규칙",
        "1. 한 번에 한 단계만 안내하세요. 전체 규칙을 한꺼번에 설명하지 마세요.",
        "2. 플레이어가 행동을 완료했다고 말하면 다음 단계로 넘어가세요.",
        "3. 답변은 3~5문장 이내로 짧게. 음성으로 읽기 편한 구어체를 사용하세요.",
        "4. 마크다운 헤더(#, ##)를 쓰지 마세요. 굵은 글씨(**텍스트**)는 핵심 키워드에만 사용하세요.",
        "5. 세팅이 끝나면 턴 진행을 안내하고, 각 플레이어 차례마다 할 수 있는 행동을 알려주세요.",
        "6. 게임 종료 조건이 충족되면 점수 계산을 안내하세요.",
        "7. '~해주세요', '~하시면 됩니다' 같은 안내 말투를 사용하세요.",
    ]

    if msg.player_count:
        system_parts.append(f"\n## 현재 게임 인원: {msg.player_count}명")

    if setup_by_player:
        system_parts.append(f"\n## 인원별 세팅 규칙\n{setup_by_player}")

    if playbook_text:
        system_parts.append(f"\n## 플레이북 (진행 순서)\n{playbook_text}")

    # 핵심 룰 섹션도 참고용으로 포함 (요약만)
    if rules:
        for key, label in [
            ("setup", "게임 준비"), ("gameplay", "게임 진행"),
            ("end_condition", "종료 조건"), ("scoring", "점수 계산"),
        ]:
            content = rules.get(key, "")
            if content:
                system_parts.append(f"\n## {label} (참고)\n{content}")

    system_prompt = "\n".join(system_parts)

    # 대화 히스토리
    messages = [{"role": "system", "content": system_prompt}]
    for h in msg.history[-10:]:
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": msg.message})

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=400,  # 짧은 답변 강제
            temperature=0.7,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"응답 생성 중 오류가 발생했습니다: {str(e)}"

    return JSONResponse({"reply": reply})


# ============================================================
# 음성 API (STT / TTS)
# ============================================================

@router.post("/api/stt")
async def api_stt(audio: UploadFile = File(...)):
    """음성 → 텍스트 변환 (OpenAI gpt-4o-mini-transcribe)"""
    import openai
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return JSONResponse({"text": ""}, status_code=500)

    try:
        audio_bytes = await audio.read()
        client = openai.OpenAI(api_key=api_key)

        # 파일명/MIME으로 OpenAI SDK가 형식을 자동 감지
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("audio.webm", audio_bytes, audio.content_type or "audio/webm"),
            language="ko",
        )
        return JSONResponse({"text": transcription.text})
    except Exception as e:
        return JSONResponse({"text": "", "error": str(e)}, status_code=500)


class TtsRequest(BaseModel):
    text: str
    voice: str = "coral"
    instructions: str = (
        "당신은 친근한 보드게임 카페의 게임마스터입니다. "
        "따뜻하고 밝은 목소리로, 보드게임을 안내하는 사장님처럼 읽어주세요. "
        "한국어로 자연스럽게 말해주세요."
    )


@router.post("/api/tts")
async def api_tts(req: TtsRequest):
    """텍스트 → 음성 변환 (OpenAI gpt-4o-mini-tts)"""
    import openai
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return JSONResponse({"error": "API key missing"}, status_code=500)

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=req.voice,
            input=req.text,
            instructions=req.instructions,
            response_format="mp3",
        )
        audio_bytes = response.content
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Length": str(len(audio_bytes))},
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
