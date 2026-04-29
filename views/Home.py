import streamlit as st
import pandas as pd
from datetime import datetime

CURRENT_PAGE = "home"
previous_page = st.session_state.get("_current_page")
entered_from_other_page = previous_page != CURRENT_PAGE
st.session_state["_current_page"] = CURRENT_PAGE


def has_unsaved_new_patient_form():
    return (
        st.session_state.get("management_mode") == "register" and (
            bool(str(st.session_state.get("pm_new_name", "")).strip())
            or st.session_state.get("pm_new_dob") is not None
            or st.session_state.get("pm_new_gender", "선택") != "선택"
            or st.session_state.get("pm_new_edu") is not None
            or st.session_state.get("pending_new_patient") is not None
            or st.session_state.get("show_patient_confirm_dialog", False)
        )
    )


def clear_new_patient_form_state():
    st.session_state.pending_new_patient = None
    st.session_state.show_patient_confirm_dialog = False
    st.session_state.management_mode = "search"
    for key in ["pm_new_name", "pm_new_dob", "pm_new_gender", "pm_new_edu"]:
        if key in st.session_state:
            del st.session_state[key]


def render_leave_registration_dialog(destination_label: str):
    @st.dialog("입력 중인 환자 정보가 있습니다", width="small", dismissible=False)
    def _dialog():
        st.markdown(
            """
            **신규 환자 등록 화면에 아직 저장되지 않은 입력이 남아 있습니다.**  
            지금 이동을 계속하면 입력 내용은 초기화됩니다.
            """
        )
        st.caption("계속 입력을 이어서 진행하시겠습니까, 아니면 현재 페이지로 이동하시겠습니까?")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("↩️ 계속 입력하기", type="primary", use_container_width=True):
                st.switch_page("views/1_Patient_Management.py")
        with c2:
            if st.button(f"🗂️ 입력 취소 후 {destination_label}로 이동", use_container_width=True):
                clear_new_patient_form_state()
                st.rerun()

    _dialog()


# 1. 페이지 기본 설정
st.set_page_config(page_title="CERAD-K Auto Scorer", page_icon="🧠", layout="wide")

# 2. 전역 세션 상태(Session State) 초기화
# 앱 전체에서 공유할 환자 정보를 담는 그릇입니다.
if 'selected_patient_id' not in st.session_state:
    st.session_state.selected_patient_id = None
if 'selected_patient_name' not in st.session_state:
    st.session_state.selected_patient_name = None
if 'selected_patient_info' not in st.session_state:
    st.session_state.selected_patient_info = "" # 나이/성별/교육연수 등 문자열 저장용

if previous_page == "patient_management" and has_unsaved_new_patient_form():
    render_leave_registration_dialog("메인 대시보드")

# 3. UI 구성: 헤더
st.title("🧠 CERAD-K 통합 인지기능 검사 관리 시스템")
st.markdown("---")

# 4. 상단(Stats): 현황판 (DB 연동 전 임시 데이터)
st.subheader("📊 시스템 현황")
col1, col2, col3 = st.columns(3)

with col1:
    # 델타값(증감)을 활용해 UI를 시각적으로 풍성하게 만듭니다.
    st.metric(label="총 등록 환자 수", value="142 명", delta="이번 주 +3명")
with col2:
    st.metric(label="금월 검사 건수", value="28 건", delta="전월 대비 +5건")
with col3:
    st.metric(label="미완료 소견서 (Draft)", value="2 건", delta="-1건 (처리됨)", delta_color="inverse")

st.markdown("<br>", unsafe_allow_html=True)

# 5. 중앙(Recent Activities): 최근 검사 완료 리스트
st.subheader("📋 최근 검사 완료 리스트 (최신순)")

# 임시 데이터프레임 (추후 Supabase DB에서 SELECT * FROM Test_Results ORDER BY date DESC LIMIT 10)
recent_data = pd.DataFrame({
    '검사 일자': ['2026-04-09', '2026-04-08', '2026-04-07', '2026-04-05'],
    '환자 번호': ['A041', 'A023', 'A035', 'A012'],
    '성명': ['김철수', '이영희', '박지민', '최동훈'],
    '상태': ['완료', '완료', '소견서 미완료', '완료']
})

# Streamlit의 dataframe 기능을 이용해 깔끔하게 표출
st.dataframe(recent_data, use_container_width=True, hide_index=True)

st.markdown("---")

# 6. 하단: 네비게이션 가이드
st.info("""
**💡 빠른 작업 가이드**
* 새로운 환자를 등록하거나 검색하려면 좌측 메뉴의 **[1. Patient Management]**로 이동하세요.
* 검색된 환자를 통해 신규 검사를 진행하거나 과거 기록을 조회할 수 있습니다.
""")