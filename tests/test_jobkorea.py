from datetime import datetime

from sources.jobkorea import _parse_card

REAL_CARD_TEXT = """신입 지원 가능
스크랩
전산관리 신입사원 채용
㈜엘에스티
전남광주 서구
물류·운송·배송, R&D·연구원
즉시 지원
신입
07/24(금) 등록
•
08/23(일) 마감"""


def test_parse_card_extracts_fields_from_real_card_text():
    posting = _parse_card("/Recruit/GI_Read/49646333", REAL_CARD_TEXT)

    assert posting is not None
    assert posting.source == "jobkorea"
    assert posting.external_id == "49646333"
    assert posting.title == "전산관리 신입사원 채용"
    assert posting.company == "㈜엘에스티"
    assert posting.location == "전남광주 서구"
    assert posting.url == "https://www.jobkorea.co.kr/Recruit/GI_Read/49646333"
    assert posting.experience_years_required == 0
    # JobKorea gives no year (MM/DD); normalized to YYYY-MM-DD using the
    # current year.
    assert posting.posted_date == f"{datetime.now().year}-07-24"
    assert posting.closing_date == f"{datetime.now().year}-08-23"


def test_parse_card_reads_numeric_experience():
    text = "스크랩\n제목\n회사\n서울 강남구\n태그\n즉시 지원\n경력2년↑\n07/01(수) 등록\n•\n08/01(토) 마감"
    posting = _parse_card("/Recruit/GI_Read/1", text)
    assert posting.experience_years_required == 2


def test_parse_card_returns_none_when_no_scrap_marker():
    assert _parse_card("/Recruit/GI_Read/1", "이상한 텍스트만 있음") is None
