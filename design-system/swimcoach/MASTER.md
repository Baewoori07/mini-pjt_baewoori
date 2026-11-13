# SwimCoach 디자인 시스템 (MASTER)

> **적용 규칙:** 특정 화면을 만들 때는 먼저 `design-system/swimcoach/pages/[화면].md`를 확인하고, 있으면 그 규칙이 이 파일보다 우선합니다. 없으면 이 파일을 따릅니다.

**프로젝트:** SwimCoach — 마스터즈 수영 선수를 위한 대회 대비 훈련 코치 (로컬 웹앱, `static/index.html` 단일 페이지)
**생성:** 2026-11-12, `ui-ux-pro-max` 스킬로 초안 생성 후 서비스에 맞게 조정
**기반 검색:** `search.py "water hydration tracker sports training progress" --design-system` (색), `"masters swimming training coach ..."` (글꼴), `"sports performance analytics dashboard"` (스타일)

---

## 1. 디자인 방향

| 항목 | 결정 | 이유 |
|---|---|---|
| 성격 | **차분한 물 + 정확한 기록** | 사용자는 매일 계획을 확인하고 기록을 남기는 성인 선수. 들뜬 랜딩 페이지가 아니라 매일 쓰는 도구 |
| 스타일 | **Data-Dense Dashboard + 레인 모티프** | 세트표·주차 타임라인·CSS 기록이 핵심 정보. 카드·표 중심, 여백은 넉넉하되 장식은 최소 |
| 색 | **풀장 블루(주) + 레인 청록(보조)**, 시기별 3색(기초·강화·테이퍼) | 수영 맥락을 바로 전달. 시기 색은 주기화 계획을 한눈에 구분 |
| 숫자 | **Barlow Condensed + tabular-nums** | 기록·거리·페이스(1:32/100m)를 전광판처럼 크고 정렬되게 |
| 한글 | **Noto Sans KR** | Barlow에는 한글이 없음. 본문·설명은 Noto Sans KR |

**스킬 기본안에서 버린 것:** Claymorphism(어린이·장난감 느낌), Varela Round/Nunito(한글 미지원), "Product Demo" 랜딩 패턴(단일 대시보드 앱에 불필요), 검정 글자 주 버튼.

---

## 2. 색 토큰

모든 텍스트 조합은 WCAG AA 4.5:1 이상을 계산으로 확인했습니다(괄호 안 대비값).

### 라이트

| 역할 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 배경 | `--bg` | `#F0F9FF` | 페이지 배경 (물빛) |
| 표면 | `--surface` | `#FFFFFF` | 카드, 다이얼로그 |
| 표면 2 | `--surface-2` | `#F5FAFD` | 표 머리글, 입력창 배경 |
| 본문 | `--ink` | `#0F172A` | 기본 글자 (16.8:1) |
| 보조 글자 | `--muted` | `#475569` | 설명, 단위 (7.1:1) |
| 선 | `--line` | `#D6E6F0` | 카드 테두리, 표 구분선 |
| 주 색 | `--brand` | `#0369A1` | 주 버튼, 링크, 선택 탭 (흰 글자 5.9:1) |
| 주 색 위 글자 | `--brand-ink` | `#FFFFFF` | |
| 주 색 옅게 | `--brand-soft` | `#E0F2FE` | 선택된 행, 칩 배경 |
| 레인 청록 | `--accent` | `#06B6D4` | **장식 전용**(레인 줄, 진행 막대). 흰 바탕 글자로 쓰지 않음 (2.4:1) |
| 청록 글자 | `--accent-ink` | `#0E7490` | 청록 계열 텍스트가 필요할 때 (5.4:1) |
| 포커스 링 | `--ring` | `#0369A1` | `outline: 2px solid; outline-offset: 2px` |

### 시기(주기화) 색

| 시기 | 글자 | 배경 | 대비 |
|---|---|---|---|
| 기초 Base | `--base` `#1D4ED8` | `--base-soft` `#E6F0FF` | 5.8:1 |
| 강화 Build | `--build` `#92400E` | `--build-soft` `#FEF3DC` | 6.4:1 |
| 테이퍼 Taper | `--taper` `#047857` | `--taper-soft` `#E2F8EF` | 4.9:1 |

시기는 **색만으로 구분하지 않습니다.** 배지에 항상 "기초/강화/테이퍼" 글자를 함께 씁니다.

### 상태

