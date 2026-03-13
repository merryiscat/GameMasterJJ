"""
BGG API로 보드게임 샘플 10개 수집 및 분석
BGG XML API2: https://boardgamegeek.com/xmlapi2/
"""

import requests
import xml.etree.ElementTree as ET
import json
import time

BGG_API_BASE = "https://boardgamegeek.com/xmlapi2"

# BGG 역대 랭킹 상위 10개 게임 ID (잘 알려진 인기작)
TOP_GAME_IDS = [
    174430,  # Gloomhaven
    224517,  # Brass: Birmingham
    167791,  # Terraforming Mars
    169786,  # Scythe
    312484,  # Lost Ruins of Arnak
    266192,  # Wingspan
    173346,  # 7 Wonders Duel
    291457,  # Gloomhaven: Jaws of the Lion
    187645,  # Star Wars: Rebellion
    182028,  # Through the Ages: A New Story of Civilization
]


def fetch_games(game_ids: list[int]) -> str:
    """BGG API에서 게임 상세정보 가져오기"""
    ids_str = ",".join(str(gid) for gid in game_ids)
    url = f"{BGG_API_BASE}/thing?id={ids_str}&stats=1"

    print(f"요청 URL: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_games(xml_text: str) -> list[dict]:
    """XML 응답을 파싱하여 딕셔너리 리스트로 변환"""
    root = ET.fromstring(xml_text)
    games = []

    for item in root.findall("item"):
        game = {}

        # 기본 정보
        game["bgg_id"] = int(item.get("id"))
        game["type"] = item.get("type")

        # 이름 (primary + alternate)
        names = {}
        for name_el in item.findall("name"):
            names[name_el.get("type")] = name_el.get("value")
        game["name"] = names.get("primary", "")
        game["alternate_names"] = [
            n.get("value") for n in item.findall("name") if n.get("type") == "alternate"
        ]

        # 기본 수치
        game["year_published"] = _val(item, "yearpublished")
        game["min_players"] = _val(item, "minplayers")
        game["max_players"] = _val(item, "maxplayers")
        game["playing_time"] = _val(item, "playingtime")
        game["min_playtime"] = _val(item, "minplaytime")
        game["max_playtime"] = _val(item, "maxplaytime")
        game["min_age"] = _val(item, "minage")

        # 설명
        desc_el = item.find("description")
        game["description"] = desc_el.text[:200] + "..." if desc_el is not None and desc_el.text else ""

        # 이미지
        game["thumbnail"] = _text(item, "thumbnail")
        game["image"] = _text(item, "image")

        # 카테고리, 메카니즘, 디자이너, 퍼블리셔
        game["categories"] = _links(item, "boardgamecategory")
        game["mechanics"] = _links(item, "boardgamemechanic")
        game["designers"] = _links(item, "boardgamedesigner")
        game["publishers"] = _links(item, "boardgamepublisher")
        game["families"] = _links(item, "boardgamefamily")

        # 통계 (ratings)
        ratings = item.find(".//ratings")
        if ratings is not None:
            game["avg_rating"] = _val(ratings, "average")
            game["bgg_rank"] = _get_rank(ratings, "boardgame")
            game["num_ratings"] = _val(ratings, "usersrated")
            game["weight"] = _val(ratings, "averageweight")  # 난이도 (1~5)
            game["num_owned"] = _val(ratings, "owned")

        games.append(game)

    return games


def _val(parent, tag):
    """value 속성 추출"""
    el = parent.find(tag)
    return el.get("value") if el is not None else None


def _text(parent, tag):
    """텍스트 내용 추출"""
    el = parent.find(tag)
    return el.text if el is not None else None


def _links(item, link_type):
    """link 요소에서 특정 타입 추출"""
    return [
        {"id": int(link.get("id")), "name": link.get("value")}
        for link in item.findall("link")
        if link.get("type") == link_type
    ]


def _get_rank(ratings, rank_type):
    """BGG 랭킹 추출"""
    for rank in ratings.findall(".//rank"):
        if rank.get("name") == rank_type:
            val = rank.get("value")
            return int(val) if val != "Not Ranked" else None
    return None


def print_summary(games: list[dict]):
    """수집 결과 요약 출력"""
    print("\n" + "=" * 70)
    print(f"수집 완료: {len(games)}개 게임")
    print("=" * 70)

    for g in games:
        print(f"\n{'─' * 50}")
        print(f"🎲 {g['name']} ({g['year_published']})")
        print(f"   BGG ID: {g['bgg_id']} | 랭킹: #{g.get('bgg_rank', 'N/A')}")
        print(f"   평점: {g.get('avg_rating', 'N/A')} | 난이도: {g.get('weight', 'N/A')}/5")
        print(f"   인원: {g['min_players']}~{g['max_players']}명 | 시간: {g['playing_time']}분")
        print(f"   카테고리: {', '.join(c['name'] for c in g['categories'])}")
        print(f"   메카니즘: {', '.join(m['name'] for m in g['mechanics'][:5])}")
        print(f"   퍼블리셔 수: {len(g['publishers'])}개")
        print(f"   별명 수: {len(g['alternate_names'])}개")

    # 필드 분석
    print(f"\n{'=' * 70}")
    print("📊 데이터 필드 분석")
    print("=" * 70)

    if games:
        all_keys = list(games[0].keys())
        print(f"\n총 필드 수: {len(all_keys)}")
        print(f"필드 목록: {', '.join(all_keys)}")

        # 카테고리 전체 목록
        all_categories = set()
        all_mechanics = set()
        for g in games:
            for c in g["categories"]:
                all_categories.add(c["name"])
            for m in g["mechanics"]:
                all_mechanics.add(m["name"])

        print(f"\n카테고리 종류 ({len(all_categories)}개): {', '.join(sorted(all_categories))}")
        print(f"\n메카니즘 종류 ({len(all_mechanics)}개): {', '.join(sorted(all_mechanics))}")


if __name__ == "__main__":
    print("BGG API에서 샘플 보드게임 10개 수집 중...")

    xml_text = fetch_games(TOP_GAME_IDS)
    games = parse_games(xml_text)

    # JSON 저장
    output_path = "scripts/bgg_sample_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)
    print(f"\n✅ JSON 저장: {output_path}")

    # 요약 출력
    print_summary(games)
