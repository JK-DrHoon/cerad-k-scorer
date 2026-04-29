import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import math
import platform
import numpy as np

# ==========================================
# 🧠 [엔진] 규준표 데이터 로드 및 Z-Score 연산
# ==========================================
@st.cache_data
def load_excel_data(sheet_name):
    file_path = "CERAD_K_Norm_DB.xlsx"
    if not os.path.exists(file_path):
        return None
    return pd.read_excel(file_path, sheet_name=sheet_name, header=1)

def get_age_group_str(age):
    if 50 <= age <= 59: return "50-59"
    elif 60 <= age <= 69: return "60-69"
    elif 70 <= age <= 74: return "70-74"
    elif 75 <= age <= 79: return "75-79"
    else: return "80-90"

def get_general_edu_cols(edu):
    if edu <= 3: return "0-3 M", "0-3 SD"
    elif 4 <= edu <= 9: return "4-9 M", "4-9 SD"
    elif 10 <= edu <= 12: return "10-12 M", "10-12 SD"
    else: return ">=13 M", ">=13 SD"

def get_tmta_edu_cols(edu):
    if edu <= 3: return "0-3 M", "0-3 SD"
    elif 4 <= edu <= 6: return "4-6 M", "4-6 SD"
    elif 7 <= edu <= 9: return "7-9 M", "7-9 SD"
    else: return ">=10 M", ">=10 SD"

def get_tmtb_edu_cols(edu):
    if edu <= 6: return "0-6 M", "0-6 SD"
    elif 7 <= edu <= 9: return "7-9 M", "7-9 SD"
    else: return ">=10 M", ">=10 SD"

def get_stroop_edu_cols(edu):
    if edu <= 3: return "0-3 M", "0-3 SD"
    elif 4 <= edu <= 9: return "4-9 M", "4-9 SD"
    else: return ">=10 M", ">=10 SD"

def calc_z_score(test_name, raw_score, age, edu, gender):
    try:
        # [일반 검사 및 총점 처리 로직]
        if test_name in ["언어유창성", "보스톤이름대기", "MMSE-KC", "단어목록기억", "구성행동", "단어목록회상", "단어목록재인", "구성회상", "총점 I", "총점 II"]:
            if 50 <= age <= 59: sheet_name = "50-59세_일반검사"
            elif 60 <= age <= 64: sheet_name = "60-64세_일반검사"
            elif 65 <= age <= 69: sheet_name = "65-69세_일반검사"
            elif 70 <= age <= 74: sheet_name = "70-74세_일반검사"
            elif 75 <= age <= 79: sheet_name = "75-79세_일반검사"
            else: sheet_name = "80-90세_일반검사"
            
            df = load_excel_data(sheet_name)
            if df is None: return 0.0
            
            # 총점 검색 로직 추가 (세부항목 컬럼에서 찾음)
            if "총점" in test_name:
                filtered = df[(df['성별'] == gender) & (df['검사항목'] == '총점') & (df['세부항목'] == test_name)]
            else:
                filtered = df[(df['성별'] == gender) & (df['검사항목'].str.contains(test_name, na=False, case=False))]
                
            if filtered.empty: return 0.0
            
            m_col, sd_col = get_general_edu_cols(edu)
            
            mean = filtered[m_col].values[0]
            sd = filtered[sd_col].values[0]
            
            if pd.isna(mean) or pd.isna(sd) or sd == 0: return 0.0
            return round((raw_score - mean) / sd, 2)
            
        # [특수 검사 (TMT, 스트룹) 처리 로직]
        else:
            age_group = get_age_group_str(age)
            reverse = False
            
            if test_name == "TMT_A":
                df = load_excel_data("TMT_A")
                filtered = df[(df['성별'] == gender) & (df['연령대'] == age_group)]
                m_col, sd_col = get_tmta_edu_cols(edu)
                reverse = True
            elif test_name == "TMT_B":
                df = load_excel_data("TMT_B")
                filtered = df[(df['성별'] == '공통') & (df['연령대'] == age_group)]
                m_col, sd_col = get_tmtb_edu_cols(edu)
                reverse = True
            elif test_name in ["STR_W", "STR_C", "STR_CW"]:
                df = load_excel_data("스트룹검사")
                excel_test_name = "Stroop-Word" if test_name == "STR_W" else "Stroop-Color" if test_name == "STR_C" else "Stroop-Color-Word"
                filtered = df[(df['성별'] == gender) & (df['연령대'] == age_group) & (df['검사항목'] == excel_test_name)]
                m_col, sd_col = get_stroop_edu_cols(edu)
                
            if filtered is None or filtered.empty: return 0.0
            
            mean = filtered[m_col].values[0]
            sd = filtered[sd_col].values[0]
            
            if pd.isna(mean) or pd.isna(sd) or sd == 0: return 0.0
            
            z = (raw_score - mean) / sd
            return round(-z if reverse else z, 2)
            
    except Exception as e:
        return 0.0

