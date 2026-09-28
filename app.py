#import necessary Libraries
import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="St. George's – Church Analytics Dashboard",
    page_icon="⛪",
    layout="wide",
    initial_sidebar_state="expanded",
)

PRIMARY = "#5B2C6F"
ACCENT = "#D4AC0D"
GOOD = "#2E8B57"
BAD = "#C0392B"

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = px.colors.qualitative.Set2

# --------------------------------------------------------------------------
# EXPECTED SCHEMA (matches the uploaded register)
# --------------------------------------------------------------------------
EXPECTED_COLS = [
    "Member_ID", "First_Name", "Last_Name", "Gender", "Age",
    "Baptismal_Status", "Baptismal_Date", "Baptismal_Parish",
    "First_communion_Status", "First_communion_Date",
    "Confirmation_Date", "Confirmation_Parish",
    "Marriage_Status", "Marriage_Date", "Marriage_Parish",
    "Jumuia", "Church_Groups", "Ministry",
    "Leadership_Position", "Tithe", "Departed_Congregants",
]

DATE_COLS = ["Baptismal_Date", "First_communion_Date", "Confirmation_Date",
             "Marriage_Date", "Departed_Congregants"]


# --------------------------------------------------------------------------
# DATA LOADING & CLEANING
# --------------------------------------------------------------------------
@st.cache_data
def make_sample_data(n=400, seed=42):
    """Synthetic data shaped like the real register, for demo purposes."""
    import numpy as np
    rng = np.random.default_rng(seed)

    parishes = ["Regina Mundi Parish", "St. Charles Lwanga Parish", "St. Francis Xavier Parish",
                "St. Peter Claver Parish", "Christ the King Cathedral", "Holy Family Basilica",
                "Consolata Shrine Parish", "Sacred Heart Parish", "St. Joseph the Worker Parish",
                "St. Paul's Parish", "St. Austin's Parish", "Our Lady of Visitation Parish"]
    jumuias = ["St. Martin", "St. Monica", "St. Dominic", "St. Joseph", "St. Cecilia",
               "St. Rita", "St. Charles Lwanga", "St. Michael", "St. Anthony", "St. Paul",
               "St. Peter", "St. Jude", "St. Francis", "St. Mary"]
    groups = ["CWA", "CMA", "MYM", "YCA", "PMC"]
    ministries = ["Catechist", "Choir", "Lectors", "Men_Fellowship", "Small_Christian_Comm",
                  "Youth_Ministry", "Prayer_Group", None, None, None]
    leadership = ["Moderator", "Vice_Moderator", "Secretary", "Treasurer", "Coordinator", None,
                  None, None, None, None]

    rows = []
    for i in range(1, n + 1):
        gender = rng.choice(["Male", "Female"])
        age = int(rng.integers(1, 85))
        baptized = age >= 0 and rng.random() < 0.93
        first_comm = baptized and age >= 8 and rng.random() < 0.8
        confirmed = first_comm and age >= 13 and rng.random() < 0.65
        married = confirmed and age >= 20 and rng.random() < 0.5
        tithe = rng.choice(["Yes", "No"], p=[0.55, 0.45])
        departed = rng.random() < 0.08
        dep_date = None
        if departed:
            dep_date = pd.Timestamp(2023, 1, 1) + pd.Timedelta(days=int(rng.integers(0, 1000)))

        def rand_date(start_year, end_year):
            start = pd.Timestamp(start_year, 1, 1).toordinal()
            end = pd.Timestamp(end_year, 12, 31).toordinal()
            return pd.Timestamp.fromordinal(int(rng.integers(start, end)))

        rows.append({
            "Member_ID": i,
            "First_Name": f"Member{i}",
            "Last_Name": f"Family{rng.integers(1, 120)}",
            "Gender": gender,
            "Age": age,
            "Baptismal_Status": "Yes" if baptized else "No",
            "Baptismal_Date": rand_date(1945, 2026) if baptized else None,
            "Baptismal_Parish": rng.choice(parishes) if baptized else None,
            "First_communion_Status": "Yes" if first_comm else "No",
            "First_communion_Date": rand_date(1955, 2026) if first_comm else None,
            "Confirmation_Date": rand_date(1960, 2026) if confirmed else None,
            "Confirmation_Parish": rng.choice(parishes) if confirmed else None,
            "Marriage_Status": "YES" if married else "NO",
            "Marriage_Date": rand_date(1975, 2026) if married else None,
            "Marriage_Parish": rng.choice(parishes) if married else None,
            "Jumuia": rng.choice(jumuias),
            "Church_Groups": rng.choice(groups),
            "Ministry": rng.choice(ministries),
            "Leadership_Position": rng.choice(leadership),
            "Tithe": tithe,
            "Departed_Congregants": dep_date,
        })
    return pd.DataFrame(rows)


