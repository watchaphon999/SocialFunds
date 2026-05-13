import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 1. ระบบฐานข้อมูล SQLite (Database Layer) ---
# เจนนี่ตั้งค่าให้สร้างไฟล์ sadao_welfare.db อัตโนมัติเมื่อเริ่มรันโปรแกรม
conn = sqlite3.connect('sadao_welfare.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    """สร้างตารางเก็บข้อมูลสมาชิก หากยังไม่มีตารางนี้"""
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

# เรียกใช้งานฟังก์ชันสร้างฐานข้อมูล
init_db()

# --- 2. ตรรกะทางกฎหมายตามระเบียบปี 2568 (Logic Layer) ---
def calculate_death_benefit(join_date_str):
    """คำนวณเงินจัดการศพตามระเบียบข้อ 17.6"""
    join_date = datetime.strptime(join_date_str, '%Y-%m-%d').date()
    days = (date.today() - join_date).days
    years = days / 365
    if days < 180: return 0
    elif days < 365: return 1500
    elif years < 2: return 3000
    elif years < 5: return 6000
    elif years < 8: return 10000
    elif years < 12: return 12000
    elif years < 15: return 20000
    else:
        return 20000 + (max(0, int(years - 15)) * 500)

def check_membership_status(last_payment_date_str):
    """เช็คสถานะสมาชิกตามระเบียบข้อ 7.4 (ห้ามขาดส่งเกิน 90 วัน)"""
    last_payment = datetime.strptime(last_payment_date_str, '%Y-%m-%d').date()
    days_overdue = (date.today() - last_payment).days
    if days_overdue > 90:
        return "พ้นสภาพ (ขาดส่งเกิน 90 วัน)", "error"
    return "ปกติ", "success"

# --- 3. การออกแบบหน้าจอ (UI Layer) ---
st.set_page_config(page_title="Sadao Smart Welfare", layout="wide")

st.title("🏛️ ระบบสวัสดิการชุมชนดิจิทัล เทศบาลเมืองสะเดา")
st.subheader("Sadao City Data Platform - Local Testing")

menu = st.sidebar.selectbox("เมนูการใช้งาน", [
    "สมัครสมาชิกใหม่", 
    "ตรวจสอบสถานะสมาชิก (ค้นหาจากฐานข้อมูล)",
    "Dashboard ส่วนตัว (ตัวอย่างการดึงข้อมูล)"
])

if menu == "สมัครสมาชิกใหม่":
    st.header("📝 แบบฟอร์มสมัครสมาชิกกองทุน (รายใหม่)")
    st.info("ค่าธรรมเนียมสมัคร 20 บาท เพื่อจัดทำสมุดประจำตัวสมาชิก (ไม่คืนเงินทุกกรณี)")
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("ชื่อ-นามสกุล")
            id_card = st.text_input("เลขบัตรประจำตัวประชาชน")
            birth_date = st.date_input("วัน/เดือน/ปี เกิด", min_value=date(1920, 1, 1))
        with col2:
            address = st.text_area("ที่อยู่ตามทะเบียนบ้าน/สถานที่ประกอบอาชีพในเขตเทศบาล")
            phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
            beneficiary = st.text_input("ชื่อผู้รับผลประโยชน์ (กรณีเสียชีวิต)")
        
        st.write("---")
        agree = st.checkbox("ข้าพเจ้ายินยอมปฏิบัติตามระเบียบข้อบังคับของกองทุนทุกประการ")
        submit_reg = st.form_submit_button("บันทึกลงฐานข้อมูล")
        
        if submit_reg:
            if agree and full_name and id_card:
                try:
                    # บันทึกข้อมูลลง SQLite
                    today_str = date.today().strftime('%Y-%m-%d')
                    c.execute('''
                        INSERT INTO members (full_name, id_card, birth_date, address, phone, beneficiary, join_date, last_payment_date, total_savings)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (full_name, id_card, birth_date.strftime('%Y-%m-%d'), address, phone, beneficiary, today_str, today_str, 0))
                    conn.commit()
                    st.success(f"บันทึกข้อมูลคุณ {full_name} ลงระบบเรียบร้อยแล้วค่ะ!")
                    st.balloons()
                except sqlite3.IntegrityError:
                    st.error("เกิดข้อผิดพลาด: เลขบัตรประชาชนนี้มีในระบบแล้วค่ะ")
            else:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วนและกดยอมรับเงื่อนไขค่ะ")

elif menu == "ตรวจสอบสถานะสมาชิก (ค้นหาจากฐานข้อมูล)":
    st.header("🔍 ระบบสืบค้นข้อมูลสมาชิก (เจ้าหน้าที่)")
    search_query = st.text_input("กรอกชื่อ หรือ เลขบัตรประชาชน เพื่อค้นหา")
    
    if search_query:
        # ค้นหาใน SQLite ด้วยคำสั่ง SQL
        c.execute("SELECT full_name, id_card, join_date, total_savings, last_payment_date FROM members WHERE full_name LIKE ? OR id_card LIKE ?", ('%'+search_query+'%', '%'+search_query+'%'))
        results = c.fetchall()
        
        if results:
            # นำข้อมูลที่ได้มาแสดงผลเป็นตารางสวยๆ
            df = pd.DataFrame(results, columns=["ชื่อ-นามสกุล", "เลขบัตรประชาชน", "วันที่สมัคร", "ยอดเงินออม (บาท)", "ส่งเงินล่าสุด"])
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("ไม่พบข้อมูลในระบบค่ะ ลองตรวจสอบตัวสะกดอีกครั้งนะคะ")

elif menu == "Dashboard ส่วนตัว (ตัวอย่างการดึงข้อมูล)":
    st.header("📊 หน้าตัวอย่าง Dashboard สมาชิก")
    st.write("เลือกสมาชิกจากฐานข้อมูลเพื่อดู Dashboard ของแต่ละคนค่ะ")
    
    c.execute("SELECT id_card, full_name FROM members")
    all_members = c.fetchall()
    
    if all_members:
        member_dict = {f"{m[1]} ({m[0]})": m[0] for m in all_members}
        selected_member = st.selectbox("เลือกสมาชิก", list(member_dict.keys()))
        
        # ดึงข้อมูลรายบุคคลจาก SQLite
        c.execute("SELECT * FROM members WHERE id_card=?", (member_dict[selected_member],))
        m_data = c.fetchone()
        
        status, status_type = check_membership_status(m_data[8])
        death_benefit = calculate_death_benefit(m_data[7])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("สถานะสมาชิก", status)
        with col2: st.metric("ยอดเงินออมรวม", f"{m_data[9]:,} บาท")
        with col3: st.metric("สิทธิจัดการศพปัจจุบัน", f"{death_benefit:,} บาท")
        with col4: st.metric("สิทธิรักษาคงเหลือ", f"{12 - m_data[10]} / 12 คืน")
    else:
        st.info("ยังไม่มีข้อมูลสมาชิกในระบบ ลองไปที่เมนู 'สมัครสมาชิกใหม่' ดูก่อนนะคะ")