def get_status_with_name(name, z):
    if "총점" in name: return "-"
    if z <= -1.5: return "심한 저하"
    elif z <= -1.0: return "경도 저하"
    else: return "정상"

# ==========================================
# 🖥️ UI 구성
# ==========================================
st.title("⚡ 간편 점수 계산기 (규준표 연동)")
st.info("환자 등록 없이 항목을 입력하여 즉시 Z-Score를 확인하고 프로파일 그래프를 확인합니다.")

# 1. 환자 기본 정보 입력
st.subheader("👤 1. 환자 기본 정보")
c1, c2, c3 = st.columns(3)
with c1: age = st.number_input("나이 (만)", min_value=50, max_value=90, value=72)
with c2: edu = st.number_input("교육 연수 (년)", min_value=0, max_value=25, value=12)
with c3: gender = st.selectbox("성별", ["남성", "여성"]) 

st.markdown("---")

# 2. 검사 원점수 입력
st.subheader("📝 2. 검사 원점수 입력")
tab1, tab2 = st.tabs(["일반 검사 (J1~J8)", "특수 검사 (TMT & Stroop)"])

with tab1:
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("##### **[언어 및 지남력]**")
        j1 = st.number_input("J1. 언어유창성 (동물)", 0.0, 50.0, 15.0)
        j2 = st.number_input("J2. 보스톤 이름대기", 0.0, 15.0, 12.0)
        j3 = st.number_input("J3. MMSE-KC", 0.0, 30.0, 25.0)
        
        st.markdown("##### **[J4. 단어목록기억]**")
        w1, w2, w3 = st.columns(3)
        with w1: j4_1 = st.number_input("1회차", 0.0, 10.0, 5.0)
        with w2: j4_2 = st.number_input("2회차", 0.0, 10.0, 6.0)
        with w3: j4_3 = st.number_input("3회차", 0.0, 10.0, 7.0)
        j4_sum = j4_1 + j4_2 + j4_3
        st.caption(f"💡 단어목록기억 합계 (30점): {j4_sum}점")

    with col_r:
        st.markdown("##### **[구성 및 회상/재인]**")
        j5 = st.number_input("J5. 구성행동", 0.0, 11.0, 10.0)
        j6 = st.number_input("J6. 단어목록회상", 0.0, 10.0, 5.0)
        
        st.markdown("##### **[J7. 단어목록재인]**")
        r_y, r_n = st.columns(2)
        with r_y: j7_yes = st.number_input("예 (Correct)", 0.0, 10.0, 9.0)
        with r_n: j7_no = st.number_input("아니오 (Incorrect)", 0.0, 10.0, 1.0)
        j7_sum = max(0.0, (j7_yes + j7_no) - 10.0)
        st.caption(f"💡 단어목록재인 점수: {j7_sum}점 (예+아니오-10)")
        
        j8 = st.number_input("J8. 구성회상", 0.0, 11.0, 7.0)

