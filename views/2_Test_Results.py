import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import platform
import math
from datetime import datetime, date

st.set_page_config(page_title="검사 결과", page_icon="📊", layout="wide")

CURRENT_PAGE = "test_results"
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


if previous_page == "patient_management" and has_unsaved_new_patient_form():
    render_leave_registration_dialog("검사 결과")

if entered_from_other_page:
    st.session_state.is_input_mode = False
    st.session_state.test_input_step = "general"
    st.session_state.pending_test_mode = "new"
    st.session_state.pending_test_record_idx = None
    st.session_state.show_duplicate_test_dialog = False
    st.session_state.reset_test_form_on_rerun = False
    st.session_state.draft_record = {}

    for key in list(st.session_state.keys()):
        if key.startswith("input_"):
            del st.session_state[key]

p_id = st.session_state.get("selected_patient_id")
p_name = st.session_state.get("selected_patient_name")

if not p_id:
    st.warning("선택된 환자가 없습니다. 좌측 메뉴에서 환자를 먼저 선택해주세요.")
    st.stop()

# ==========================================
# DB 초기화
# ==========================================
if "test_results_db" not in st.session_state:
    st.session_state.test_results_db = pd.DataFrame(columns=[
        "Record_ID", "Patient_ID", "Test_Date", "Age_at_Test",
        "Total_Score_I", "Total_Score_II",
        "J1", "J2", "J3", "J4_1", "J4_2", "J4_3", "J4_sum",
        "J5", "J6", "J7_yes", "J7_no", "J7_sum", "J8",
        "TMT_A", "TMT_B", "Stroop_W", "Stroop_C", "Stroop_CW", "Draft_Impression"
    ])

