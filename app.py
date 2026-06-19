import streamlit as st
import json
import os
from datetime import date, timedelta, datetime
import pandas as pd

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Study Hours Logbook",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

DATA_FILE = "study_data.json"
PIN_FILE = "pin.json"

# ============================================================
# WEEKEND CALCULATION (your exact table + extrapolation)
# ============================================================
LOOKUP = {16: 160, 15: 140, 14: 80, 13: 60, 12: 30, 11: 15,
          10: 0, 9: -15, 8: -30, 7: -60, 6: -80, 5: -140}

def calc_adjustment(h):
    if h is None:
        return None
    if 5 <= h <= 16:
        lo, hi = int(h // 1), int(-(-h // 1))  # floor, ceil
        if lo == hi:
            return LOOKUP[int(h)]
        lo_a, hi_a = LOOKUP[lo], LOOKUP[hi]
        return lo_a + (hi_a - lo_a) * (h - lo)
    if h > 16:
        return 160 + (h - 16) * 20
    if 0 < h < 5:
        return -140 - (5 - h) * 60
    if h == 0:
        return -140 - 5 * 60
    return 0

def fmt_min(total_min):
    if total_min is None:
        return "—"
    total_min = round(total_min)
    sign = "-" if total_min < 0 else ""
    a = abs(total_min)
    return f"{sign}{a // 60} hr {a % 60} min"

# ============================================================
# DATE HELPERS
# ============================================================
def get_monday(d):
    return d - timedelta(days=d.weekday())

def iso(d):
    return d.isoformat()

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# ============================================================
# DATA PERSISTENCE
# ============================================================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def ensure_week(data, key):
    if key not in data:
        data[key] = {"mins": [None] * 5}
    return data[key]

def week_avg_hours(week):
    filled = [m for m in week["mins"] if m is not None]
    if not filled:
        return None
    return (sum(filled) / len(filled)) / 60

def week_result_minutes(week):
    avg = week_avg_hours(week)
    if avg is None:
        return None
    return 180 + calc_adjustment(avg)

# ============================================================
# PIN LOCK
# ============================================================
def load_pin():
    if os.path.exists(PIN_FILE):
        try:
            with open(PIN_FILE) as f:
                return json.load(f).get("pin")
        except Exception:
            return None
    return None

def save_pin(pin):
    with open(PIN_FILE, "w") as f:
        json.dump({"pin": pin}, f)

# ============================================================
# STYLING
# ============================================================
st.markdown("""
<style>
    .main { background: #FAFAFE; }
    .stApp { background:
        radial-gradient(circle at 8% 8%, rgba(123,92,250,0.08), transparent 38%),
        radial-gradient(circle at 95% 12%, rgba(0,200,150,0.08), transparent 40%),
        #FAFAFE; }
    h1, h2, h3 { font-family: 'Georgia', serif; }
    div[data-testid="stMetricValue"] { font-size: 20px; font-weight: 700; }
    .reward-box {
        background: linear-gradient(120deg, #1A0F3D, #2B1854 50%, #0E3D34);
        border-radius: 18px; padding: 22px 24px; color: #fff; margin: 12px 0 20px;
    }
    .reward-label { font-size: 12px; color: rgba(255,255,255,0.6);
        text-transform: uppercase; letter-spacing: 0.06em; font-weight: 700; margin-bottom: 6px; }
    .reward-value { font-family: 'Georgia', serif; font-size: 30px; font-weight: 700; color: #FFB627; }
    .reward-sub { font-size: 12px; color: rgba(255,255,255,0.5); margin-top: 6px; }
    .stButton button { border-radius: 10px; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False
if "view_monday" not in st.session_state:
    st.session_state.view_monday = iso(get_monday(date.today()))

stored_pin = load_pin()

# ============================================================
# LOCK SCREEN
# ============================================================
if not st.session_state.unlocked:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align:center;'>📚 Study Logbook</h1>", unsafe_allow_html=True)

    if stored_pin is None:
        st.markdown("<p style='text-align:center; color:#6B7280;'>Create a 4-digit passcode to protect your data</p>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            new_pin = st.text_input("New passcode", type="password", max_chars=4, key="newpin")
            confirm_pin = st.text_input("Confirm passcode", type="password", max_chars=4, key="confirmpin")
            if st.button("Set passcode", use_container_width=True):
                if len(new_pin) == 4 and new_pin.isdigit():
                    if new_pin == confirm_pin:
                        save_pin(new_pin)
                        st.session_state.unlocked = True
                        st.rerun()
                    else:
                        st.error("Passcodes don't match")
                else:
                    st.error("Passcode must be 4 digits")
    else:
        st.markdown("<p style='text-align:center; color:#6B7280;'>Enter your passcode</p>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            entered = st.text_input("Passcode", type="password", max_chars=4, key="enterpin")
            if st.button("Unlock", use_container_width=True):
                if entered == stored_pin:
                    st.session_state.unlocked = True
                    st.rerun()
                else:
                    st.error("Incorrect passcode")
    st.stop()

# ============================================================
# MAIN APP
# ============================================================
data = load_data()
view_monday = date.fromisoformat(st.session_state.view_monday)
real_monday = get_monday(date.today())
week_key = iso(view_monday)
week = ensure_week(data, week_key)

# Header
hc1, hc2 = st.columns([3, 1])
with hc1:
    st.markdown("## 📚 Study hours")
with hc2:
    if st.button("🔒 Lock"):
        st.session_state.unlocked = False
        st.rerun()

# Metrics
cur_result = week_result_minutes(ensure_week(data, iso(real_monday)))
sorted_keys = sorted(data.keys())
last_keys = [k for k in sorted_keys if k < iso(real_monday)]
last_result = week_result_minutes(data[last_keys[-1]]) if last_keys else None

m1, m2, m3 = st.columns(3)
m1.metric("This week", fmt_min(cur_result) if cur_result is not None else "No data")
m2.metric("Last week", fmt_min(last_result) if last_result is not None else "No data")
m3.metric("Weeks tracked", len(sorted_keys))

st.divider()

# Week navigation
nav1, nav2, nav3 = st.columns([1, 3, 1])
with nav1:
    if st.button("◀ Prev"):
        st.session_state.view_monday = iso(view_monday - timedelta(days=7))
        st.rerun()
with nav2:
    friday = view_monday + timedelta(days=4)
    tag = "This week" if view_monday == real_monday else ("Past week" if view_monday < real_monday else "Upcoming")
    st.markdown(f"<p style='text-align:center; margin:0;'><b>{view_monday.strftime('%d %b')} – {friday.strftime('%d %b')}</b><br><span style='color:#7B5CFA; font-size:12px;'>{tag}</span></p>", unsafe_allow_html=True)
with nav3:
    if view_monday < real_monday:
        if st.button("Next ▶"):
            st.session_state.view_monday = iso(view_monday + timedelta(days=7))
            st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# Daily entry
st.markdown("#### Log your hours")
cols = st.columns(5)
changed = False
for i, day in enumerate(DAY_NAMES):
    d = view_monday + timedelta(days=i)
    mins = week["mins"][i]
    cur_h = mins // 60 if mins is not None else 0
    cur_m = mins % 60 if mins is not None else 0
    with cols[i]:
        st.markdown(f"<p style='text-align:center; font-size:12px; color:#7B5CFA; font-weight:700; margin-bottom:2px;'>{day[:3]}</p><p style='text-align:center; font-size:11px; color:#6B7280; margin-top:0;'>{d.strftime('%d/%m')}</p>", unsafe_allow_html=True)
        h = st.number_input("hr", min_value=0, max_value=23, value=int(cur_h), key=f"h{i}", label_visibility="collapsed")
        m = st.number_input("min", min_value=0, max_value=59, value=int(cur_m), key=f"m{i}", label_visibility="collapsed")
        new_val = h * 60 + m
        if new_val != (mins if mins is not None else 0):
            pass  # captured on save

if st.button("💾 Save week", use_container_width=True, type="primary"):
    for i in range(5):
        h = st.session_state[f"h{i}"]
        m = st.session_state[f"m{i}"]
        total = h * 60 + m
        week["mins"][i] = total if total > 0 else None
    data[week_key] = week
    save_data(data)
    st.success("Saved!")
    st.rerun()

# Reward panel
result = week_result_minutes(week)
filled_count = len([m for m in week["mins"] if m is not None])
if result is not None:
    sub = f"{filled_count} of 5 days logged"
    val = fmt_min(result)
else:
    sub = "Log hours to calculate"
    val = "—"
st.markdown(f"""
<div class="reward-box">
  <div class="reward-label">🏖️ Weekend free time</div>
  <div class="reward-value">{val}</div>
  <div class="reward-sub">{sub}</div>
</div>
""", unsafe_allow_html=True)

# Charts
st.markdown("#### This week — daily hours")
day_data = pd.DataFrame({
    "Day": DAY_NAMES,
    "Hours": [round(m / 60, 1) if m is not None else 0 for m in week["mins"]]
}).set_index("Day")
st.bar_chart(day_data, height=220, color="#7B5CFA")

# History
st.markdown("#### Weekly history")
if sorted_keys:
    hist_rows = []
    for k in sorted_keys:
        w = data[k]
        mon = date.fromisoformat(k)
        fri = mon + timedelta(days=4)
        r = week_result_minutes(w)
        fc = len([m for m in w["mins"] if m is not None])
        hist_rows.append({
            "Week": f"{mon.strftime('%d %b')} – {fri.strftime('%d %b')}",
            "Days logged": f"{fc}/5",
            "Weekend time": fmt_min(r) if r is not None else "—",
            "_hours": round(r / 60, 1) if r is not None else 0,
        })
    hist_df = pd.DataFrame(hist_rows)
    st.dataframe(hist_df[["Week", "Days logged", "Weekend time"]], use_container_width=True, hide_index=True)

    chart_df = hist_df.set_index("Week")[["_hours"]].rename(columns={"_hours": "Weekend hours"})
    st.markdown("#### Weekend free time per week")
    st.bar_chart(chart_df, height=220, color="#00C896")
else:
    st.info("No history yet. Log some hours to get started.")

# Backup / restore
with st.expander("⚙️ Backup & restore data"):
    st.caption("Copy this code to back up, or paste a backup to restore.")
    st.code(json.dumps(data), language="json")
    restore_text = st.text_area("Paste backup code to restore", height=80)
    if st.button("Restore from code"):
        try:
            restored = json.loads(restore_text)
            save_data(restored)
            st.success("Data restored!")
            st.rerun()
        except Exception:
            st.error("Invalid backup code")

st.markdown("<p style='text-align:center; color:#9CA3AF; font-size:11px; margin-top:24px;'>Data saved on the app server. Use backup to transfer between deployments.</p>", unsafe_allow_html=True)
