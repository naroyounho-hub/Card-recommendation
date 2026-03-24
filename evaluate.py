"""
Base 모델 vs RAG 모델 비교 평가 스크립트
- Base: GPT에 직접 질문 (검색 증강 없음)
- RAG: Hybrid Search + Multi-Query → GPT
- 평가 지표: 임베딩 코사인 유사도 (응답 vs 이상적 답변)
"""
import json
import time
from src.chain import get_base_response, get_recommendation
from src.utils import compute_similarity

# 평가용 페르소나 + 이상적 답변 기준
EVAL_CASES = [
    {
        "name": "이세봉(26세, 유학생)",
        "persona": "서울 소재 대학원 재학 중인 중국 유학생입니다. 월 수입 약 120만원이고, 월세 45만원, 편의점 식비 월 25만원, 교통비 월 2만5천원, 해외송금 수수료 월 5만원, 알리익스프레스 직구 월 15만원을 씁니다. 해외결제 수수료 면제, 편의점 할인, 교통 할인 카드를 추천해주세요.",
        "ideal": "해외결제 수수료 면제 카드, 편의점 할인 카드, 대중교통 할인 카드를 추천합니다. 해외 직구와 송금이 많으므로 해외결제 수수료가 면제되는 카드가 가장 중요하고, 편의점과 교통비 할인도 월 고정 지출을 줄여줍니다.",
    },
    {
        "name": "김지연(34세, 직장인 여성)",
        "persona": "서울 거주 마케팅회사 대리, 월 실수령 약 280만원입니다. 해외여행 연 2회, 의료비 월 20만원, 주유비 연 180만원, 온라인쇼핑 월 25만원, 커피 월 10만원을 씁니다. 항공 마일리지, 해외결제 수수료 면제, 의료비 할인 카드를 추천해주세요.",
        "ideal": "항공 마일리지 적립 카드, 해외결제 수수료 면제 카드, 의료비 할인 카드를 추천합니다. 연 2회 해외여행으로 마일리지 적립이 효과적이고, 주유 할인과 온라인쇼핑 캐시백도 소비 패턴에 적합합니다.",
    },
    {
        "name": "박민수(42세, 자영업자)",
        "persona": "경기도 거주 치킨 프랜차이즈 운영, 월 카드 지출 약 500만원입니다. 마트 식자재 월 200만원, 주유비 월 40만원, 통신비 월 20만원, 외식 월 30만원을 씁니다. 마트 적립, 주유 할인, 포인트 환급 카드를 추천해주세요.",
        "ideal": "마트 대량 구매 적립률이 높은 카드, 주유 할인 카드, 높은 전월실적 충족 시 포인트 환급이 큰 카드를 추천합니다. 월 500만원 지출로 높은 실적 구간 혜택을 최대화할 수 있습니다.",
    },
    {
        "name": "최수아(28세, 사회초년생)",
        "persona": "서울 자취 IT 스타트업 신입 개발자, 월 실수령 약 280만원입니다. 월세 70만원, 배달앱 식비 월 35만원, OTT 구독 월 4만원, 쿠팡 쇼핑 월 25만원을 씁니다. 배달앱 할인, 구독서비스 할인, 쿠팡 적립 카드를 추천해주세요.",
        "ideal": "배달앱 할인 카드, 온라인 쇼핑 적립 카드, OTT 구독 할인 카드를 추천합니다. 배달앱과 쿠팡 지출이 월 60만원으로 큰 비중을 차지하므로 이 영역의 할인이 가장 효과적입니다.",
    },
    {
        "name": "정태양(52세, 중년 직장인)",
        "persona": "수도권 거주 대기업 부장, 월 실수령 약 600만원입니다. 골프 월 80만원, 고급 외식 월 70만원, 리조트/호텔 연 240만원, 백화점 월 50만원을 씁니다. 골프장 할인, 라운지, 호텔 할인, 백화점 VIP 혜택 카드를 추천해주세요.",
        "ideal": "골프장 할인 및 라운지 이용 가능한 프리미엄 카드, 호텔 할인 카드, 백화점 VIP 혜택 카드를 추천합니다. 높은 소득과 프리미엄 소비 패턴에 맞는 연회비 높은 프리미엄 카드가 적합합니다.",
    },
]


def run_evaluation():
    results = []

    print("=" * 60)
    print("Base 모델 vs RAG 모델 비교 평가")
    print("=" * 60)

    for case in EVAL_CASES:
        print(f"\n{'─' * 40}")
        print(f"페르소나: {case['name']}")
        print(f"{'─' * 40}")

        # Base 모델 응답
        print("  [Base] 응답 생성 중...")
        t0 = time.time()
        base_response = get_base_response(case["persona"])
        base_time = time.time() - t0

        # RAG 모델 응답
        print("  [RAG]  응답 생성 중...")
        t0 = time.time()
        rag_result = get_recommendation(case["persona"])
        rag_time = time.time() - t0
        rag_response = rag_result["answer"]

        # 유사도 평가
        base_sim = compute_similarity(base_response, case["ideal"])
        rag_sim = compute_similarity(rag_response, case["ideal"])
        improvement = rag_sim - base_sim

        result = {
            "name": case["name"],
            "base_similarity": round(base_sim, 4),
            "rag_similarity": round(rag_sim, 4),
            "improvement": round(improvement, 4),
            "base_time": round(base_time, 2),
            "rag_time": round(rag_time, 2),
            "base_response": base_response[:200],
            "rag_response": rag_response[:200],
        }
        results.append(result)

        print(f"  Base 유사도: {base_sim:.4f} ({base_time:.1f}s)")
        print(f"  RAG  유사도: {rag_sim:.4f} ({rag_time:.1f}s)")
        print(f"  개선폭:      {improvement:+.4f}")

    # 요약
    avg_base = sum(r["base_similarity"] for r in results) / len(results)
    avg_rag = sum(r["rag_similarity"] for r in results) / len(results)
    avg_improve = sum(r["improvement"] for r in results) / len(results)

    print(f"\n{'=' * 60}")
    print("평균 결과")
    print(f"{'=' * 60}")
    print(f"  Base 평균 유사도: {avg_base:.4f}")
    print(f"  RAG  평균 유사도: {avg_rag:.4f}")
    print(f"  평균 개선폭:      {avg_improve:+.4f}")

    # 결과 저장
    output = {
        "summary": {
            "avg_base_similarity": round(avg_base, 4),
            "avg_rag_similarity": round(avg_rag, 4),
            "avg_improvement": round(avg_improve, 4),
        },
        "details": results,
    }

    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: eval_results.json")
    return output


if __name__ == "__main__":
    run_evaluation()