with tab2:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("##### **[Trail Making Test]**")
        tmt_a = st.number_input("TMT-A 소요시간 (초)", 0.0, 300.0, 45.0)
        tmt_b = st.number_input("TMT-B 소요시간 (초)", 0.0, 400.0, 130.0)
    with col_t2:
        st.markdown("##### **[Stroop Test]**")
        s_w = st.number_input("Stroop-Word", 0.0, 150.0, 80.0)
        s_c = st.number_input("Stroop-Color", 0.0, 150.0, 55.0)
        s_cw = st.number_input("Stroop-Color/Word", 0.0, 150.0, 30.0)

st.markdown("---")

# 3. 결과 연산 및 출력
if st.button("📊 실제 규준 적용하여 확인하기", type="primary", use_container_width=True):
    st.success("데이터 연산이 완료되었습니다.")
    st.divider()

    # 1. CERAD-K 총점 계산
    total_i = j1 + j2 + j3 + j4_sum + j5 + j6 + j7_sum
    total_ii = total_i + j8

    # 2. 결과 리스트 (총점도 이제 calc_z_score 로 계산합니다!)
    results = [
        ("CERAD-K 총점I", total_i, calc_z_score("총점 I", total_i, age, edu, gender)),
        ("CERAD-K 총점II", total_ii, calc_z_score("총점 II", total_ii, age, edu, gender)),
        ("언어유창성", j1, calc_z_score("언어유창성", j1, age, edu, gender)),
        ("보스톤 이름대기", j2, calc_z_score("보스톤이름대기", j2, age, edu, gender)),
        ("MMSE-KC", j3, calc_z_score("MMSE-KC", j3, age, edu, gender)),
        ("단어목록기억", j4_sum, calc_z_score("단어목록기억", j4_sum, age, edu, gender)),
        ("구성행동", j5, calc_z_score("구성행동", j5, age, edu, gender)),
        ("단어목록회상", j6, calc_z_score("단어목록회상", j6, age, edu, gender)),
        ("단어목록재인", j7_sum, calc_z_score("단어목록재인", j7_sum, age, edu, gender)),
        ("구성회상", j8, calc_z_score("구성회상", j8, age, edu, gender)),
        ("TMT-A", tmt_a, calc_z_score("TMT_A", tmt_a, age, edu, gender)),
        ("TMT-B", tmt_b, calc_z_score("TMT_B", tmt_b, age, edu, gender)),
        ("Stroop-W", s_w, calc_z_score("STR_W", s_w, age, edu, gender)),
        ("Stroop-C", s_c, calc_z_score("STR_C", s_c, age, edu, gender)),
        ("Stroop-CW", s_cw, calc_z_score("STR_CW", s_cw, age, edu, gender))
    ]

    df_res = pd.DataFrame(results, columns=["검사 항목", "원점수", "Z-Score"])
    df_res["판정"] = df_res.apply(lambda row: get_status_with_name(row["검사 항목"], row["Z-Score"]), axis=1)

    col_res1, col_res2 = st.columns([1.2, 1.8])
    
    with col_res1:
        st.subheader("📋 세부 검사 결과")
        st.dataframe(df_res, height=560, use_container_width=True, hide_index=True)

    with col_res2:
        st.subheader("📈 인지기능 프로파일")
        
        if platform.system() == "Windows": plt.rc("font", family="Malgun Gothic")
        elif platform.system() == "Darwin": plt.rc("font", family="AppleGothic")
        plt.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(7.0, 7.5))
        
        y_labels = df_res["검사 항목"][::-1]
        x_values = df_res["Z-Score"][::-1]
        judgments = df_res["판정"][::-1]

        # 색상 지정 로직 수정: 총점 막대도 보이게! (파란색 기본)
        def get_color(j, name):
             if "총점" in name: return "#4c78a8" # 이제 총점 막대도 정상적으로 보입니다!
             if j == "심한 저하": return "#d62728"
             elif j == "경도 저하": return "#ff7f0e"
             else: return "#4c78a8"
             
        colors = [get_color(j, label) for j, label in zip(judgments, y_labels)]

        bars = ax.barh(y_labels, x_values, color=colors, height=0.6)

        for bar, label in zip(bars, y_labels):
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