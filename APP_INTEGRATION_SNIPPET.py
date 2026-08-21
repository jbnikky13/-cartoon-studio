# Add near the top of your existing app.py
from realityblend_ui import render_realityblend

# Add inside your existing Streamlit UI, after the current Cartoon Studio controls:
with st.expander("🌍 RealityBlend V6 — real backgrounds + cartoon characters"):
    render_realityblend()