# ==========================================
# 세션 상태 관리
# ==========================================
def ensure_test_input_state():
    defaults = {
        "is_input_mode": False,
        "test_input_step": "general",
        "pending_test_mode": "new",
        "pending_test_record_idx": None,
        "show_duplicate_test_dialog": False,
        "duplicate_target_step": "save",
        "results_flash_message": "",
        "reset_test_form_on_rerun": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def clear_input_widgets():
    for key in list(st.session_state.keys()):
        if key.startswith("input_"):
            del st.session_state[key]


def full_reset_test_input_state():
    st.session_state.test_input_step = "general"
    st.session_state.pending_test_mode = "new"
    st.session_state.pending_test_record_idx = None
    st.session_state.show_duplicate_test_dialog = False
    clear_input_widgets()


def close_input_mode():
    st.session_state.is_input_mode = False
    full_reset_test_input_state()
    st.session_state.draft_record = {}


def normalize_to_date(value):
    if value is None:
        return datetime.today().date()
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return pd.to_datetime(value).date()
    except Exception:
        return datetime.today().date()


def calc_age_on_date(dob_value, ref_date):
    dob = pd.to_datetime(dob_value, errors="coerce")
    if pd.isna(dob):
        return 0

    dob = dob.date()
    ref_date = normalize_to_date(ref_date)

    return ref_date.year - dob.year - ((ref_date.month, ref_date.day) < (dob.month, dob.day))


def get_effective_test_date():
    if "input_test_date" in st.session_state:
        return normalize_to_date(st.session_state.input_test_date)

    d = st.session_state.get("draft_record", {})
    return normalize_to_date(d.get("Test_Date", datetime.today().date()))


ensure_test_input_state()

if st.session_state.reset_test_form_on_rerun:
    full_reset_test_input_state()
    st.session_state.reset_test_form_on_rerun = False

patient_records = st.session_state.test_results_db[
    st.session_state.test_results_db["Patient_ID"] == p_id
].copy()

# ==========================================
# Draft (초안) 동기화 시스템
# ==========================================
if "draft_record" not in st.session_state:
    st.session_state.draft_record = {}


def init_new_draft():
    st.session_state.draft_record = {
        "Test_Date": datetime.today().date(),
        "J1": 0, "J2": 0, "J3": 0, "J4_1": 0, "J4_2": 0, "J4_3": 0,
        "J5": 0, "J6": 0, "J7_yes": 0, "J7_no": 0, "J8": 0,
        "TMT_A": 0, "TMT_B": 0, "Stroop_W": 0, "Stroop_C": 0, "Stroop_CW": 0
    }
    clear_input_widgets()


def load_draft_from_record(record):
    try:
        t_date = datetime.strptime(record["Test_Date"], "%Y-%m-%d").date()
    except Exception:
        t_date = datetime.today().date()

    def s_int(v):
        return int(v) if pd.notna(v) else 0

    st.session_state.draft_record = {
        "Test_Date": t_date,
        "J1": s_int(record.get("J1")),
        "J2": s_int(record.get("J2")),
        "J3": s_int(record.get("J3")),
        "J4_1": s_int(record.get("J4_1")),
        "J4_2": s_int(record.get("J4_2")),
        "J4_3": s_int(record.get("J4_3")),
        "J5": s_int(record.get("J5")),
        "J6": s_int(record.get("J6")),
        "J7_yes": s_int(record.get("J7_yes")),
        "J7_no": s_int(record.get("J7_no")),
        "J8": s_int(record.get("J8")),
        "TMT_A": s_int(record.get("TMT_A")),
        "TMT_B": s_int(record.get("TMT_B")),
        "Stroop_W": s_int(record.get("Stroop_W")),
        "Stroop_C": s_int(record.get("Stroop_C")),
        "Stroop_CW": s_int(record.get("Stroop_CW")),
    }
    clear_input_widgets()


def sync_widgets_to_draft():
    d = st.session_state.draft_record
    if not d:
        return

    d["Test_Date"] = normalize_to_date(st.session_state.get("input_test_date", d.get("Test_Date")))

    for k in [
        "J1", "J2", "J3", "J4_1", "J4_2", "J4_3",
        "J5", "J6", "J7_yes", "J7_no", "J8",
        "TMT_A", "TMT_B", "Stroop_W", "Stroop_C", "Stroop_CW"
    ]:
        d[k] = st.session_state.get(f"input_{k.lower()}", d.get(k, 0))


def sync_draft_to_widgets():
    d = st.session_state.draft_record
    if not d:
        return

    if "input_test_date" not in st.session_state:
        st.session_state.input_test_date = normalize_to_date(d.get("Test_Date", datetime.today().date()))

    for k in [
        "J1", "J2", "J3", "J4_1", "J4_2", "J4_3",
        "J5", "J6", "J7_yes", "J7_no", "J8",
        "TMT_A", "TMT_B", "Stroop_W", "Stroop_C", "Stroop_CW"
    ]:
        w_key = f"input_{k.lower()}"
        if w_key not in st.session_state:
            st.session_state[w_key] = d.get(k, 0)

# ==========================================
# 데이터베이스 저장 실행 함수
# ==========================================
def execute_save_test_data(p_id, age):
    d = st.session_state.draft_record
    test_date_str = normalize_to_date(d["Test_Date"]).strftime("%Y-%m-%d")

    j4_sum = d["J4_1"] + d["J4_2"] + d["J4_3"]
    j7_sum = max(0, (d["J7_yes"] + d["J7_no"]) - 10)
    tot_i = d["J1"] + d["J2"] + d["J3"] + j4_sum + d["J5"] + d["J6"] + j7_sum
    tot_ii = tot_i + d["J8"]

    payload = {
        "Patient_ID": p_id,
        "Test_Date": test_date_str,
        "Age_at_Test": age,
        "Total_Score_I": tot_i,
        "Total_Score_II": tot_ii,
        "J1": d["J1"],
        "J2": d["J2"],
        "J3": d["J3"],
        "J4_1": d["J4_1"],
        "J4_2": d["J4_2"],
        "J4_3": d["J4_3"],
        "J4_sum": j4_sum,
        "J5": d["J5"],
        "J6": d["J6"],
        "J7_yes": d["J7_yes"],
        "J7_no": d["J7_no"],
        "J7_sum": j7_sum,
        "J8": d["J8"],
        "TMT_A": d["TMT_A"],
        "TMT_B": d["TMT_B"],
        "Stroop_W": d["Stroop_W"],
        "Stroop_C": d["Stroop_C"],
        "Stroop_CW": d["Stroop_CW"],
    }

    if st.session_state.pending_test_mode == "update":
        idx = st.session_state.pending_test_record_idx
        for col, value in payload.items():
            st.session_state.test_results_db.at[idx, col] = value
        st.session_state.results_flash_message = f"✅ {test_date_str} 검사 기록이 수정되었습니다."
    else:
        record_id = f"{p_id}-{test_date_str.replace('-', '')}-{datetime.now().strftime('%H%M%S')}"
        payload["Record_ID"] = record_id
        payload["Draft_Impression"] = ""
        new_record = pd.DataFrame([payload])
        st.session_state.test_results_db = pd.concat(
            [st.session_state.test_results_db, new_record],
            ignore_index=True
        )
        st.session_state.results_flash_message = f"✅ {test_date_str} 신규 검사 기록이 저장되었습니다."

    st.session_state.view_date = test_date_str
    close_input_mode()

# ==========================================
# 날짜 중복 확인 팝업
# ==========================================
@st.dialog("검사 날짜 중복", width="small", dismissible=False)
def duplicate_test_dialog(current_age):
    idx = st.session_state.get("pending_test_record_idx")
    if idx is None:
        st.session_state.show_duplicate_test_dialog = False
        st.rerun()

    existing = st.session_state.test_results_db.loc[idx]
    date_str = normalize_to_date(st.session_state.draft_record["Test_Date"]).strftime("%Y-%m-%d")

    st.warning(f"{date_str} 날짜의 검사 기록이 이미 있습니다.")
    st.write(f"기존 Record ID: **{existing['Record_ID']}**")
    st.write("기존 기록을 업데이트할까요?")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✏️ 업데이트 계속", type="primary", use_container_width=True):
            st.session_state.pending_test_mode = "update"
            st.session_state.show_duplicate_test_dialog = False
            execute_save_test_data(p_id, current_age)
            st.rerun()

    with c2:
        if st.button("↩️ 날짜 다시 선택", use_container_width=True):
            st.session_state.show_duplicate_test_dialog = False
            st.rerun()


# ==========================================
# 탭 스타일
# ==========================================
st.markdown("""
<style>
div[data-baseweb="tab-list"] {
    gap: 0.25rem;
    background-color: #0f172a;
    padding: 0.4rem 0.5rem 0 0.5rem;
    border-radius: 0.6rem 0.6rem 0 0;
    border-bottom: 1px solid #1f2937;
}
button[role="tab"] {
    border-radius: 0.5rem 0.5rem 0 0 !important;
    padding: 0.9rem 1.2rem !important;
    color: #e5e7eb !important;
    font-weight: 700 !important;
    font-size: 1.15rem !important;
    background-color: #111827 !important;
    border: none !important;
}
button[role="tab"][aria-selected="true"] {
    color: #ff4b4b !important;
    background-color: #0b1220 !important;
    border-bottom: 4px solid #ff4b4b !important;
}
div[data-baseweb="tab-panel"] {
    padding-top: 1.2rem;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# [모드 A] 신규/수정 입력 화면
# ==========================================
if st.session_state.is_input_mode:
    sync_draft_to_widgets()

    patient_info = st.session_state.patient_db[
        st.session_state.patient_db["Patient_ID"] == p_id
    ].iloc[0]

    effective_test_date = get_effective_test_date()
    age = calc_age_on_date(patient_info["DOB"], effective_test_date)
    is_age_eligible = age >= 45

    j4_sum = st.session_state.input_j4_1 + st.session_state.input_j4_2 + st.session_state.input_j4_3
    j7_sum = max(0, (st.session_state.input_j7_yes + st.session_state.input_j7_no) - 10)
    total_i = (
        st.session_state.input_j1 + st.session_state.input_j2 + st.session_state.input_j3
        + j4_sum + st.session_state.input_j5 + st.session_state.input_j6 + j7_sum
    )
    total_ii = total_i + st.session_state.input_j8

    save_mode_text = "기존 기록 수정" if st.session_state.pending_test_mode == "update" else "신규 검사 입력"
    st.header(f"📝 CERAD-K {save_mode_text}")
    st.info(
        f"**진행 중인 환자:** {p_name} ({p_id}) | "
        f"**검사 연령:** {age}세"
    )

    if not is_age_eligible:
        st.error(
            f"이 환자는 검사일 {effective_test_date.strftime('%Y-%m-%d')} 기준 만 {age}세입니다. "
            "만 45세 이상만 검사 결과를 입력할 수 있습니다."
        )

    # 검사일 고정 상단
    patient_dob = pd.to_datetime(patient_info["DOB"], errors="coerce")
    min_test_date = patient_dob.date() if pd.notna(patient_dob) else date(1900, 1, 1)
    max_test_date = date.today()

    current_test_date = get_effective_test_date()
    if current_test_date < min_test_date:
        current_test_date = min_test_date
    if current_test_date > max_test_date:
        current_test_date = max_test_date

    d_col1, d_col2, d_col3 = st.columns([1.2, 1.9, 4.3])
    with d_col1:
        st.markdown(
            "<p style='font-size:22px; font-weight:600; margin:8px 0 0 0;'>검사 일자</p>",
            unsafe_allow_html=True
        )
    with d_col2:
        st.date_input(
            "",
            value=current_test_date,
            min_value=min_test_date,
            max_value=max_test_date,
            key="input_test_date",
            label_visibility="collapsed"
        )

    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)

    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.metric("CERAD-K 총점 I (J1~J7)", total_i)
    with s_col2:
        st.metric("CERAD-K 총점 II (I+J8)", total_ii)

    st.markdown("---")

    tab_general, tab_tmt = st.tabs(["✏️ 1. 일반검사", "⏱️ 2. TMT/스트룹"])

    with tab_general:
        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown(
                "<p style='font-size:22px; font-weight:600; margin-top:10px; margin-bottom:8px;'>📋 언어 및 지남력</p>",
                unsafe_allow_html=True
            )
            st.number_input("J1. 언어유창성 (동물 범주)", min_value=0, max_value=50, key="input_j1")
            st.number_input("J2. 보스톤 이름대기 (15점)", min_value=0, max_value=15, key="input_j2")
            st.number_input("J3. 간이 정신상태 검사 (MMSE-KC, 30점)", min_value=0, max_value=30, key="input_j3")

            st.markdown("---")
            st.markdown("**J4. 단어목록기억 (10점 x 3회)**")
            w1, w2, w3 = st.columns(3)
            w1.number_input("1회", min_value=0, max_value=10, key="input_j4_1")
            w2.number_input("2회", min_value=0, max_value=10, key="input_j4_2")
            w3.number_input("3회", min_value=0, max_value=10, key="input_j4_3")
            st.caption(f"💡 J4. 단어목록기억 합계 (30점): {j4_sum} 점")

        with col_right:
            st.markdown(
                "<p style='font-size:22px; font-weight:600; margin-top:10px; margin-bottom:8px;'>📋 구성 및 회상/재인</p>",
                unsafe_allow_html=True
            )
            st.number_input("J5. 구성행동 (11점)", min_value=0, max_value=11, key="input_j5")
            st.number_input("J6. 단어목록회상 (10점)", min_value=0, max_value=10, key="input_j6")
            st.number_input("J8. 구성회상 (11점)", min_value=0, max_value=11, key="input_j8")

            st.markdown("---")
            st.markdown("**J7. 단어목록재인**")
            r_y, r_n = st.columns(2)
            r_y.number_input("예 (Correct)", min_value=0, max_value=10, key="input_j7_yes")
            r_n.number_input("아니오 (Incorrect)", min_value=0, max_value=10, key="input_j7_no")
            st.caption(f"💡 J7. 단어목록재인 합계: {j7_sum} 점 (예+아니오-10)")

    with tab_tmt:
        c_t1, c_t2 = st.columns(2)

        with c_t1:
            st.markdown("##### **[Trail Making Test]**")
            st.number_input(
                "TMT-A 소요시간 (초)",
                min_value=0,
                key="input_tmt_a"
            )
            st.number_input(
                "TMT-B 소요시간 (초)",
                min_value=0,
                key="input_tmt_b"
            )

        with c_t2:
            st.markdown("##### **[Stroop Test]**")
            st.number_input(
                "Stroop-Word (단어읽기)",
                min_value=0,
                key="input_stroop_w"
            )
            st.number_input(
                "Stroop-Color (색상명명)",
                min_value=0,
                key="input_stroop_c"
            )
            st.number_input(
                "Stroop-Color-Word (색단어)",
                min_value=0,
                key="input_stroop_cw"
            )

    st.markdown("---")

    c_cancel, c_space, c_save = st.columns([2.5, 6, 2.5])

    with c_cancel:
        if st.button("❌ 취소 및 닫기", use_container_width=True):
            close_input_mode()
            st.rerun()

    with c_save:
        if st.button("💾 저장 후 닫기", type="primary", use_container_width=True, disabled=not is_age_eligible):
            sync_widgets_to_draft()
            effective_test_date = get_effective_test_date()
            current_age = calc_age_on_date(patient_info["DOB"], effective_test_date)

            if current_age < 45:
                st.error(
                    f"검사일 {effective_test_date.strftime('%Y-%m-%d')} 기준 만 {current_age}세입니다. "
                    "만 45세 이상만 저장할 수 있습니다."
                )
            else:
                test_date_str = st.session_state.draft_record["Test_Date"].strftime("%Y-%m-%d")
                dup_df = patient_records[patient_records["Test_Date"] == test_date_str]

                if not dup_df.empty and st.session_state.pending_test_mode != "update":
                    st.session_state.pending_test_record_idx = dup_df.index[0]
                    st.session_state.duplicate_target_step = "save"
                    st.session_state.show_duplicate_test_dialog = True
                    st.rerun()
                else:
                    execute_save_test_data(p_id, current_age)
                    st.rerun()

    if st.session_state.get("show_duplicate_test_dialog", False):
        duplicate_test_dialog(age)

# ==========================================
# [모드 B] 검사 결과 조회 화면
# ==========================================
else:
    st.header(f"📊 {p_name} : 인지기능 검사 결과")

    if st.session_state.get("results_flash_message"):
        st.success(st.session_state.results_flash_message)
        st.session_state.results_flash_message = ""

    if patient_records.empty:
        st.info("이 환자의 저장된 검사 기록이 없습니다.")
        if st.button("🚀 신규 검사 시작", type="primary"):
            init_new_draft()
            st.session_state.is_input_mode = True
            st.session_state.pending_test_mode = "new"
            st.rerun()
        st.stop()

    patient_records = patient_records.sort_values(by="Test_Date", ascending=False)
    record_dates = patient_records["Test_Date"].tolist()

    if "view_date" not in st.session_state or st.session_state.view_date not in record_dates:
        st.session_state.view_date = record_dates[0]

    selected_record = patient_records[patient_records["Test_Date"] == st.session_state.view_date].iloc[0]
    record_idx = patient_records.index[
        patient_records["Test_Date"] == st.session_state.view_date
    ].tolist()[0]
    patient_info = st.session_state.patient_db[
        st.session_state.patient_db["Patient_ID"] == p_id
    ].iloc[0]

    st.info(
        f"**성별:** {patient_info['Gender']}   |   "
        f"**검사 연령:** {selected_record['Age_at_Test']}세   |  "
        f"**교육 연수:** {patient_info['Edu_Years']}년"
    )
    st.markdown("---")

    top_left, top_mid, top_right, _ = st.columns([2.5, 2.2, 2.2, 3.1])

    with top_left:
        selected_date = st.selectbox(
            "검사 목록",
            options=record_dates,
            index=record_dates.index(st.session_state.view_date),
            label_visibility="collapsed"
        )

    with top_mid:
        if st.button("✏️ 현재 검사 수정", use_container_width=True):
            load_draft_from_record(selected_record)
            st.session_state.is_input_mode = True
            st.session_state.pending_test_mode = "update"
            st.session_state.pending_test_record_idx = record_idx
            st.rerun()

    with top_right:
        if st.button("➕ 신규 검사 추가", type="primary", use_container_width=True):
            init_new_draft()
            st.session_state.is_input_mode = True
            st.session_state.pending_test_mode = "new"
            st.rerun()

    if selected_date != st.session_state.view_date:
        st.session_state.view_date = selected_date
        st.rerun()

    st.caption(f"검사 일자: {st.session_state.view_date} | Record ID: {selected_record['Record_ID']}")
    st.markdown("<br>", unsafe_allow_html=True)

    col_table, col_graph = st.columns([1, 1.2])

    with col_table:
        st.subheader("📋 세부 검사 결과")

        mock_z_scores = pd.DataFrame({
            "검사 항목": [
                "CERAD-K 총점I", "CERAD-K 총점II", "언어유창성", "보스톤 이름대기", "MMSE-KC", "단어목록기억",
                "구성행동", "단어목록회상", "단어목록재인", "구성회상",
                "TMT-A", "TMT-B", "Stroop-Word", "Stroop-Color", "Stroop-Color/Word"
            ],
            "원점수": [
                selected_record.get("Total_Score_I", 0), selected_record.get("Total_Score_II", 0),
                selected_record.get("J1", 0), selected_record.get("J2", 0), selected_record.get("J3", 0),
                selected_record.get("J4_sum", 0), selected_record.get("J5", 0), selected_record.get("J6", 0),
                selected_record.get("J7_sum", 0), selected_record.get("J8", 0),
                selected_record.get("TMT_A", 0), selected_record.get("TMT_B", 0),
                selected_record.get("Stroop_W", 0), selected_record.get("Stroop_C", 0), selected_record.get("Stroop_CW", 0)
            ],
            "Z-Score": [0.0, 0.0, -0.5, -1.2, 0.2, -2.1, 0.5, -1.8, -0.9, -1.5, -1.0, -0.5, 0.1, -0.2, -1.1],
            "판정": ["-", "-", "정상", "경도 저하", "정상", "심한 저하", "정상", "심한 저하", "정상", "경도 저하", "경도 저하", "정상", "정상", "정상", "경도 저하"]
        })

        st.dataframe(mock_z_scores, height=560, use_container_width=True, hide_index=True)

    with col_graph:
        st.subheader("📈 인지기능 프로파일")

        if platform.system() == "Windows":
            plt.rc("font", family="Malgun Gothic")
        elif platform.system() == "Darwin":
            plt.rc("font", family="AppleGothic")

        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(7.0, 7.5))

        label_map = {
            "Stroop-Word": "Stroop-W",
            "Stroop-Color": "Stroop-C",
            "Stroop-Color/Word": "Stroop-CW"
        }
        raw_y_labels = mock_z_scores["검사 항목"][::-1]
        y_labels = [label_map.get(l, l) for l in raw_y_labels]
        x_values = mock_z_scores["Z-Score"][::-1]
        judgments = mock_z_scores["판정"][::-1]

        colors = [
            "#d62728" if j == "심한 저하"
            else "#ff7f0e" if j == "경도 저하"
            else "#4c78a8"
            for j in judgments
        ]

        bars = ax.barh(y_labels, x_values, color=colors, height=0.6)

        for bar in bars:
            w = bar.get_width()
            ax.text(
                w + (0.05 if w >= 0 else -0.05),
                bar.get_y() + bar.get_height() / 2,
                f"{w:.1f}",
                va="center",
                ha="left" if w >= 0 else "right",
                fontweight="bold",
                fontsize=9
            )

        ax.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
        ax.axvline(-1.0, color="orange", linestyle="--", linewidth=1)
        ax.axvline(-1.5, color="red", linestyle=":", linewidth=1)

        z_min, z_max = min(x_values), max(x_values)
        x_min = min(-1.5, math.floor(z_min * 2) / 2)
        x_max = max(1.5, math.ceil(z_max * 2) / 2)

        ax.set_xlim(x_min, x_max)
        ax.set_xticks(np.arange(x_min, x_max + 0.5, 0.5))
        ax.set_xlabel("Z-score")

        plt.grid(axis="x", alpha=0.3)
        plt.tight_layout()

        st.pyplot(fig, use_container_width=True)