@st.cache_data
def load_excel(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes))
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]

    # normalize Yes/No style columns
    for col in ["Baptismal_Status", "First_communion_Status", "Tithe"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    if "Marriage_Status" in df.columns:
        df["Marriage_Status"] = df["Marriage_Status"].astype(str).str.strip().str.upper()

    # dates
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    if "Age" in df.columns:
        df["Age"] = pd.to_numeric(df["Age"], errors="coerce")

    # derived flags
    df["Is_Baptized"] = df.get("Baptismal_Status", pd.Series(dtype=str)).eq("Yes")
    df["Is_First_Communion"] = df.get("First_communion_Status", pd.Series(dtype=str)).eq("Yes")
    df["Is_Confirmed"] = df.get("Confirmation_Date").notna() if "Confirmation_Date" in df.columns else False
    df["Is_Married"] = df.get("Marriage_Status", pd.Series(dtype=str)).eq("YES")
    df["Is_Tithing"] = df.get("Tithe", pd.Series(dtype=str)).eq("Yes")
    df["Has_Ministry"] = df.get("Ministry").notna() if "Ministry" in df.columns else False
    df["Has_Leadership"] = df.get("Leadership_Position").notna() if "Leadership_Position" in df.columns else False
    df["Is_Departed"] = df.get("Departed_Congregants").notna() if "Departed_Congregants" in df.columns else False
    df["Is_Active"] = ~df["Is_Departed"]

    def age_band(a):
        if pd.isna(a):
            return "Unknown"
        if a < 13:
            return "PMC (0-14)"
        if a < 18:
            return "MYM (14-18)"
        if a < 24:
            return "YSC (1-17)"
        if a < 35:
            return "YCA (18-34)"
        if a < 100:
            return "CMA/CWA (35-59)"
        #return "Senior (60+)"

    df["Age_Band"] = df["Age"].apply(age_band)
    return df


def pct(numerator, denominator):
    if denominator == 0:
        return 0.0
    return 100 * numerator / denominator


def kpi_card(col, label, value, delta=None, help_text=None):
    with col:
        st.metric(label, value, delta=delta, help=help_text)


# --------------------------------------------------------------------------
# SIDEBAR: DATA SOURCE + FILTERS
# --------------------------------------------------------------------------
st.sidebar.title("⛪ Dashboard Filters.")
st.sidebar.caption("Upload your membership register or explore with sample data.")

uploaded = st.sidebar.file_uploader("Upload Excel register (.xlsx)", type=["xlsx", "xls"])

if uploaded is not None:
    raw_df = load_excel(uploaded.read())
    st.sidebar.success(f"Loaded {len(raw_df)} records from your file.")
else:
    raw_df = make_sample_data()
    st.sidebar.info("Showing **sample data** — upload your file to see your real numbers.")

df = clean_data(raw_df)

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

gender_opts = sorted(df["Gender"].dropna().unique().tolist()) if "Gender" in df.columns else []
group_opts = sorted(df["Church_Groups"].dropna().unique().tolist()) if "Church_Groups" in df.columns else []
jumuia_opts = sorted(df["Jumuia"].dropna().unique().tolist()) if "Jumuia" in df.columns else []

sel_gender = st.sidebar.multiselect("Gender", gender_opts, default=gender_opts)
sel_group = st.sidebar.multiselect("Church Group", group_opts, default=group_opts)
sel_jumuia = st.sidebar.multiselect("Jumuia", jumuia_opts, default=jumuia_opts)
sel_status = st.sidebar.radio("Membership Status", ["All", "Active only", "Departed only"], index=0)

min_age = int(df["Age"].min()) if df["Age"].notna().any() else 0
max_age = int(df["Age"].max()) if df["Age"].notna().any() else 100
age_range = st.sidebar.slider("Age range", min_age, max_age, (min_age, max_age))

fdf = df.copy()
if sel_gender:
    fdf = fdf[fdf["Gender"].isin(sel_gender)]
if sel_group:
    fdf = fdf[fdf["Church_Groups"].isin(sel_group)]
if sel_jumuia:
    fdf = fdf[fdf["Jumuia"].isin(sel_jumuia)]
if sel_status == "Active only":
    fdf = fdf[fdf["Is_Active"]]
elif sel_status == "Departed only":
    fdf = fdf[fdf["Is_Departed"]]
fdf = fdf[(fdf["Age"].fillna(-1) >= age_range[0]) & (fdf["Age"].fillna(-1) <= age_range[1]) | fdf["Age"].isna()]

st.sidebar.markdown("---")
st.sidebar.caption(f"Showing **{len(fdf)}** of {len(df)} congregants after filters.")

# --------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------
#st.image("church.webp", width=100)
#st.title("⛪ St. George's – Church Analytics Dashboard.")
col1, col2 = st.columns([1, 8])

with col1:
    st.image("church.webp", width=70)

with col2:
    st.title("St. George's – Church Analytics Dashboard")
st.caption("Membership, sacraments, engagement, stewardship and retention — at a glance.")

tabs = st.tabs([
    "📊 Overview",
    "✝️ Sacramental Journey",
    "🤝 Engagement & Leadership",
    "💰 Stewardship (Tithe)",
    "📉 Retention & Attrition",
    "🧑‍🤝‍🧑 Demographics",
])

# ==========================================================================
# TAB 1 — OVERVIEW
# ==========================================================================
with tabs[0]:
    total = len(fdf)
    active = fdf["Is_Active"].sum()
    departed = fdf["Is_Departed"].sum()
    avg_age = fdf["Age"].mean()
    tithing_rate = pct(fdf["Is_Tithing"].sum(), total)
    ministry_rate = pct(fdf["Has_Ministry"].sum(), total)

    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_card(c1, "Total Congregants", f"{total:,}")
    kpi_card(c2, "Active Members", f"{active:,}", delta=f"{pct(active,total):.0f}% of total")
    kpi_card(c3, "Departed", f"{departed:,}", delta=f"-{pct(departed,total):.0f}%" if departed else "0%")
    kpi_card(c4, "Avg. Age", f"{avg_age:.0f} yrs" if pd.notna(avg_age) else "N/A")
    kpi_card(c5, "Tithing Rate", f"{tithing_rate:.0f}%")

    st.markdown("#### Sacrament Completion Rates")
    sac_cols = st.columns(4)
    sac_data = {
        "Baptism": fdf["Is_Baptized"].sum(),
        "First Communion": fdf["Is_First_Communion"].sum(),
        "Confirmation": fdf["Is_Confirmed"].sum(),
        "Marriage": fdf["Is_Married"].sum(),
    }
    for col, (label, count) in zip(sac_cols, sac_data.items()):
        kpi_card(col, label, f"{pct(count, total):.0f}%", delta=f"{count:,} people")

    st.markdown("---")
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown("##### Membership by Jumuia")
        if "Jumuia" in fdf.columns:
            jc = fdf["Jumuia"].value_counts().reset_index()
            jc.columns = ["Jumuia", "Members"]
            fig = px.bar(jc, x="Jumuia", y="Members", color="Members",
                         color_continuous_scale="Purples")
            fig.update_layout(showlegend=False, coloraxis_showscale=False, height=380)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("##### Church Group Mix")
        if "Church_Groups" in fdf.columns:
            gc = fdf["Church_Groups"].value_counts().reset_index()
            gc.columns = ["Group", "Members"]
            fig = px.pie(gc, names="Group", values="Members", hole=0.45)
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **Why these KPIs matter:** total membership and active/departed counts give leadership an
    immediate read on congregation health; sacrament completion rates flag how well the
    community is being formed spiritually; Jumuia and group mix show where people are
    concentrated so resources and pastoral visits can be targeted.
    """)

# ==========================================================================
# TAB 2 — SACRAMENTAL JOURNEY
# ==========================================================================
with tabs[1]:
    st.subheader("Sacramental Funnel & Drop-off")
    st.caption("Where do people stop progressing through the sacraments?")

    funnel_df = pd.DataFrame({
        "Stage": ["Baptism", "First Communion", "Confirmation", "Marriage"],
        "Count": [
            fdf["Is_Baptized"].sum(),
            fdf["Is_First_Communion"].sum(),
            fdf["Is_Confirmed"].sum(),
            fdf["Is_Married"].sum(),
        ],
    })
    fig = go.Figure(go.Funnel(
        y=funnel_df["Stage"], x=funnel_df["Count"],
        textinfo="value+percent initial",
        marker={"color": [PRIMARY, "#8E44AD", "#AF7AC5", ACCENT]},
    ))
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    drop_bc = fdf["Is_Baptized"].sum() - fdf["Is_First_Communion"].sum()
    drop_cf = fdf["Is_First_Communion"].sum() - fdf["Is_Confirmed"].sum()
    drop_fm = fdf["Is_Confirmed"].sum() - fdf["Is_Married"].sum()
    d1, d2, d3 = st.columns(3)
    kpi_card(d1, "Drop-off: Baptism → 1st Communion", f"{max(drop_bc,0):,}")
    kpi_card(d2, "Drop-off: 1st Communion → Confirmation", f"{max(drop_cf,0):,}")
    kpi_card(d3, "Drop-off: Confirmation → Marriage", f"{max(drop_fm,0):,}")

    st.markdown("---")
    st.subheader("Sacrament Trends Over Time")
    date_choice = st.selectbox(
        "Choose a sacrament date field",
        [c for c in ["Baptismal_Date", "First_communion_Date", "Confirmation_Date", "Marriage_Date"] if c in fdf.columns],
    )
    if date_choice and fdf[date_choice].notna().any():
        ts = fdf.dropna(subset=[date_choice]).copy()
        ts["Year"] = ts[date_choice].dt.year
        yc = ts.groupby("Year").size().reset_index(name="Count")
        fig2 = px.line(yc, x="Year", y="Count", markers=True)
        fig2.update_traces(line_color=PRIMARY)
        fig2.update_layout(height=360)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No valid dates available for this field in the current filter selection.")

    st.markdown("---")
    st.subheader("Top Parishes by Sacrament")
    parish_field = st.selectbox(
        "Parish field",
        [c for c in ["Baptismal_Parish", "Confirmation_Parish", "Marriage_Parish"] if c in fdf.columns],
    )
    if parish_field:
        pc = fdf[parish_field].value_counts().head(10).reset_index()
        pc.columns = ["Parish", "Count"]
        fig3 = px.bar(pc, x="Count", y="Parish", orientation="h", color="Count",
                      color_continuous_scale="Purples")
        fig3.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False, height=400)
        st.plotly_chart(fig3, use_container_width=True)

# ==========================================================================
# TAB 3 — ENGAGEMENT & LEADERSHIP
# ==========================================================================
with tabs[2]:
    st.subheader("Ministry & Leadership Engagement")

    total = len(fdf)
    e1, e2, e3 = st.columns(3)
    kpi_card(e1, "In a Ministry", f"{pct(fdf['Has_Ministry'].sum(), total):.0f}%",
              delta=f"{fdf['Has_Ministry'].sum():,} people")
    kpi_card(e2, "In a Leadership Role", f"{pct(fdf['Has_Leadership'].sum(), total):.0f}%",
              delta=f"{fdf['Has_Leadership'].sum():,} people")
    unengaged = total - fdf["Has_Ministry"].sum()
    kpi_card(e3, "Not Yet in a Ministry", f"{unengaged:,}", delta="Growth opportunity")

    left, right = st.columns(2)
    with left:
        st.markdown("##### Ministry Participation")
        if "Ministry" in fdf.columns:
            mc = fdf["Ministry"].value_counts().reset_index()
            mc.columns = ["Ministry", "Members"]
            fig = px.bar(mc, x="Members", y="Ministry", orientation="h", color="Members",
                         color_continuous_scale="Greens")
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False, height=420)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("##### Leadership Positions Held")
        if "Leadership_Position" in fdf.columns:
            lc = fdf["Leadership_Position"].value_counts().reset_index()
            lc.columns = ["Position", "Count"]
            fig = px.bar(lc, x="Position", y="Count", color="Count",
                         color_continuous_scale="Oranges")
            fig.update_layout(coloraxis_showscale=False, height=420)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Engagement by Church Group")
    if "Church_Groups" in fdf.columns:
        eng = fdf.groupby("Church_Groups").agg(
            Members=("Member_ID", "count") if "Member_ID" in fdf.columns else ("Church_Groups", "count"),
            Ministry_Rate=("Has_Ministry", "mean"),
            Leadership_Rate=("Has_Leadership", "mean"),
            Tithing_Rate=("Is_Tithing", "mean"),
        ).reset_index()
        for c in ["Ministry_Rate", "Leadership_Rate", "Tithing_Rate"]:
            eng[c] = (eng[c] * 100).round(1)
        st.dataframe(eng, use_container_width=True, hide_index=True)

    st.markdown("""
    **Decision angle:** groups with high membership but low ministry/leadership rates
    represent an untapped volunteer pool. Groups with high leadership but low tithing
    may need clearer stewardship messaging.
    """)

# ==========================================================================
# TAB 4 — STEWARDSHIP (TITHE)
# ==========================================================================
with tabs[3]:
    st.subheader("Tithing / Stewardship KPIs")
    total = len(fdf)
    t1, t2, t3 = st.columns(3)
    kpi_card(t1, "Overall Tithing Rate", f"{pct(fdf['Is_Tithing'].sum(), total):.0f}%")
    kpi_card(t2, "Tithing Members", f"{fdf['Is_Tithing'].sum():,}")
    kpi_card(t3, "Non-Tithing Members", f"{total - fdf['Is_Tithing'].sum():,}")

    left, right = st.columns(2)
    with left:
        st.markdown("##### Tithing Rate by Jumuia")
        if "Jumuia" in fdf.columns:
            tj = fdf.groupby("Jumuia")["Is_Tithing"].mean().mul(100).round(1).sort_values(ascending=False).reset_index()
            tj.columns = ["Jumuia", "Tithing_Rate_%"]
            fig = px.bar(tj, x="Jumuia", y="Tithing_Rate_%", color="Tithing_Rate_%",
                         color_continuous_scale="YlGn")
            fig.update_layout(coloraxis_showscale=False, height=400)
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("##### Tithing Rate by Age Band")
        tb = fdf.groupby("Age_Band")["Is_Tithing"].mean().mul(100).round(1).reset_index()
        tb.columns = ["Age Band", "Tithing_Rate_%"]
        order = ["Children (0-7)", "Pre-teen (8-12)", "Youth (13-17)",
                 "Young Adult (18-34)", "Adult (35-59)", "Senior (60+)", "Unknown"]
        tb["Age Band"] = pd.Categorical(tb["Age Band"], categories=order, ordered=True)
        tb = tb.sort_values("Age Band")
        fig = px.bar(tb, x="Age Band", y="Tithing_Rate_%", color="Tithing_Rate_%",
                     color_continuous_scale="YlOrBr")
        fig.update_layout(coloraxis_showscale=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **Decision angle:** low-tithing Jumuias or age bands can be prioritized for
    stewardship teaching or targeted pastoral follow-up.
    """)