| 역할 | 토큰 | 값 | 용도 |
|---|---|---|---|
| 경고 글자 / 배경 / 선 | `--warn-ink` / `--warn-bg` / `--warn-line` | `#7A4B00` / `#FFF6E0` / `#F0B429` | 시간 초과 경고(G-01), 통증 안내(G-02) (6.9:1) |
| 오류 | `--danger` | `#B91C1C` | 입력 오류, 실패 토스트 (6.5:1) |
| 성공 | `--taper` 재사용 | `#047857` | 저장 완료 토스트 |

### 다크 (`prefers-color-scheme: dark`)

| 토큰 | 값 | 대비 |
|---|---|---|
| `--bg` / `--surface` / `--surface-2` | `#07131F` / `#0E1E2E` / `#13263A` | |
| `--ink` / `--muted` / `--line` | `#E6EEF6` / `#94A3B8` / `#1F3550` | 16.0:1 / 6.6:1 |
| `--brand` / `--brand-ink` / `--brand-soft` | `#38BDF8` / `#04121F` / `#123049` | 버튼 8.8:1, 표면 위 글자 7.9:1 |
| `--accent` / `--accent-ink` | `#22D3EE` / `#22D3EE` | 9.3:1 |
| `--base` / `--base-soft` | `#93C5FD` / `#16294A` | 8.0:1 |
| `--build` / `--build-soft` | `#FCD34D` / `#3A2A0C` | 9.6:1 |
| `--taper` / `--taper-soft` | `#6EE7B7` / `#0D3326` | 9.1:1 |
| `--warn-ink` / `--warn-bg` / `--warn-line` | `#F8D784` / `#3A2C08` / `#B7861D` | 9.8:1 |
| `--danger` | `#F87171` | 6.1:1 |

---

## 3. 타이포그래피

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
```

```css
--font-body: "Noto Sans KR", system-ui, -apple-system, "Malgun Gothic", sans-serif;
--font-display: "Barlow Condensed", "Noto Sans KR", system-ui, sans-serif; /* 한글은 Noto로 폴백 */
```

로컬 앱이므로 폰트를 못 받아도 `Malgun Gothic`·`system-ui`로 깨지지 않게 폴백을 둡니다.

| 단계 | 크기 / 줄간 | 굵기 | 글꼴 | 예 |
|---|---|---|---|---|
| Display | 40px / 1.1 | 700 | display | D-23, CSS 1:32 |
| H1 | 24px / 1.3 | 700 | body | 화면 제목 |
| H2 | 18px / 1.4 | 700 | body | 카드 제목 "이번 주 세션" |
| Body | 16px / 1.6 | 400 | body | 설명, 채팅 |
| Small | 14px / 1.5 | 500 | body | 단위, 날짜, 표 보조 |
| Number | 상황별 | 600 | display | 세트표 거리·반복·페이스 |

- 숫자가 들어가는 곳(세트표, 기록, D-day, 페이스)은 `font-variant-numeric: tabular-nums;`
- 본문은 12px 미만 금지, 모바일 입력창은 16px 이상(iOS 확대 방지)

---

## 4. 간격·모서리·그림자

| 토큰 | 값 | 용도 |
|---|---|---|
| `--space-1` | 4px | 아이콘-글자 사이 |
| `--space-2` | 8px | 칩 사이, 버튼 내부 세로 |
| `--space-3` | 12px | 표 셀 |
| `--space-4` | 16px | 카드 안쪽, 모바일 좌우 여백 |
| `--space-5` | 24px | 카드 사이, 섹션 사이 |
| `--space-6` | 32px | 데스크톱 페이지 여백 |
| `--radius-sm` / `--radius` / `--radius-lg` | 8px / 12px / 16px | 입력·칩 / 카드 / 다이얼로그·채팅 창 |
| `--shadow` | `0 1px 2px rgba(15,34,54,.06), 0 4px 16px rgba(15,34,54,.06)` | 카드 |
| `--shadow-lg` | `0 12px 32px rgba(15,34,54,.18)` | 다이얼로그, 채팅 창, FAB |

---

## 5. 레이아웃

- **데스크톱(≥1024px):** 2단. 왼쪽 정보 열(대회 D-day·시기 → CSS → 최근 기록), **오른쪽 넓은 열에 수영 프로그램**(주기화 타임라인 → 주차 탭 → 세션 세트표). 열은 `grid-template-columns: minmax(0,1fr) minmax(0,2fr)`.
- **태블릿(768–1023px):** 2단 유지, 왼쪽 열 축소.
- **모바일(<768px):** 1단. 순서는 대회 → 프로그램 → CSS → 기록. 좌우 여백 16px, 가로 스크롤 금지(`min-width:0`). 세트표만 표 내부 가로 스크롤 허용.
- 헤더는 고정하지 않음(콘텐츠 가림 방지). 채팅은 오른쪽 아래 FAB → 오른쪽 서랍(모바일은 전체 화면 시트).
- 확인 해상도: 375 / 768 / 1024 / 1440px.

---

## 6. 컴포넌트

### 버튼
```css
.btn{min-height:44px;padding:10px 18px;border-radius:var(--radius-sm);font:600 15px/1 var(--font-body);
  display:inline-flex;align-items:center;gap:var(--space-2);cursor:pointer;
  transition:background-color .15s ease, box-shadow .15s ease;}
