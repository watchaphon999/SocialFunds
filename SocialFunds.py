import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. ระบบฐานข้อมูล SQLite ---
conn = sqlite3.connect('sadao_welfare.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            id_card TEXT UNIQUE NOT NULL,
            birth_date TEXT,
            address TEXT,
            phone TEXT,
            beneficiary TEXT,
            join_date TEXT,
            last_payment_date TEXT,
            total_savings INTEGER DEFAULT 0,
            medical_used_this_year INTEGER DEFAULT 0
        )
    ''')
    conn.commit()

init_db()

# --- 2. ตรรกะทางกฎหมายตามระเบียบปี 2568 ---
def calculate_death_benefit(join_date_str):
    join_date = datetime.strptime(join_date_str, '%Y-%m-%d').date()
    days = (date.today() - join_date).days
    years = days / 365
    
    # ตรวจสอบสิทธิขั้นต่ำ 6 เดือน (ข้อ 10.4) [cite: 60]
    if days < 180: return 0 
    
    # คำนวณตามเกณฑ์ข้อ 17.6 [cite: 88-94]
    if days < 365: return 1500
    elif years < 2: return 3000
    elif years < 5: return 6000
    elif years < 8: return 10000
    elif years < 12: return 12000
    elif years < 15: return 20000
    else:
        extra_years = int(years - 15)
        return 20000 + (extra_years * 500)

def check_membership_status(last_payment_date_str):
    last_payment = datetime.strptime(last_payment_date_str, '%Y-%m-%d').date()
    days_overdue = (date.today() - last_payment).days
    # ขาดส่งเกิน 90 วันพ้นสภาพ (ข้อ 7.4) [cite: 47]
    if days_overdue > 90:
        return "พ้นสภาพ (ขาดส่งเกิน 90 วัน)", "🔴"
    return "ปกติ", "🟢"

# --- 3. การออกแบบหน้าจอ UI ---
st.set_page_config(page_title="Sadao Smart Welfare", layout="wide")

st.title("🏛️ ระบบสวัสดิการชุมชนดิจิทัล เทศบาลเมืองสะเดา")
st.subheader("Sadao City Data Platform (3,000+ Members Support)")

menu = st.sidebar.selectbox("เมนูการใช้งาน", [
    "ตรวจสอบสถานะสมาชิก (รายชื่อทั้งหมด)",
    "สมัครสมาชิกใหม่", 
    "Dashboard ส่วนตัว"
])

if menu == "ตรวจสอบสถานะสมาชิก (รายชื่อทั้งหมด)":
    st.header("🔍 รายชื่อสมาชิกและสิทธิสวัสดิการ")
    
    # 1. ดึงข้อมูลทั้งหมดจากฐานข้อมูลมาเป็น DataFrame
    c.execute("SELECT full_name, id_card, join_date, total_savings, last_payment_date, medical_used_this_year FROM members")
    raw_data = c.fetchall()
    df = pd.DataFrame(raw_data, columns=["ชื่อ-นามสกุล", "เลขบัตรประชาชน", "วันที่สมัคร", "เงินสมทบสะสม", "ส่งเงินล่าสุด", "นอน รพ. ไปแล้ว(คืน)"])

    # 2. ช่องค้นหา (กรองข้อมูลจากตาราง)
    search_q = st.text_input("พิมพ์ชื่อ หรือ เลขบัตรประชาชน เพื่อค้นหาด่วน...", placeholder="ค้นหาจากสมาชิก 3,000+ คน")
    if search_q:
        df = df[df['ชื่อ-นามสกุล'].str.contains(search_q) | df['เลขบัตรประชาชน'].str.contains(search_q)]

    st.info("💡 คลิกเลือกที่แถวชื่อสมาชิก เพื่อดูรายละเอียดสิทธิคงเหลือด้านล่าง")

    # 3. แสดงตารางแบบโต้ตอบได้ (ใช้ feature selection)
    # หมายเหตุ: ต้องใช้ Streamlit เวอร์ชั่น 1.35.0 ขึ้นไป
    event = st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="single_row"
    )

    # 4. แสดงรายละเอียดสิทธิเมื่อมีการคลิกเลือกแถว
    if len(event.selection.rows) > 0:
        selected_row_idx = event.selection.rows[0]
        selected_member_id = df.iloc[selected_row_idx]['เลขบัตรประชาชน']
        
        # ดึงข้อมูลดิบมาคำนวณสิทธิ
        c.execute("SELECT * FROM members WHERE id_card=?", (selected_member_id,))
        m = c.fetchone()
        
        st.divider()
        st.subheader(f"✨ สิทธิสวัสดิการคงเหลือของ: {m[1]}")
        
        # คำนวณค่าต่าง ๆ
        status_text, status_icon = check_membership_status(m[8])
        death_ben = calculate_death_benefit(m[7])
        med_rem = 12 - m[10] # ข้อ 17.2 [cite: 80]
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("สถานะสมาชิก", f"{status_icon} {status_text}")
        with c2:
            st.metric("เงินจัดการศพ (หากเสียชีวิตวันนี้)", f"{death_ben:,} บาท")
            st.caption("ตามระยะเวลาที่เป็นสมาชิก")
        with c3:
            st.metric("โควตานอน รพ. คงเหลือ", f"{med_rem} / 12 คืน")
            st.progress(med_rem / 12)
        with c4:
            st.metric("ยอดเงินสมทบสะสม", f"{m[9]:,} บาท")

elif menu == "สมัครสมาชิกใหม่":
    st.header("📝 แบบฟอร์มสมัครสมาชิกใหม่")
    with st.form("reg_form", clear_on_submit=True):
        f_name = st.text_input("ชื่อ-นามสกุล")
        i_card = st.text_input("เลขบัตรประชาชน")
        b_date = st.date_input("วันเกิด")
        addr = st.text_area("ที่อยู่/ที่ทำงานในเขตสะเดา")
        bene = st.text_input("ผู้รับผลประโยชน์")
        submit = st.form_submit_button("บันทึกสมาชิก")
        
        if submit and f_name and i_card:
            try:
                today_s = date.today().strftime('%Y-%m-%d')
                c.execute("INSERT INTO members (full_name, id_card, birth_date, address, beneficiary, join_date, last_payment_date) VALUES (?,?,?,?,?,?,?)",
                          (f_name, i_card, b_date.strftime('%Y-%m-%d'), addr, bene, today_s, today_s))
                conn.commit()
                st.success(f"เพิ่มคุณ {f_name} เข้าสู่ฐานข้อมูลสะเดาแล้วค่ะ!")
            except:
                st.error("เลขบัตรนี้มีในระบบแล้ว")
