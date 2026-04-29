import streamlit as st
import pandas as pd

st.set_page_config(page_title="소견서 관리", page_icon="📝", layout="wide")

CURRENT_PAGE = "report"
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
    render_leave_registration_dialog("소견서")

if entered_from_other_page:
    # 다른 페이지 갔다가 다시 들어오면 수정 모드가 아니라 조회 모드부터 시작
    st.session_state.is_editing_report = False

p_id = st.session_state.get('selected_patient_id')
p_name = st.session_state.get('selected_patient_name')

if not p_id:
    st.warning("선택된 환자가 없습니다. 좌측 메뉴에서 환자를 먼저 선택해주세요.")
    st.stop()

if 'test_results_db' not in st.session_state or st.session_state.test_results_db.empty:
    st.info("아직 이 환자의 검사 기록이 없습니다. [📊 검사 결과] 메뉴에서 신규 검사를 먼저 진행해 주세요.")
    st.stop()

patient_records = st.session_state.test_results_db[
    st.session_state.test_results_db['Patient_ID'] == p_id
].copy()

if patient_records.empty:
    st.info("이 환자의 저장된 검사 결과가 없습니다.")
    st.stop()

patient_records = patient_records.sort_values(by='Test_Date', ascending=False)
record_dates = patient_records['Test_Date'].tolist()

if 'report_view_date' not in st.session_state or st.session_state.report_view_date not in record_dates:
    st.session_state.report_view_date = record_dates[0]

if 'is_editing_report' not in st.session_state:
    st.session_state.is_editing_report = False

st.header(f"✍️ {p_name} 환자 소견서 관리")
st.markdown("---")

col_sel, _ = st.columns([2, 8])
with col_sel:
    selected_date = st.selectbox(
        "검사 목록",
        options=record_dates,
        index=record_dates.index(st.session_state.report_view_date),
        label_visibility="collapsed"
    )

if selected_date != st.session_state.report_view_date:
    st.session_state.report_view_date = selected_date
    st.session_state.is_editing_report = False
    st.rerun()

selected_record = patient_records[
    patient_records['Test_Date'] == st.session_state.report_view_date
].iloc[0]
db_idx = patient_records.index[
    patient_records['Test_Date'] == st.session_state.report_view_date
].tolist()[0]
existing_draft = selected_record.get('Draft_Impression', "")

if pd.isna(existing_draft):
    existing_draft = ""
else:
    existing_draft = str(existing_draft).strip()

if not existing_draft or st.session_state.is_editing_report:
    st.subheader(f"✏️ {st.session_state.report_view_date} 소견서 작성/수정")

    if not existing_draft:
        auto_draft = f"{p_name} 환자님의 {st.session_state.report_view_date} 신경심리검사 결과입니다.\n특이사항을 기록해 주세요."
    else:
        auto_draft = existing_draft

    final_impression = st.text_area("소견서 내용을 작성해 주세요.", value=auto_draft, height=250)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 저장하기", type="primary", use_container_width=True):
            st.session_state.test_results_db.at[db_idx, 'Draft_Impression'] = final_impression
            st.session_state.is_editing_report = False
            st.success("소견서가 저장되었습니다!")
            st.rerun()

    with c2:
        if existing_draft and st.button("❌ 수정 취소", use_container_width=True):
            st.session_state.is_editing_report = False
            st.rerun()

else:
    st.subheader(f"📄 {st.session_state.report_view_date} 소견서 조회")
    st.info(existing_draft)

    st.markdown("<br>", unsafe_allow_html=True)
    c_btn1, c_btn2, c_btn3 = st.columns(3)

    with c_btn1:
        if st.button("✏️ 수정하기", type="primary", use_container_width=True):
            st.session_state.is_editing_report = True
            st.rerun()

    with c_btn2:
        if st.button("🗑️ 삭제하기", use_container_width=True):
            st.session_state.test_results_db.at[db_idx, 'Draft_Impression'] = ""
            st.success("소견서가 삭제되었습니다.")
            st.rerun()

    with c_btn3:
        st.download_button(
            label="📥 다운로드",
            data=existing_draft,
            file_name=f"{p_name}_소견서_{st.session_state.report_view_date}.txt",
            mime="text/plain",
            use_container_width=True
        )
