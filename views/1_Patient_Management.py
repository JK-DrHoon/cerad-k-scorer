import streamlit as st
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="환자 관리 및 검색", page_icon="👥", layout="wide")

CURRENT_PAGE = "patient_management"
previous_page = st.session_state.get("_current_page")
entered_from_other_page = previous_page != CURRENT_PAGE
st.session_state["_current_page"] = CURRENT_PAGE

# ==========================================
# 세션 상태 초기화
# ==========================================
if 'management_mode' not in st.session_state:
    st.session_state.management_mode = "search"

if 'pending_new_patient' not in st.session_state:
    st.session_state.pending_new_patient = None

if 'show_patient_confirm_dialog' not in st.session_state:
    st.session_state.show_patient_confirm_dialog = False

if 'show_age_warning_dialog' not in st.session_state:
    st.session_state.show_age_warning_dialog = False

if 'patient_search_query' not in st.session_state:
    st.session_state.patient_search_query = ""

if 'newly_registered_patient_label' not in st.session_state:
    st.session_state.newly_registered_patient_label = ""

if 'is_input_mode' not in st.session_state:
    st.session_state.is_input_mode = False

if 'is_editing_report' not in st.session_state:
    st.session_state.is_editing_report = False


def clear_new_patient_form(reset_mode=False):
    st.session_state.pending_new_patient = None
    st.session_state.show_patient_confirm_dialog = False
    st.session_state.show_age_warning_dialog = False

    for key in ["pm_new_name", "pm_new_dob", "pm_new_gender", "pm_new_edu"]:
        if key in st.session_state:
            del st.session_state[key]

    if reset_mode:
        st.session_state.management_mode = "search"


def has_unsaved_new_patient_form():
    return (
        st.session_state.get("management_mode") == "register" and (
            bool(str(st.session_state.get("pm_new_name", "")).strip())
            or st.session_state.get("pm_new_dob") is not None
            or st.session_state.get("pm_new_gender", "선택") != "선택"
            or st.session_state.get("pm_new_edu") is not None
            or st.session_state.get("pending_new_patient") is not None
            or st.session_state.get("show_patient_confirm_dialog", False)
            or st.session_state.get("show_age_warning_dialog", False)
        )
    )


if entered_from_other_page:
    # 상위 사이드바 메뉴로 다시 들어오면 항상 기본 검색 화면부터 시작
    st.session_state.management_mode = "search"
    st.session_state.patient_search_query = ""
    st.session_state.newly_registered_patient_label = ""
    clear_new_patient_form(reset_mode=False)


def reset_patient_workflow_state():
    """환자를 새로 선택할 때 결과/소견서 페이지의 하위 상태를 초기화."""
    st.session_state.is_input_mode = False
    st.session_state.is_editing_report = False
    st.session_state.test_input_step = "general"
    st.session_state.pending_test_mode = "new"
    st.session_state.pending_test_record_idx = None
    st.session_state.show_duplicate_test_dialog = False
    st.session_state.preload_tmt_from_record_idx = None
    st.session_state.reset_test_form_on_rerun = False
    st.session_state.draft_record = {}

    for key in ['view_date', 'report_view_date']:
        if key in st.session_state:
            del st.session_state[key]

    for key in list(st.session_state.keys()):
        if key.startswith("input_"):
            del st.session_state[key]


def calc_age_today(dob_value):
    dob = pd.to_datetime(dob_value, errors="coerce")
    if pd.isna(dob):
        return 0

    dob = dob.date()
    today = datetime.today().date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


# ==========================================
# 45세 이하 경고 팝업
# ==========================================
@st.dialog("연령 확인", width="small", dismissible=False)
def age_warning_dialog():
    pending = st.session_state.get("pending_new_patient")

    if not pending:
        st.session_state.show_age_warning_dialog = False
        st.rerun()

    age = calc_age_today(pending["DOB"])

    st.warning(f"이 환자는 현재 날짜 기준 만 {age}세입니다.")
    st.markdown("**만 45세 이하 환자입니다.**")
    st.caption("그래도 이 환자 정보를 그대로 저장하시겠습니까?")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("✅ 그래도 저장 진행", type="primary", use_container_width=True):
            st.session_state.show_age_warning_dialog = False
            st.session_state.show_patient_confirm_dialog = True
            st.rerun()

    with c2:
        if st.button("↩️ 다시 수정하기", use_container_width=True):
            st.session_state.show_age_warning_dialog = False
            st.rerun()


# ==========================================
# 신규 환자 등록 확인 팝업
# ==========================================
@st.dialog("신규 환자 등록 확인", width="small", dismissible=False)
def confirm_new_patient_dialog():
    pending = st.session_state.get("pending_new_patient")

    if not pending:
        st.rerun()

    dob = datetime.strptime(pending['DOB'], "%Y-%m-%d").date()
    today = datetime.today().date()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    st.write("아래 정보로 신규 환자를 등록하시겠습니까?")
    st.markdown(f"**성명:** {pending['Name']}")
    st.markdown(f"**생년월일:** {pending['DOB']} **(현재 만 {age}세)**")
    st.markdown(f"**성별:** {pending['Gender']}")
    st.markdown(f"**교육연수:** {pending['Edu_Years']}년")
    st.caption("검사 연령은 실제 검사 결과 입력 시, 검사일 기준으로 별도로 계산됩니다.")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("✅ 등록", type="primary", use_container_width=True):
            current_ids = st.session_state.patient_db['Patient_ID'].tolist()
            if current_ids:
                valid_ids = []
                for id_str in current_ids:
                    id_str = str(id_str)
                    if id_str.startswith("A"):
                        try:
                            valid_ids.append(int(id_str[1:]))
                        except ValueError:
                            pass
                max_id_num = max(valid_ids) if valid_ids else 0
                new_id = f"A{max_id_num + 1:03d}"
            else:
                new_id = "A001"

            new_data = pd.DataFrame({
                'Patient_ID': [new_id],
                'Name': [pending["Name"]],
                'Gender': [pending["Gender"]],
                'DOB': [pending["DOB"]],
                'Edu_Years': [pending["Edu_Years"]],
                'Status': ['Active']
            })

            st.session_state.patient_db = pd.concat(
                [st.session_state.patient_db, new_data],
                ignore_index=True
            )

            clear_new_patient_form(reset_mode=False)
            st.session_state.management_mode = "search"
            st.session_state.patient_search_query = new_id
            st.session_state.newly_registered_patient_label = f"{new_id} - {pending['Name']}"
            st.rerun()

    with c2:
        if st.button("❌ 취소", use_container_width=True):
            st.session_state.pending_new_patient = None
            st.session_state.show_patient_confirm_dialog = False
            st.session_state.show_age_warning_dialog = False
            st.rerun()


