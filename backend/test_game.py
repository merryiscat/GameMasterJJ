#!/usr/bin/env python3
"""
GameMasterJJ 대화형 테스트 스크립트
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"
SESSION_ID = "interactive-test-session"
USER_ID = "test-player"

def send_message(content):
    """메시지를 에이전트 시스템에 전송"""
    url = f"{BASE_URL}/api/v1/sessions/{SESSION_ID}/messages"

    payload = {
        "content": content,
        "user_id": USER_ID
    }

    try:
        print(f"\n🎮 플레이어: {content}")
        print("⏳ AI 처리중...")

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()

            if result["success"]:
                print(f"\n🤖 {result['agent'].upper()} 에이전트:")
                print("=" * 60)
                print(result["message"])
                print("=" * 60)
                print(f"📊 처리 정보: {result['processing_info']['handoff_chain']} "
                      f"({result['processing_info']['processing_time']:.2f}초)")
                return True
            else:
                print(f"❌ 에러: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP 에러: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"❌ 연결 에러: {str(e)}")
        return False

def test_scenarios():
    """미리 정의된 테스트 시나리오들"""
    scenarios = [
        "I roll a d20 for a strength check",
        "I want to talk to the mysterious hooded figure in the corner",
        "Tell me about the history of this ancient castle",
        "I look around the room for any hidden passages",
        "I cast a fireball spell at the orc",
        "What do I know about the Dragon of Mount Shadowpeak?"
    ]

    print("🎯 미리 정의된 테스트 시나리오:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario}")

    choice = input("\n테스트할 시나리오 번호를 선택하세요 (1-6): ")

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(scenarios):
            return send_message(scenarios[idx])
        else:
            print("❌ 잘못된 번호입니다.")
            return False
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        return False

def interactive_mode():
    """대화형 모드"""
    print("\n🎲 대화형 TRPG 모드")
    print("'quit' 또는 'exit'를 입력하면 종료됩니다.")

    while True:
        try:
            user_input = input("\n🎮 당신의 행동: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 게임을 종료합니다!")
                break

            if not user_input:
                continue

            send_message(user_input)

        except KeyboardInterrupt:
            print("\n\n👋 게임을 종료합니다!")
            break
        except Exception as e:
            print(f"❌ 에러: {str(e)}")

def main():
    """메인 함수"""
    print("🎮 GameMasterJJ 테스트 스크립트")
    print("=" * 50)

    # 서버 연결 확인
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=5)
        if response.status_code == 200:
            print("✅ 서버 연결 성공!")
        else:
            print("❌ 서버 연결 실패!")
            return
    except Exception as e:
        print(f"❌ 서버에 연결할 수 없습니다: {str(e)}")
        print("서버가 실행 중인지 확인해주세요: python start.py")
        return

    while True:
        print("\n📋 선택하세요:")
        print("1. 미리 정의된 시나리오 테스트")
        print("2. 자유롭게 대화하기")
        print("3. 종료")

        choice = input("\n선택: ").strip()

        if choice == "1":
            test_scenarios()
        elif choice == "2":
            interactive_mode()
        elif choice == "3":
            print("👋 안녕히 가세요!")
            break
        else:
            print("❌ 1, 2, 3 중에서 선택해주세요.")

if __name__ == "__main__":
    main()