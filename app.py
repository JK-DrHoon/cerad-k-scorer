import streamlit as st
import pandas as pd

# ==========================================
# [데이터베이스 초기화]
# ==========================================
if 'patient_db' not in st.session_state:
    st.session_state.patient_db = pd.DataFrame({
        'Patient_ID': ['A001', 'A027', 'A099'],
        'Name': ['홍길동', '김영희', '홍길녀'],
        'Gender': ['M', 'F', 'F'],
        'DOB': ['1950-01-01', '1960-05-15', '1954-03-01'],
        'Edu_Years': [12, 9, 14],
        'Status': ['Active', 'Active', 'Active']
    })

if 'test_results_db' not in st.session_state:
    st.session_state.test_results_db = pd.DataFrame({
        'Record_ID': ['A099-20260409'], 'Patient_ID': ['A099'], 'Test_Date': ['2026-04-09'],
        'Age_at_Test': [72], 'Total_Score_I': [79], 'Total_Score_II': [86],
        'J1': [13], 'J2': [12], 'J3': [26], 'J4_1': [5], 'J4_2': [6], 'J4_3': [7], 'J4_sum': [18],
        'J5': [10], 'J6': [5], 'J7_yes': [9], 'J7_no': [9], 'J7_sum': [8], 'J8': [7],
        'TMT_A': [45], 'TMT_B': [130], 'Stroop_W': [80], 'Stroop_C': [55], 'Stroop_CW': [30],
        'Draft_Impression': ["홍길녀 환자님의 2026-04-09 신경심리검사 결과입니다.\n전반적인 인지기능은 양호하나, 단어목록회상에서 약간의 저하 소견이 관찰됩니다."]
    })

# ==========================================
# [메뉴 세팅]
# ==========================================
page_home = st.Page("views/Home.py", title="메인 대시보드", icon="🏠", default=True)
page_management = st.Page("views/1_Patient_Management.py", title="환자 관리 및 검색", icon="👥")
page_results = st.Page("views/2_Test_Results.py", title="📊 검사 결과", icon="📈")
page_report = st.Page("views/3_Report.py", title="📝 소견서", icon="✍️")

# 신규 추가: 간편 계산기 페이지 등록
page_quick_scorer = st.Page("views/Quick_Scorer.py", title="⚡ 간편 점수 계산기", icon="⚡")

if 'selected_patient_id' not in st.session_state:
    st.session_state.selected_patient_id = None
    st.session_state.selected_patient_name = ""

# 네비게이션 구성 변경
if st.session_state.selected_patient_id is None:
    # 환자가 선택되지 않았을 때: 홈, 환자관리, 그리고 간편 계산기 노출
    pg = st.navigation({
        "메인": [page_home, page_management],
        "도구": [page_quick_scorer] 
    })
else:
    # 환자가 선택되었을 때: 기존 메뉴 + 간편 계산기 노출
    patient_group_label = f"선택된 환자: {st.session_state.selected_patient_id} {st.session_state.selected_patient_name}"
    pg = st.navigation({
        "메인": [page_home, page_management],
        patient_group_label: [page_results, page_report],
        "도구": [page_quick_scorer] # 어느 상황에서든 바로 쓸 수 있게 배치
    })

pg.run()