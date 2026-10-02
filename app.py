import streamlit as st
from openai import OpenAI
from datetime import datetime, timedelta
import pandas as pd

# Page setup
st.set_page_config(page_title="WardNurse AI Dashboard", page_icon="🏥", layout="wide")

# Initialize OpenAI Client via Streamlit Secrets or Sidebar Input
api_key = st.secrets.get("OPENAI_API_KEY") if "OPENAI_API_KEY" in st.secrets else None

if not api_key:
    with st.sidebar:
        st.warning("⚠️ OpenAI API Key missing!")
        api_key = st.text_input("Enter OpenAI API Key:", type="password")

client = OpenAI(api_key=api_key) if api_key else None

# Pre-defined Drug Library for quick lookup
DRUG_DATABASE = {
    "Hydrocortisone": {
        "brand": "Efcorlin",
        "class": "Corticosteroid",
        "dose": "100mg IV slow bolus over 3-5 mins",
        "iv_compat": "Compatible with Normal Saline (0.9% NaCl) and D5W",
        "caution": "Monitor blood glucose and blood pressure closely."
    },
    "Noradrenaline": {
        "brand": "Adrenor / Norad",
        "class": "Vasopressor",
        "dose": "2-4 mcg/min IV infusion via syringe pump",
        "iv_compat": "Run in D5W or NS. Incompatible with Sodium Bicarbonate",
        "caution": "Central line preferred; risk of tissue necrosis on extravasation."
    },
    "Dextrose 25%": {
        "brand": "D25",
        "class": "Hypertonic Glucose",
        "dose": "100 mL IV STAT over 10 minutes",
        "iv_compat": "Compatible with standard peripheral IV lines",
        "caution": "Re-check blood glucose in 15 minutes."
    }
}

# System Prompt for Clinical Decision Support
SYSTEM_PROMPT = """
You are "WardNurse AI", an instant Clinical Decision Support System pre-loaded with standard Indian hospital ward protocols and ACLS triage rules.

EMERGENCY PROTOCOL RULES:
1. HYPOVOLEMIC / SEPTIC SHOCK (Bed A):
   - Position: Elevate legs 45 degrees (Trendelenburg).
   - O2: High-flow O2 via non-rebreather mask (10-15 L/min).
   - IV: Prepare 500 mL Normal Saline rapid bolus STAT.
2. SEVERE RESPIRATORY DISTRESS (Bed B):
   - Position: High Fowler's position (sit upright at 90 degrees).
   - O2: Nebulization with Duolin / Budecort driven by O2 at 6-8 L/min.
   - Meds: Inj. Hydrocortisone 100mg IV STAT as per standing order.
3. SEVERE HYPOGLYCEMIA (Bed C):
   - Position: Turn patient lateral (recovery position) to prevent aspiration.
   - IV: Administer 100 mL of 25% Dextrose (D25) IV STAT over 10 mins.

INSTRUCTIONS:
- Keep emergency responses under 60 words in clear bullet points.
- Highlight immediate physical actions for the nurse while waiting for the duty doctor.
"""

# Initialize Session States
if "patients" not in st.session_state:
    st.session_state.patients = {
        "Bed A": {"name": "Ramesh (52M)", "diagnosis": "Post-Op Lap Chole", "status": "Stable", "iv_end": None},
        "Bed B": {"name": "Sunita (45F)", "diagnosis": "Acute Severe Asthma", "status": "Stable", "iv_end": None},
        "Bed C": {"name": "Amit (60M)", "diagnosis": "Diabetic Foot Ulcer", "status": "Stable", "iv_end": None}
    }

if "alert_log" not in st.session_state:
    st.session_state.alert_log = []

# Header
st.title("🏥 WardNurse AI - Clinical Decision & Monitoring Dashboard")
st.caption("Real-Time Ward Decision Support System for Nurses & Pharmacists")
st.divider()

# Helper function to call OpenAI API
def call_ai(prompt):
    if not client:
        return "❌ Please enter a valid OpenAI API Key in the sidebar or Streamlit Secrets."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

# Ward Beds Layout (3 Columns)
col1, col2, col3 = st.columns(3)

beds = [("Bed A", col1), ("Bed B", col2), ("Bed C", col3)]

for bed_id, col in beds:
    patient = st.session_state.patients[bed_id]
    with col:
        st.subheader(f"🛏️ {bed_id}")
        st.markdown(f"**Patient:** {patient['name']}")
        st.markdown(f"**Diagnosis:** {patient['diagnosis']}")
        
        # Status Badge
        if patient['status'] == "CRITICAL":
            st.error("Status: CRITICAL / DETERIORATING")
        else:
            st.success("Status: Stable")

        # IV Timer Logic (Python Exact Calculation)
        st.markdown("---")
        st.markdown("##### 💉 IV Line & Timer")
        if patient["iv_end"]:
            remaining = (patient["iv_end"] - datetime.now()).total_seconds()
            if remaining > 0:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                st.info(f"⏳ IV Drip Running: **{mins}m {secs}s** remaining")
            else:
                st.error("🚨 **IV ALERT:** Drip complete! Reset/flush line NOW!")
        else:
            st.caption("No active IV timer running.")

        # Quick Action Buttons
        st.markdown("##### ⚡ Quick Actions")
        
        # 1. Start IV Drip Button
        if st.button(f"Start 60m IV ({bed_id})", key=f"iv_{bed_id}"):
            st.session_state.patients[bed_id]["iv_end"] = datetime.now() + timedelta(minutes=60)
            st.rerun()

        # 2. EMERGENCY Deterioration Button
        if st.button(f"🚨 DETERIORATE {bed_id}", type="primary", key=f"det_{bed_id}"):
            st.session_state.patients[bed_id]["status"] = "CRITICAL"
            prompt = f"EMERGENCY: {bed_id} ({patient['diagnosis']}) is deteriorating. Give immediate 3-step protocol."
            output = call_ai(prompt)
            st.session_state.alert_log.insert(0, f"**{bed_id} ({datetime.now().strftime('%H:%M:%S')}):**\n\n{output}")
            st.rerun()

st.divider()

# Lower Section: Live AI Response Feed & Drug Library Search
left_panel, right_panel = st.columns([2, 1])

with left_panel:
    st.subheader("📋 Clinical Decision Support Feed")
    if st.session_state.alert_log:
        for alert in st.session_state.alert_log:
            st.warning(alert)
    else:
        st.info("Ward is quiet. Click a red emergency button above to trigger instant decision support protocols.")

with right_panel:
    st.subheader("💊 Drug Formulary Search")
    selected_drug = st.selectbox("Select Ward Drug:", list(DRUG_DATABASE.keys()))
    if selected_drug:
        info = DRUG_DATABASE[selected_drug]
        st.markdown(f"**Brand:** {info['brand']}")
        st.markdown(f"**Class:** {info['class']}")
        st.markdown(f"**Standard Dose:** {info['dose']}")
        st.markdown(f"**IV Compatibility:** {info['iv_compat']}")
        st.warning(f"**Caution:** {info['caution']}")

# Sidebar Actions
with st.sidebar:
    st.divider()
    if st.button("🔄 Reset Ward / Clear Alerts"):
        st.session_state.patients["Bed A"]["status"] = "Stable"
        st.session_state.patients["Bed B"]["status"] = "Stable"
        st.session_state.patients["Bed C"]["status"] = "Stable"
        st.session_state.patients["Bed A"]["iv_end"] = None
        st.session_state.patients["Bed B"]["iv_end"] = None
        st.session_state.patients["Bed C"]["iv_end"] = None
        st.session_state.alert_log = []
        st.rerun()