# ==========================================
# 화면
# ==========================================
st.title("👥 환자 관리 및 검색")

col_tab1, col_tab2, _ = st.columns([2, 2, 6])
with col_tab1:
    if st.button(
        "🔍 환자 검색 및 선택",
        type="primary" if st.session_state.management_mode == "search" else "secondary",
        use_container_width=True
    ):
        st.session_state.management_mode = "search"
        st.rerun()

with col_tab2:
    if st.button(
        "➕ 신규 환자 등록",
        type="primary" if st.session_state.management_mode == "register" else "secondary",
        use_container_width=True
    ):
        st.session_state.management_mode = "register"
        st.rerun()

st.markdown("---")

# ==========================================
# [모드 A] 환자 검색 및 선택
# ==========================================
if st.session_state.management_mode == "search":
    st.subheader("등록된 환자 목록")

    search_query = st.text_input(
        "🔍 이름 또는 환자번호로 검색 (예: 홍길동, A001)",
        value=st.session_state.get("patient_search_query", "")
    )
    st.session_state.patient_search_query = search_query
    df = st.session_state.patient_db.copy()

    if search_query:
        filtered_df = df[
            df['Name'].astype(str).str.contains(search_query, case=False, na=False) |
            df['Patient_ID'].astype(str).str.contains(search_query, case=False, na=False)
        ]
    else:
        filtered_df = df

    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    st.markdown("#### 🎯 환자 선택 후 작업 진행")

    patient_options = list(filtered_df['Patient_ID'].astype(str) + " - " + filtered_df['Name'].astype(str))
    select_options = ["선택 안 함"] + patient_options

    default_index = 0
    highlight_label = st.session_state.get("newly_registered_patient_label", "")
    if highlight_label and highlight_label in select_options:
        default_index = select_options.index(highlight_label)
        st.success(f"신규 환자 등록 완료: {highlight_label}")

    col1, col2 = st.columns([3, 1])
    with col1:
        selected_option = st.selectbox("작업할 환자를 선택하세요:", select_options, index=default_index)

    with col2:
        st.write("")
        st.write("")
        if selected_option != "선택 안 함":
            selected_id = selected_option.split(" - ")[0]
            selected_name = selected_option.split(" - ", 1)[1]

            if st.button("✅ 이 환자로 선택완료", type="primary", use_container_width=True):
                reset_patient_workflow_state()
                st.session_state.selected_patient_id = selected_id
                st.session_state.selected_patient_name = selected_name
                st.session_state.newly_registered_patient_label = ""
                st.session_state.redirect_to_results = True
                st.rerun()

# ==========================================
# [모드 B] 신규 환자 등록
# ==========================================
else:
    st.subheader("신규 환자 정보 입력")
    st.caption("입력 도중 다른 메뉴로 이동하면, 저장되지 않은 내용에 대해 한 번 더 확인해 드립니다.")

    dob_min_date = date(1900, 1, 1)
    dob_max_date = date.today()
    default_dob = (pd.Timestamp.today() - pd.DateOffset(years=50)).date()

    with st.form("new_patient_form"):
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            new_name = st.text_input("성명 *", placeholder="이름을 입력하세요", key="pm_new_name")
            new_dob = st.date_input(
                "생년월일 *",
                value=default_dob,
                min_value=dob_min_date,
                max_value=dob_max_date,
                key="pm_new_dob"
            )

        with col_f2:
            new_gender = st.selectbox("성별 *", ["선택", "M", "F"], key="pm_new_gender")
            new_edu = st.number_input(
                "교육연수 (년) *",
                min_value=0,
                max_value=30,
                value=None,
                placeholder="예: 12",
                key="pm_new_edu"
            )

        submitted = st.form_submit_button("📝 신규 환자 등록")

    if submitted:
        if not new_name.strip() or new_dob is None or new_gender == "선택" or new_edu is None:
            st.error("이름, 생년월일, 성별, 교육연수를 모두 입력해주세요.")
        else:
            st.session_state.pending_new_patient = {
                "Name": new_name.strip(),
                "DOB": new_dob.strftime("%Y-%m-%d"),
                "Gender": new_gender,
                "Edu_Years": int(new_edu)
            }

            current_age = calc_age_today(new_dob)
            if current_age <= 45:
                st.session_state.show_age_warning_dialog = True
                st.session_state.show_patient_confirm_dialog = False
            else:
                st.session_state.show_age_warning_dialog = False
                st.session_state.show_patient_confirm_dialog = True

            st.rerun()

if st.session_state.get("show_age_warning_dialog", False) and st.session_state.get("pending_new_patient"):
    age_warning_dialog()

if st.session_state.get("show_patient_confirm_dialog", False) and st.session_state.get("pending_new_patient"):
    confirm_new_patient_dialog()