import streamlit as st

from .pipeline import build_demo

st.set_page_config(page_title="Finance Operations Demo", layout="wide")
demo = build_demo()
st.title("Finance Operations Intelligence Engine")
st.caption("Synthetic demonstration. No accounting-system connection.")
left, mid, right = st.columns(3)
left.metric("Gross margin", f"{demo['kpis']['gross_margin_pct']}%")
mid.metric("DSO", f"{demo['kpis']['days_sales_outstanding']} days")
right.metric("Week 13 cash", f"${demo['management_package']['week_13_cash']:,.0f}")
st.subheader("Human approval queue")
st.dataframe(demo["approval_queue"], use_container_width=True)
st.subheader("13-week cash forecast")
st.line_chart({"ending cash": [row["ending_cash"] for row in demo["cash_forecast"]]})