# ==========================================================================
# TAB 5 — RETENTION & ATTRITION
# ==========================================================================
with tabs[4]:
    st.subheader("Retention & Attrition")
    total = len(fdf)
    departed = fdf["Is_Departed"].sum()
    r1, r2, r3 = st.columns(3)
    kpi_card(r1, "Attrition Rate", f"{pct(departed, total):.1f}%")
    kpi_card(r2, "Retention Rate", f"{pct(total - departed, total):.1f}%")
    kpi_card(r3, "Departed (count)", f"{departed:,}")

    if "Departed_Congregants" in fdf.columns and fdf["Departed_Congregants"].notna().any():
        dep = fdf.dropna(subset=["Departed_Congregants"]).copy()
        dep["Month"] = dep["Departed_Congregants"].dt.to_period("M").astype(str)
        mc = dep.groupby("Month").size().reset_index(name="Departures")
        fig = px.bar(mc, x="Month", y="Departures", color="Departures", color_continuous_scale="Reds")
        fig.update_layout(coloraxis_showscale=False, height=380)
        st.markdown("##### Departures Over Time")
        st.plotly_chart(fig, use_container_width=True)

        left, right = st.columns(2)
        with left:
            st.markdown("##### Departures by Jumuia")
            if "Jumuia" in dep.columns:
                dj = dep["Jumuia"].value_counts().reset_index()
                dj.columns = ["Jumuia", "Departures"]
                fig = px.bar(dj, x="Jumuia", y="Departures", color="Departures", color_continuous_scale="Reds")
                fig.update_layout(coloraxis_showscale=False, height=360)
                st.plotly_chart(fig, use_container_width=True)
        with right:
            st.markdown("##### Departures by Engagement Level")
            dep["Engagement"] = dep["Has_Ministry"].map({True: "Had a Ministry", False: "No Ministry"})
            de = dep["Engagement"].value_counts().reset_index()
            de.columns = ["Engagement", "Departures"]
            fig = px.pie(de, names="Engagement", values="Departures", hole=0.45)
            fig.update_layout(height=360)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Decision angle:** if most departures come from members with **no ministry
        involvement**, this is strong evidence that engagement (not just attendance)
        drives retention — prioritize plugging new/inactive members into a ministry
        early.
        """)
    else:
        st.info("No departure dates found in the current filter selection — attrition trend charts need the 'Departed_Congregants' date column populated.")

# ==========================================================================
# TAB 6 — DEMOGRAPHICS
# ==========================================================================
with tabs[5]:
    st.subheader("Congregation Demographics")
    left, right = st.columns(2)
    with left:
        st.markdown("##### Age Distribution")
        fig = px.histogram(fdf.dropna(subset=["Age"]), x="Age", nbins=20, color_discrete_sequence=[PRIMARY])
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        st.markdown("##### Age Band Composition")
        ab = fdf["Age_Band"].value_counts().reset_index()
        ab.columns = ["Age Band", "Members"]
        fig = px.pie(ab, names="Age Band", values="Members", hole=0.45)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### Gender Balance")
    if "Gender" in fdf.columns:
        gcount = fdf["Gender"].value_counts().reset_index()
        gcount.columns = ["Gender", "Members"]
        fig = px.bar(gcount, x="Gender", y="Members", color="Gender")
        fig.update_layout(height=340)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### Filtered Data (for export / verification)")
    st.dataframe(fdf, use_container_width=True, hide_index=True)
    csv = fdf.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download filtered data as CSV", csv, "filtered_congregants.csv", "text/csv")

st.markdown("---")
st.caption(f"Dashboard generated {datetime.now().strftime('%d %b %Y, %H:%M')} · By George Odhiambo.")
