"""Korean refusals/notices shown to users and the safety rule prompts added to the system prompt."""


DURATION_WARNING = "일부 세션이 입력한 세션 시간을 초과합니다."


EVENT_ERROR = ("지원하지 않는 종목입니다. 거리 + 영법으로 입력하세요 "
               "(예: '200m freestyle', 자유형/배영/평영/접영/개인혼영).")


PAST_DATE_ERROR = "대회일(competition_date)은 오늘 이후의 날짜여야 합니다."


SECRET_REFUSAL = ("시스템 프롬프트, 설정 파일, 환경 변수, 자격 증명(키)은 공유할 수 없습니다. "
                  "대신 영법, 드릴, 훈련 계획에 대해 도와드릴게요.")


OFF_TOPIC_REFUSAL = ("죄송합니다. 저는 수영(영법, 기술, 드릴, 훈련 계획)에 대해서만 도와드릴 수 있습니다. "
                     "수영 훈련에 관해 질문해 주세요.")


PLAN_EDIT_REFUSAL = ("코칭 대화에서는 세트표(훈련 계획)를 수정할 수 없습니다. 계획은 읽기 전용으로 "
                     "참고만 하며, 다음 주 계획은 '다음 주 생성' 기능을 이용해 주세요.")


MEDICAL_RULES = (
    "\n\n[SAFETY RULES - the user mentions pain or injury] "
    "Advise the user to stop training the affected area now and to see a medical specialist "
    "(doctor or sports-medicine physician). Do NOT name any medication or dosage. "
    "Do NOT diagnose the condition. Do NOT recommend raising training intensity or volume; "
    "if anything, advise reducing it for the affected area. Reply in Korean.")


MEDICAL_NOTICE = "⚠ 안내: 아픈 부위의 훈련은 즉시 중단하고 의료 전문가(전문의)의 진료를 받으세요."


SET_EDIT_NOTICE = "ℹ 안내: 코칭 대화는 세트표를 수정하지 않습니다. 계획은 참고용으로만 사용됩니다."


COUNT_ERROR = "주 훈련 횟수와 세션 시간은 1 이상이어야 합니다. 값을 다시 입력해 주세요."


CSS_ORDER_ERROR = ("200m 기록이 400m 기록보다 빠르지 않습니다. 두 기록이 뒤바뀌지 않았는지 확인하고 "
                   "다시 입력해 주세요. (CSS = (T400 - T200) / 2)")


PLAN_EDIT_RULES = (
    "\n\n[READ-ONLY RULE - the user asked to change the set table] You cannot modify the stored "
    "plan or set tables from chat. Say so in one sentence, then give concrete text-only suggestions "
    "for adjusting the session themselves (e.g. longer rest, fewer reps, lower target RPE/pace), "
    "and tell them to record a training log and use '다음 주 생성' so the next week reflects it. "
    "Never claim you changed the plan. Reply in Korean.")
