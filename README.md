# 오늘의 핵심 뉴스 (@onul_ns) 카드뉴스 만들기

## 폴더 안에 있는 것
| 이름 | 뭐예요? |
|---|---|
| `CLAUDE.md` | Claude Code가 읽는 작업 설명서예요. 뉴스 고르는 기준, 사실 확인 방법, 카드 문구 규칙이 다 들어 있어요 |
| `make_cards.py` | 문구를 카드 이미지로 바꿔 주는 프로그램이에요 |
| `fonts/` | 카드에 쓰는 한글 글꼴(Noto, 무료 글꼴)이에요 |
| `examples/` | 예시 문구(`cards_example.json`)와 예시 카드 이미지예요 |

## Claude Code에서 쓰는 법
1. 이 폴더를 Claude Code에서 열어요(이 폴더를 작업 폴더로 선택).
2. "오늘 카드뉴스 만들어 줘"라고 말해요.
3. Claude가 `CLAUDE.md`를 읽고 뉴스 조사 → 사실 확인 → 카드 5장 + 캡션을 만들어 줘요.

규칙을 바꾸고 싶으면 Claude Code에 "제목을 더 짧게 하도록 CLAUDE.md 고쳐 줘"처럼 말하면 돼요.

## 참고
- 인스타그램에는 직접 "올려"라고 하기 전까지 아무것도 올리지 않도록 적어 두었어요.
- 매일 아침 7시 13분 예약 작업은 이 GitHub 저장소(donghyeonim/onul_ns_project)를 내려받아 `CLAUDE.md`대로 카드를 만들어요. 그래서 여기서 `CLAUDE.md`나 `make_cards.py`를 고쳐 GitHub에 올리면 다음 날 아침부터 바로 반영돼요.
