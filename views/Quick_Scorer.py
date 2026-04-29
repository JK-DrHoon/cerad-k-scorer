import streamlit as st
import pandas as pd
import os
import math
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# ==========================================
# 폰트 설정: 서버(리눅스) 환경 대응 완결판
# ==========================================
@st.cache_resource
def set_korean_font():
    # 1. 시스템에 설치된 폰트 목록 새로고침 (packages.txt 설치 직후 대응)
    fm.fontManager.addfont('/usr/share/fonts/truetype/nanum/NanumGothic.ttf') # 나눔폰트 경로 직접 추가
    
    # 2. 폰트 이름 설정
    # Streamlit Cloud(리눅스)는 NanumGothic, 윈도우는 Malgun Gothic
    font_names = [f.name for f in fm.fontManager.ttflist]
    
    if 'NanumGothic' in font_names:
        plt.rcParams['font.family'] = 'NanumGothic'
    elif 'Malgun Gothic' in font_names:
        plt.rcParams['font.family'] = 'Malgun Gothic'
    
    plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지

# 폰트 설정 실행
try:
    set_korean_font()
except:
    # 경로를 직접 못 찾을 경우를 대비한 일반적인 설정
    plt.rc('font', family='NanumGothic') 

# ... (이후 load_excel_data 등 기존 함수들은 그대로 두시면 됩니다)

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
        if test_name in ["언어유창성", "보스톤이름대기", "MMSE-KC", "단어목록기억", "구성행동", "단어목록회상", "단어목록재인", "구성회상", "총점 I", "총점 II"]:
            if 50 <= age <= 59: sheet_name = "50-59세_일반검사"
            elif 60 <= age <= 64: sheet_name = "60-64세_일반검사"
            elif 65 <= age <= 69: sheet_name = "65-69세_일반검사"
            elif 70 <= age <= 74: sheet_name = "70-74세_일반검사"
            elif 75 <= age <= 79: sheet_name = "75-79세_일반검사"
            else: sheet_name = "80-90세_일반검사"
            
            df = load_excel_data(sheet_name)
            if df is None: return 0.0
            
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

# ==========================================
# 🖥️ UI 구성
# ==========================================
st.title("⚡ 간편 점수 계산기 (규준표 연동)")
st.info("환자 등록 없이 항목을 입력하여 즉시 Z-Score를 확인하고 프로파일 그래프를 확인합니다.")

c1, c2, c3 = st.columns(3)
with c1: age = st.number_input("나이 (만)", min_value=50, max_value=90, value=72, step=1)
with c2: edu = st.number_input("교육 연수 (년)", min_value=0, max_value=25, value=12, step=1)
with c3: gender = st.selectbox("성별", ["남성", "여성"]) 

st.markdown("---")

tab1, tab2 = st.tabs(["일반 검사 (J1~J8)", "특수 검사 (TMT & Stroop)"])

with tab1:
    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("##### **[언어 및 지남력]**")
        j1 = st.number_input("J1. 언어유창성 (동물)", 0, 50, 15, step=1)
        j2 = st.number_input("J2. 보스톤 이름대기", 0, 15, 12, step=1)
        j3 = st.number_input("J3. MMSE-KC", 0, 30, 25, step=1)
        st.markdown("##### **[J4. 단어목록기억]**")
        w1, w2, w3 = st.columns(3)
        with w1: j4_1 = st.number_input("1회차", 0, 10, 5, step=1)
        with w2: j4_2 = st.number_input("2회차", 0, 10, 6, step=1)
        with w3: j4_3 = st.number_input("3회차", 0, 10, 7, step=1)
        j4_sum = j4_1 + j4_2 + j4_3
    with col_r:
        st.markdown("##### **[구성 및 회상/재인]**")
        j5 = st.number_input("J5. 구성행동", 0, 11, 10, step=1)
        j6 = st.number_input("J6. 단어목록회상", 0, 10, 5, step=1)
        st.markdown("##### **[J7. 단어목록재인]**")
        ry, rn = st.columns(2)
        with ry: j7_yes = st.number_input("예", 0, 10, 9, step=1)
        with rn: j7_no = st.number_input("아니오", 0, 10, 1, step=1)
        j7_sum = max(0, (j7_yes + j7_no) - 10)
        j8 = st.number_input("J8. 구성회상", 0, 11, 7, step=1)

with tab2:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("##### **[Trail Making Test]**")
        tmt_a = st.number_input("TMT-A 소요시간 (초)", 0, 300, 39, step=1)
        tmt_b = st.number_input("TMT-B 소요시간 (초)", 0, 400, 115, step=1)
    with col_t2:
        st.markdown("##### **[Stroop Test]**")
        s_w = st.number_input("Stroop-Word", 0, 150, 64, step=1)
        s_c = st.number_input("Stroop-Color", 0, 150, 51, step=1)
        s_cw = st.number_input("Stroop-Color/Word", 0, 150, 37, step=1)

st.markdown("---")

