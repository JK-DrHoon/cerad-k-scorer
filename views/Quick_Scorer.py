import streamlit as st
import pandas as pd
import os
import math
import altair as alt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ==========================================
# 폰트 설정: 서버(리눅스) 환경 대응 완결판
# ==========================================
@st.cache_resource
def set_korean_font():
    fm.fontManager.addfont('/usr/share/fonts/truetype/nanum/NanumGothic.ttf') 
    font_names = [f.name for f in fm.fontManager.ttflist]
    
    if 'NanumGothic' in font_names:
        plt.rcParams['font.family'] = 'NanumGothic'
    elif 'Malgun Gothic' in font_names:
        plt.rcParams['font.family'] = 'Malgun Gothic'
    
    plt.rcParams['axes.unicode_minus'] = False 

try:
    set_korean_font()
except:
    plt.rc('font', family='NanumGothic') 

# ==========================================
# 🧠 [엔진] 규준표 데이터 로드 및 연산 로직
# ==========================================
@st.cache_data
def load_excel_data(sheet_name):
    current_dir = os.path.dirname(os.path.abspath(__file__)) 
    parent_dir = os.path.dirname(current_dir) 
    
    candidates = [
        "CERAD_K_Norm_DB.xlsx", 
        os.path.join(current_dir, "CERAD_K_Norm_DB.xlsx"),
        os.path.join(parent_dir, "CERAD_K_Norm_DB.xlsx"),
        "CERAD_K_Norm_DB_2.xlsx", 
        os.path.join(current_dir, "CERAD_K_Norm_DB_2.xlsx")
    ]
    
    file_path = None
    for path in candidates:
        if os.path.exists(path):
            file_path = path
            break
            
    if file_path is None:
        st.error("⚠️ 엑셀 파일을 찾지 못했습니다! 'CERAD_K_Norm_DB.xlsx' 파일이 폴더에 있는지 확인해주세요.")
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
        st.error(f"⚠️ {test_name} 연산 오류: {e}")
        return 0.0

# Z-Score를 백분위수(Percentile)로 변환하는 함수
def z_to_percentile(z):
    try:
        pct = 0.5 * (1 + math.erf(float(z) / math.sqrt(2))) * 100
        return pct
    except:
        return None

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
# 📊 3. 결과 연산 및 시각화
# ==========================================
if st.button("📊 실제 규준 적용하여 확인하기", type="primary", use_container_width=True):
    total_i = j1 + j2 + j4_sum + j5 + j6 + j7_sum
    total_ii = total_i + j8

    def get_status(z):
        if z <= -1.5: return "심한 저하"
        elif z <= -1.0: return "경도 저하"
        else: return "정상"

    tests = [
        ("CERAD-K 총점 I", total_i, "총점 I"), ("CERAD-K 총점 II", total_ii, "총점 II"),
        ("언어유창성", j1, "언어유창성"), ("보스톤 이름대기", j2, "보스톤이름대기"),
        ("MMSE-KC", j3, "MMSE-KC"), ("단어목록기억", j4_sum, "단어목록기억"),
        ("구성행동", j5, "구성행동"), ("단어목록회상", j6, "단어목록회상"),
        ("단어목록재인", j7_sum, "단어목록재인"), ("구성회상", j8, "구성회상"),
        ("TMT-A", tmt_a, "TMT_A"), ("TMT-B", tmt_b, "TMT_B"),
        ("Stroop-Word", s_w, "STR_W"), ("Stroop-Color", s_c, "STR_C"),
        ("Stroop-C/W", s_cw, "STR_CW")
    ]

    results = []
    for kor_name, raw, eng_name in tests:
        # Z-score 계산
        z_val = calc_z_score(eng_name, raw, age, edu, gender)
        
        # 백분위수 계산 후 문자열로 소수점 2자리 고정 포맷팅
        pct_val = z_to_percentile(z_val)
        pct_formatted = f"{pct_val:.2f}" if pct_val is not None else "-"

        results.append({
            "검사 항목": kor_name,
            "원점수": raw,
            "백분위수(%)": pct_formatted, # [수정] 소수점 둘째 자리 고정 적용
            "Z-Score": z_val
        })

    df_res = pd.DataFrame(results)
    df_res["판정"] = df_res["Z-Score"].apply(get_status)

    col1, col2 = st.columns([1.2, 1.8])
    with col1:
        st.subheader("📋 세부 검사 결과")
        st.dataframe(df_res, height=560, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("📈 인지기능 프로파일 (Z-Score)")
        
        sort_order = df_res["검사 항목"].tolist()
        
        z_min = df_res["Z-Score"].min()
        z_max = df_res["Z-Score"].max()
        
        view_min = min(-1.5, math.floor((z_min - 0.3) * 2) / 2)
        view_max = max(1.0, math.ceil((z_max + 0.3) * 2) / 2)
        
        def assign_color(status):
            if status == "심한 저하": return "#d62728"
            elif status == "경도 저하": return "#ff7f0e"
            else: return "#4c78a8"
            
        df_res["색상"] = df_res["판정"].apply(assign_color)

        base = alt.Chart(df_res).encode(
            y=alt.Y('검사 항목:N', sort=sort_order, title="", axis=alt.Axis(labelFontSize=12, labelColor='black'))
        )

        bars = base.mark_bar(size=18).encode(
            x=alt.X('Z-Score:Q', 
                    scale=alt.Scale(domain=[view_min, view_max], nice=False), 
                    title="Z-score",
                    axis=alt.Axis(values=list(np.arange(view_min, view_max + 0.1, 0.5)), labelColor='black', titleColor='black', gridColor='lightgray')),
            color=alt.Color('색상:N', scale=None, legend=None),
            tooltip=[
                alt.Tooltip('검사 항목:N'),
                alt.Tooltip('원점수:Q'),
                alt.Tooltip('백분위수(%):N'), # [수정] 툴팁에도 동일하게 출력
                alt.Tooltip('Z-Score:Q', format='.2f'),
                alt.Tooltip('판정:N')
            ]
        )

        text = base.mark_text(
            align=alt.expr('datum.Z_Score >= 0 ? "left" : "right"'),
            baseline='middle',
            dx=alt.expr('datum.Z_Score >= 0 ? 7 : -7'), 
            fontWeight='bold',
            fontSize=11,
            color='black'
        ).encode(
            x=alt.X('Z-Score:Q'),
            text=alt.Text('Z-Score:Q', format='.2f')
        )

        rule0 = alt.Chart(pd.DataFrame({'z': [0]})).mark_rule(color='black', opacity=0.8).encode(x='z:Q')
        rule1 = alt.Chart(pd.DataFrame({'z': [-1.0]})).mark_rule(color='orange', strokeDash=[5,5]).encode(x='z:Q')
        rule2 = alt.Chart(pd.DataFrame({'z': [-1.5]})).mark_rule(color='red', strokeDash=[2,2]).encode(x='z:Q')

        chart = (bars + text + rule0 + rule1 + rule2).properties(
            height=500,
            background='white'
        ).configure_view(
            stroke='black',
            strokeWidth=1
        )

        st.altair_chart(chart, use_container_width=True)