.btn-primary{background:var(--brand);color:var(--brand-ink);border:0;}
.btn-primary:hover{background:color-mix(in srgb,var(--brand) 88%,#000);}
.btn-secondary{background:var(--surface);color:var(--ink);border:1px solid var(--line);}
.btn-secondary:hover{border-color:var(--brand);}
.btn:focus-visible{outline:2px solid var(--ring);outline-offset:2px;}
.btn[disabled]{opacity:.5;cursor:not-allowed;}
```
- 헤더 행동 버튼: **프로그램 생성 = primary**, 훈련 기록·CSS 측정 = secondary. 한 화면에 primary는 1개.
- 비동기 처리(계획 생성 수십 초) 중에는 버튼 비활성 + 스피너 + "계획 만드는 중…" 문구.

### 카드
```css
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:var(--space-4) var(--space-5);box-shadow:var(--shadow);}
```
카드는 클릭 대상이 아니므로 hover 이동 효과를 넣지 않습니다(스킬 기본안의 `translateY` 제거).

### 대회 카드 (D-day)
- `D-23`을 Display 크기 display 글꼴로, 아래에 대회명·종목(예: 자유형 100m)·대회일.
- 현재 시기 배지 + 전체 기간 대비 진행 막대(배경 `--brand-soft`, 채움 `--accent`, 레인 줄 느낌의 4px 높이).

### 시기 배지 / 주기화 타임라인
```css
.phase{display:inline-block;padding:2px 10px;border-radius:999px;font:600 13px/1.6 var(--font-body);}
.phase.base{color:var(--base);background:var(--base-soft);}
.phase.build{color:var(--build);background:var(--build-soft);}
.phase.taper{color:var(--taper);background:var(--taper-soft);}
```
타임라인은 주차를 가로 막대로 이어 붙이고, 현재 주는 `--brand` 2px 테두리 + "이번 주" 라벨.

### 세트표 (핵심)
| 구분 | 세트 | 거리 | 페이스/휴식 | 강도 |
|---|---|---|---|---|
- 머리글 `--surface-2`, 행 구분 `1px solid var(--line)`, 셀 패딩 12px.
- 거리·반복·페이스 열은 display 글꼴 + tabular-nums + 오른쪽 정렬.
- 세션 합계(총 거리, 예상 시간)를 표 아래 한 줄로. 시간 초과 세션은 아래 **경고 배너**.
- 모바일에서는 표를 `overflow-x:auto` 래퍼에 넣음.

### 경고 배너 (G-01 시간 초과 / G-02 통증)
```css
.warn{background:var(--warn-bg);color:var(--warn-ink);border-left:4px solid var(--warn-line);
  border-radius:var(--radius-sm);padding:var(--space-3) var(--space-4);}
```
`role="status"`, 아이콘 + 문장. 색만으로 의미를 전달하지 않음.

### 입력 / 다이얼로그 (프로그램 생성·훈련 기록·CSS 측정)
```css
.field label{display:block;font:500 14px/1.5 var(--font-body);color:var(--ink);margin-bottom:6px;}
.input{width:100%;min-height:44px;padding:10px 12px;font-size:16px;border:1px solid var(--line);
  border-radius:var(--radius-sm);background:var(--surface);color:var(--ink);}
.input:focus{border-color:var(--brand);outline:2px solid color-mix(in srgb,var(--brand) 30%,transparent);}
.field .hint{font-size:14px;color:var(--muted);} .field .error{font-size:14px;color:var(--danger);}
dialog{border:0;border-radius:var(--radius-lg);box-shadow:var(--shadow-lg);width:min(520px,100% - 32px);}
dialog::backdrop{background:rgba(7,19,31,.5);backdrop-filter:blur(3px);}
```
- 라벨은 항상 보이게(placeholder만 쓰지 않음). 오류는 해당 입력 바로 아래.
- 대회일: `min=오늘`. CSS 기록: `m:ss` 입력 + 실시간 미리보기("CSS 1:32/100m").
- RPE 슬라이더: 1–10, 현재 값 숫자를 옆에 크게 표시.
- 닫기: Esc, 바깥 클릭, 닫기 버튼(aria-label="닫기").

### 채팅 서랍
- FAB 56px 원형 `--brand`, `aria-label="코치 채팅 열기"`.
- 서랍 폭 420px(모바일 100%), 사용자 말풍선 `--brand-soft`, 코치 말풍선 `--surface-2`.
- 코치 답변은 안전한 Markdown 렌더(HTML 먼저 escape) — 표·목록 지원.
- 응답 대기 중 "코치가 확인하는 중…" 점 애니메이션(감소된 모션에서는 정적 문구).

### 토스트
- 오른쪽 아래(모바일 하단 중앙), 4초 후 사라짐, `role="status"`(오류는 `role="alert"`).

---

## 7. 아이콘

- **이모지·기호 문자를 아이콘으로 쓰지 않습니다**(＋ ✎ ⏱ 💬 등). SVG 아이콘(Lucide) 하나로 통일, 크기 18–20px, `stroke-width: 2`, `currentColor`.
- 권장 매핑: 프로그램 생성 `plus`, 훈련 기록 `pencil-line`, CSS 측정 `timer`, 채팅 `message-circle`, 대회 `trophy`, 경고 `triangle-alert`, 다음 주 생성 `calendar-plus`, 닫기 `x`.
- 외부 스크립트 없이 쓰려면 필요한 SVG path만 `index.html`에 인라인으로 넣습니다.
- 아이콘만 있는 버튼에는 `aria-label` 필수.

---

## 8. 모션

- 상태 전환 150–200ms `ease-out`, 다이얼로그·서랍 열기 200–250ms. 너비·높이 애니메이션 금지(transform/opacity만).
- `@media (prefers-reduced-motion: reduce)`에서 모든 전환을 0.01ms로.
- 장식용 물결·움직이는 배경은 쓰지 않음(스킬 기본안의 "water wave animation" 제외).

---

## 9. 금지 패턴

- ❌ 이모지·기호를 아이콘으로 사용
- ❌ 시기·경고를 색으로만 구분
- ❌ 흰 바탕 위 청록(`#06B6D4`) 글자 (2.4:1)
- ❌ 클릭 안 되는 카드에 hover 들썩임
- ❌ placeholder만 있는 입력창
- ❌ 고정 헤더가 콘텐츠를 가림
- ❌ 모바일 가로 스크롤(세트표 내부 스크롤만 허용)
- ❌ 포커스 링 제거

---

## 10. 납품 전 점검표

- [ ] 텍스트 대비 4.5:1 이상 (라이트·다크 모두)
- [ ] 모든 클릭 요소 `cursor:pointer`, 최소 44×44px
- [ ] 키보드로 다이얼로그·채팅 열고 닫기 가능, 포커스 링 보임
- [ ] 이모지 아이콘 없음, SVG 아이콘 한 세트
- [ ] 숫자 열 tabular-nums 정렬
- [ ] 시기 배지에 글자 포함
- [ ] `prefers-reduced-motion` 적용
- [ ] 375 / 768 / 1024 / 1440px에서 가로 스크롤 없음
- [ ] 폰트 미로딩 시에도 한글 정상 표시

---

## 부록: 현재 `static/index.html`과의 차이

| 항목 | 현재 | 이 시스템 |
|---|---|---|
| 주 색 | `--brand:#0a7cc4` (흰 글자 4.47:1, AA 근소 미달) | `#0369A1` (5.9:1) |
| 보조 글자 | `--muted:#5b6b7f` (5.1:1) | `#475569` (7.1:1) |
| 글꼴 | 시스템 글꼴 | Noto Sans KR + 숫자는 Barlow Condensed |
| 헤더·FAB 아이콘 | `＋ ✎ ⏱` 기호 문자 | Lucide 인라인 SVG |
| 시기 색 | base/build/taper 있음 | 유지, 글자 색만 대비 기준에 맞게 조정 |
| 레이아웃·다이얼로그·채팅 서랍 | 있음 | 구조 유지, 토큰만 교체 |
