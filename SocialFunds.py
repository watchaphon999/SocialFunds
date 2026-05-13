import streamlit as st
import pandas as pd
from datetime import datetime, date

# --- 1. ตรรกะทางกฎหมายตามระเบียบปี 2568 ---
def calculate_death_benefit(join_date):
    """คำนวณเงินจัดการศพตามระเบียบข้อ 17.6"""
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

def check_membership_status(last_payment_date):
    """เช็คสถานะสมาชิกตามระเบียบข้อ 7.4 (ห้ามขาดส่งเกิน 90 วัน)"""
    days_overdue = (date.today() - last_payment_date).days
    if days_overdue > 90:
        return "พ้นสภาพ (ขาดส่งเกิน 90 วัน)", "error"
    return "ปกติ", "success"

# --- 2. การออกแบบหน้าจอ (UI Layer) ---
st.set_page_config(page_title="Sadao Smart Welfare", layout="wide")

st.title("🏛️ ระบบสวัสดิการชุมชนดิจิทัล เทศบาลเมืองสะเดา")
st.subheader("Sadao City Data Platform - Smart Life Dashboard")

# เพิ่มเมนู "สมัครสมาชิกใหม่" เข้าไปใน Sidebar
menu = st.sidebar.selectbox("เมนูการใช้งาน", [
    "Dashboard สมาชิก", 
    "สมัครสมาชิกใหม่", 
    "ยื่นคำร้องขอเบิก", 
    "ตรวจสอบสถานะสมาชิก (เจ้าหน้าที่)"
])

# ข้อมูลสมมติสมาชิกเดิม
member_info = {
    "name": "นายสะเดา มีความสุข",
    "join_date": date(2020, 1, 1),
    "last_payment": date(2026, 3, 20),
    "medical_used": 5,
    "total_savings": 2200
}

if menu == "Dashboard สมาชิก":
    st.header(f"ยินดีต้อนรับ, {member_info['name']}")
    status, status_type = check_membership_status(member_info['last_payment'])
    death_benefit = calculate_death_benefit(member_info['join_date'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("สถานะสมาชิก", status)
    with col2: st.metric("ยอดเงินออมรวม (บาท)", f"{member_info['total_savings']:,}")
    with col3: st.metric("สิทธิเงินจัดการศพปัจจุบัน", f"{death_benefit:,} บาท")
    with col4:
        remaining_med = 12 - member_info['medical_used']
        st.metric("สิทธิค่ารักษาคงเหลือ", f"{remaining_med} / 12 คืน")
        st.progress(remaining_med / 12)

elif menu == "สมัครสมาชิกใหม่":
    st.header("📝 แบบฟอร์มสมัครสมาชิกกองทุน (รายใหม่)")
    st.info("ค่าธรรมเนียมสมัคร 20 บาท เพื่อจัดทำสมุดประจำตัวสมาชิก (ไม่คืนเงินทุกกรณี)")
    
    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("ชื่อ-นามสกุล")
            id_card = st.text_input("เลขบัตรประจำตัวประชาชน")
            birth_date = st.date_input("วัน/เดือน/ปี เกิด", min_value=date(1920, 1, 1))
        with col2:
            address = st.text_area("ที่อยู่ตามทะเบียนบ้าน/สถานที่ประกอบอาชีพในเขตเทศบาล")
            phone = st.text_input("เบอร์โทรศัพท์ติดต่อ")
            beneficiary = st.text_input("ชื่อผู้รับผลประโยชน์ (กรณีเสียชีวิต)")

        st.subheader("📁 อัปโหลดเอกสารประกอบ (ตามระเบียบข้อ 16)")
        id_doc = st.file_upload("สำเนาบัตรประชาชน/สูติบัตร")
        house_doc = st.file_upload("สำเนาทะเบียนบ้าน")
        
        st.write("---")
        agree = st.checkbox("ข้าพเจ้ายินยอมปฏิบัติตามระเบียบข้อบังคับของกองทุนทุกประการ")
        
        submit_reg = st.form_submit_button("ส่งข้อมูลสมัครสมาชิก")
        
        if submit_reg:
            if agree and full_name and id_card:
                st.success("บันทึกข้อมูลการสมัครสำเร็จ! กรุณาชำระค่าธรรมเนียม 20 บาทที่กองสวัสดิการชุมชน")
                st.balloons()
            else:
                st.error("กรุณากรอกข้อมูลให้ครบถ้วนและกดยอมรับเงื่อนไข")

elif menu == "ยื่นคำร้องขอเบิก":
    st.header("📝 ยื่นคำร้องขอเบิกสวัสดิการออนไลน์")
    with st.form("welfare_form"):
        welfare_type = st.selectbox("ประเภทสวัสดิการ", [
            "ค่ารักษาพยาบาล (นอนโรงพยาบาล)", "สวัสดิการคลอดบุตร", 
            "ช่วยเหลือภัยธรรมชาติ", "กรณีเสียชีวิต"
        ])
        amount = st.number_input("รายละเอียดจำนวน (คืน/บาท)", min_value=1)
        doc = st.file_upload("แนบหลักฐาน (ใบรับรองแพทย์/ใบมรณบัตร)")
        submitted = st.form_submit_button("ส่งคำร้อง")
        if submitted: st.success("ส่งคำร้องสำเร็จ! จะดำเนินการภายใน 30 วัน")

elif menu == "ตรวจสอบสถานะสมาชิก (เจ้าหน้าที่)":
    st.header("🔍 ระบบสืบค้นข้อมูลสมาชิก (Admin Only)")
    search_id = st.text_input("กรอกเลขบัตรประชาชน หรือเลขสมาชิก")
    if search_id: st.write("พบข้อมูลสมาชิกในระบบคลาวด์")