# ==========================================
# 📊 3. 결과 연산 및 시각화 (Matplotlib 복구)
# ==========================================
if st.button("📊 실제 규준 적용하여 확인하기", type="primary", use_container_width=True):
    # 한글 폰트 설정 (서버 환경 대응)
    font_names = [f.name for f in fm.fontManager.ttflist]
    if 'NanumGothic' in font_names: plt.rcParams['font.family'] = 'NanumGothic'
    elif 'Malgun Gothic' in font_names: plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False

    total_i = j1 + j2 + j4_sum + j5 + j6 + j7_sum
    total_ii = total_i + j8

    def get_status(z):
        if z <= -1.5: return "심한 저하"
        elif z <= -1.0: return "경도 저하"
        else: return "정상"

    results = [
        {"검사 항목": "CERAD-K 총점I", "원점수": total_i, "Z-Score": calc_z_score("총점 I", total_i, age, edu, gender)},
        {"검사 항목": "CERAD-K 총점II", "원점수": total_ii, "Z-Score": calc_z_score("총점 II", total_ii, age, edu, gender)},
        {"검사 항목": "언어유창성", "원점수": j1, "Z-Score": calc_z_score("언어유창성", j1, age, edu, gender)},
        {"검사 항목": "보스톤 이름대기", "원점수": j2, "Z-Score": calc_z_score("보스톤이름대기", j2, age, edu, gender)},
        {"검사 항목": "MMSE-KC", "원점수": j3, "Z-Score": calc_z_score("MMSE-KC", j3, age, edu, gender)},
        {"검사 항목": "단어목록기억", "원점수": j4_sum, "Z-Score": calc_z_score("단어목록기억", j4_sum, age, edu, gender)},
        {"검사 항목": "구성행동", "원점수": j5, "Z-Score": calc_z_score("구성행동", j5, age, edu, gender)},
        {"검사 항목": "단어목록회상", "원점수": j6, "Z-Score": calc_z_score("단어목록회상", j6, age, edu, gender)},
        {"검사 항목": "단어목록재인", "원점수": j7_sum, "Z-Score": calc_z_score("단어목록재인", j7_sum, age, edu, gender)},
        {"검사 항목": "구성회상", "원점수": j8, "Z-Score": calc_z_score("구성회상", j8, age, edu, gender)},
        {"검사 항목": "TMT-A", "원점수": tmt_a, "Z-Score": calc_z_score("TMT_A", tmt_a, age, edu, gender)},
        {"검사 항목": "TMT-B", "원점수": tmt_b, "Z-Score": calc_z_score("TMT_B", tmt_b, age, edu, gender)},
        {"검사 항목": "Stroop-W", "원점수": s_w, "Z-Score": calc_z_score("STR_W", s_w, age, edu, gender)},
        {"검사 항목": "Stroop-C", "원점수": s_c, "Z-Score": calc_z_score("STR_C", s_c, age, edu, gender)},
        {"검사 항목": "Stroop-CW", "원점수": s_cw, "Z-Score": calc_z_score("STR_CW", s_cw, age, edu, gender)}
    ]
    df_res = pd.DataFrame(results)
    df_res["판정"] = df_res["Z-Score"].apply(get_status)

    col1, col2 = st.columns([1.2, 1.8])
    with col1:
        st.subheader("📋 세부 검사 결과")
        st.dataframe(df_res, height=560, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("📈 인지기능 프로파일")
        
        # [수정] figsize의 두 번째 숫자(8 -> 6)를 줄여서 높이를 낮췄습니다.
        fig, ax = plt.subplots(figsize=(7, 6)) 
        
        plot_df = df_res.iloc[::-1] # 데이터 역순
        
        colors = ["#d62728" if s == "심한 저하" else "#ff7f0e" if s == "경도 저하" else "#4c78a8" for s in plot_df["판정"]]
        
        # [수정] 막대 두께(height)를 0.7로 살짝 키워 더 꽉 차 보이게 조절했습니다.
        bars = ax.barh(plot_df["검사 항목"], plot_df["Z-Score"], color=colors, height=0.7, edgecolor='gray', linewidth=0.5)
        
        # 유동적 범위 및 눈금 설정 (0.5 단위)
        z_min, z_max = plot_df["Z-Score"].min(), plot_df["Z-Score"].max()
        v_min = min(-1.5, math.floor((z_min - 0.4) * 2) / 2) # 여유분 확보
        v_max = max(1.0, math.ceil((z_max + 0.4) * 2) / 2)
        ax.set_xlim(v_min, v_max)
        ax.set_xticks(np.arange(v_min, v_max + 0.1, 0.5))

        # 기준선
        ax.axvline(0, color='black', linewidth=1)
        ax.axvline(-1.0, color='orange', linestyle='--', linewidth=1)
        ax.axvline(-1.5, color='red', linestyle=':', linewidth=1)
        
        # 숫자 표시 (짤림 방지를 위해 여백 정교화)
        for bar in bars:
            w = bar.get_width()
            ax.text(w + (0.05 if w >= 0 else -0.05), 
                    bar.get_y() + bar.get_height()/2, 
                    f'{w:.2f}', 
                    va='center', 
                    ha='left' if w >= 0 else 'right', 
                    fontsize=9, fontweight='bold')

        # [수정] 불필요한 위/오른쪽 테두리 제거 및 폰트 크기 조정
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(axis='y', labelsize=10) # 항목 글자 크기
        ax.grid(axis='x', linestyle='-', alpha=0.3)
        
        # [수정] 여백 자동 조절 (꽉 차게)
        plt.tight_layout()
        
        st.pyplot(fig)