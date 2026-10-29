"""GymPulse's independent Streamlit UI; all persisted data flows through HTTP."""
import html
import io
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Streamlit executes this file as a script, including in Community Cloud.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frontend.client import ApiError, GymClient

st.set_page_config(page_title="GymPulse · Train with intention", page_icon="⚡", layout="wide")


def setting(name: str, fallback: str = "") -> str:
    if os.getenv(name) is not None:
        return os.environ[name]
    try:
        return str(st.secrets.get(name, fallback))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return fallback


client = GymClient(setting("API_BASE_URL", "http://127.0.0.1:8000"), setting("APP_WRITE_TOKEN"))
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root {--lime:#c9fb69;--muted:#929b91;}
html, body, [class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif;}
h1,h2,h3,.brand,.hero-title {font-family:'Space Grotesk',sans-serif!important;letter-spacing:-1px;}
.block-container {padding:2.4rem 2.8rem 3rem;max-width:1500px;}
[data-testid="stSidebar"] {background:#151815;border-right:1px solid #2b302a;}
[data-testid="stSidebar"] .block-container {padding:2rem 1.3rem;}
.brand {font-size:30px;font-weight:700;letter-spacing:-1.5px;margin:0 0 6px;}
.brand span {color:var(--lime);}
.eyebrow {font-size:11px;color:var(--lime);letter-spacing:2.3px;font-weight:700;text-transform:uppercase;}
.muted {color:var(--muted);font-size:14px;}
.hero {border:1px solid #3a4430;background:radial-gradient(ellipse at 100% 25%,#435b22 0%,#25341c 32%,#1b2518 70%);border-radius:22px;padding:34px 36px;margin:18px 0 24px;position:relative;overflow:hidden;}
.hero-title {font-size:44px;line-height:1.12;font-weight:600;color:#f1f5eb;margin:12px 0;max-width:620px;}
.hero p {color:#b7c5aa;max-width:580px;font-size:15px;}
.hero-mark {position:absolute;right:35px;top:18px;font-size:140px;line-height:1.2;color:#c9fb69;opacity:.15;transform:rotate(-15deg);font-weight:700;}
.pill {display:inline-block;background:#c9fb6915;border:1px solid #c9fb6933;color:#c9fb69;border-radius:30px;padding:5px 11px;font-size:11px;font-weight:700;letter-spacing:1px;}
[data-testid="stMetric"] {border:1px solid #2c332b;background:#191e19;padding:20px;border-radius:16px;}
[data-testid="stMetricLabel"] {color:#9ea89c;}
[data-testid="stMetricValue"] {font-family:'Space Grotesk';font-size:32px;}
.section-label {color:#9da996;text-transform:uppercase;letter-spacing:2px;font-size:11px;margin-top:20px;}
.activity {border-bottom:1px solid #2a3028;padding:16px 2px;display:flex;align-items:center;gap:16px;}
.activity-icon {width:44px;height:44px;border-radius:12px;background:#c9fb6914;color:#c9fb69;text-align:center;line-height:44px;font-weight:bold;flex-shrink:0;}
.activity-name {font-weight:600;font-size:15px;}
.activity-meta {font-size:12px;color:#98a192;margin-top:4px;}
.activity-load {margin-left:auto;text-align:right;font-family:'Space Grotesk';font-size:20px;}
.coach {padding:22px;border:1px solid #343e2e;border-radius:16px;background:#1b2418;margin:12px 0;min-height:190px;}
.coach h3 {font-size:21px;margin:14px 0 7px;}
.coach p {color:#aab6a4;font-size:14px;line-height:1.6;}
.coach-load {font-size:30px;color:#c9fb69;font-family:'Space Grotesk';}
.footer {border-top:1px solid #2a3028;padding-top:18px;margin-top:40px;color:#75806f;font-size:12px;}
div.stButton>button[kind="primary"],div.stFormSubmitButton>button[kind="primary"] {color:#10180b;font-weight:700;border-radius:10px;}
[data-testid="stTabs"] button {font-weight:600;}
@media(max-width:700px) {.block-container{padding:1.3rem 1rem}.hero{padding:25px}.hero-title{font-size:32px}.hero-mark{display:none}}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand">gym<span>pulse</span> ↗</div><div class="muted">A little stronger. Every session.</div>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("YOUR TRAINING SPACE", ["Overview", "Workout log", "Progress", "Training coach"], label_visibility="visible")
    st.markdown("---")
    st.markdown('<div class="eyebrow">THE APPROACH</div>', unsafe_allow_html=True)
    st.caption("Show up. Track the work. Build on it. Your next session starts with understanding the last one.")
    if st.button("↻ Refresh data", use_container_width=True):
        st.rerun()
    st.caption("Demo workspace · synthetic data\n\nLoads in kilograms · dates in local calendar days")

heading, stamp = st.columns([4, 1])
with heading:
    st.markdown('<div class="eyebrow">YOUR PERSONAL TRAINING DASHBOARD</div>', unsafe_allow_html=True)
    st.title({"Overview": "Make every rep count.", "Workout log": "The work, recorded.", "Progress": "See how far you’ve come.", "Training coach": "A plan for your next rep."}[page])
with stamp:
    st.write("")
    st.caption(date.today().strftime("%A\n%d %B %Y"))

try:
    workouts = client.request("GET", "/workouts")
    summary = client.request("GET", "/summary", params={"as_of": date.today().isoformat()})
    recommendations = client.request("GET", "/recommendations", params={"as_of": date.today().isoformat()})
    status = client.request("GET", "/status")
except ApiError as error:
    st.error(str(error))
    st.info("Local startup: run `venv\\Scripts\\python.exe start.py --demo` from the project folder. The dashboard connects to FastAPI, so both apps must be running.")
    st.stop()

if status["blocked"]:
    st.warning("Database maintenance is in progress. You can view your training; new entries are temporarily paused.")

df = pd.DataFrame(workouts)
COLORS = ["#c9fb69", "#7baf81", "#4e7360", "#edd999", "#a9c4b1", "#718963"]


def chart_style(fig, height=300):
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans", color="#a9b3a4"),
        xaxis=dict(gridcolor="#272f25", title=None), yaxis=dict(gridcolor="#272f25"),
        legend=dict(orientation="h", y=-0.2), hoverlabel=dict(bgcolor="#242e20"),
    )
    return fig


def coach_card(item):
    labels = {"increase": "READY TO PROGRESS ↗", "recover": "RECOVERY FIRST ◷", "hold": "BUILD CONSISTENCY →", "deload": "TAKE A STEP BACK ↘", "restart": "EASE BACK IN ↺"}
    st.markdown(f'<div class="coach"><span class="pill">{labels[item["action"]]}</span>'
                f'<h3>{html.escape(item["exercise"])}</h3><div class="coach-load">{item["next_weight_kg"]:g} <small>kg</small></div>'
                f'<p>{html.escape(item["reason"])}</p></div>', unsafe_allow_html=True)


if page == "Overview":
    st.markdown('<div class="hero"><div class="hero-mark">↗</div><span class="pill">CONSISTENCY OVER EVERYTHING</span>'
                '<div class="hero-title">Small steps.<br>Stronger you.</div><p>Your training, your progress, your next move. Keep showing up — we’ll help you connect the dots.</p></div>', unsafe_allow_html=True)
    metrics = st.columns(4)
    for col, label, value in zip(metrics, ["Exercise entries", "Training days", "Total volume", "Exercises tracked"],
                                  [summary["total_workouts"], summary["training_days"], f'{summary["total_volume_kg"] / 1000:,.1f} t', len(summary["personal_records"])]):
        col.metric(label, value)
    left, right = st.columns([1.8, 1], gap="large")
    with left:
        st.subheader("The work adds up")
        st.caption("Weekly training volume · sets × completed reps × load")
        if summary["weekly_volume"]:
            weekly = pd.DataFrame(summary["weekly_volume"])
            fig = go.Figure(go.Scatter(x=weekly.week, y=weekly.volume_kg, mode="lines+markers", line=dict(color=COLORS[0], width=3, shape="linear"),
                                      fill="tozeroy", fillcolor="rgba(201,251,105,0.09)", marker=dict(size=7), hovertemplate="Week %{x}<br>%{y:,.0f} kg<extra></extra>"))
            fig.update_yaxes(title="Volume (kg)")
            st.plotly_chart(chart_style(fig), use_container_width=True)
        else:
            st.info("Your first logged workout will start this chart.")
    with right:
        st.subheader("Training balance")
        st.caption("Where your logged volume goes")
        if summary["muscle_volume"]:
            muscle = pd.DataFrame(summary["muscle_volume"])
            fig = px.pie(muscle, values="volume_kg", names="muscle", hole=.73, color_discrete_sequence=COLORS)
            fig.update_traces(textinfo="none", marker=dict(line=dict(color="#101211", width=4)))
            st.plotly_chart(chart_style(fig), use_container_width=True)
        else:
            st.info("Log a workout to see your muscle group balance.")
    left, right = st.columns([1.8, 1], gap="large")
    with left:
        st.subheader("Recent sessions")
        for item in workouts[:5]:
            st.markdown(f'<div class="activity"><div class="activity-icon">{html.escape(item["muscle"][:2].upper())}</div>'
                        f'<div><div class="activity-name">{html.escape(item["exercise"])}</div>'
                        f'<div class="activity-meta">{item["performed_on"]} · {item["sets"]} sets × {item["reps"]} reps · RPE {item["rpe"]:g}</div></div>'
                        f'<div class="activity-load">{item["weight_kg"]:g}<span class="muted"> kg</span></div></div>', unsafe_allow_html=True)
        if not workouts:
            st.info("Start in Workout log to add your first exercise.")
    with right:
        st.subheader("Your next move")
        progress = next((item for item in recommendations if item["action"] == "increase"), None)
        if progress or recommendations:
            coach_card(progress or recommendations[0])
        else:
            st.caption("A recommendation will appear after you log a workout.")

elif page == "Workout log":
    log_tab, history_tab, import_tab = st.tabs(["＋ Log a workout", "Training history", "Import CSV"])
    with log_tab:
        st.caption("One entry per exercise. Enter the lowest number of reps completed in any working set.")
        with st.form("workout_form", clear_on_submit=False):
            a, b = st.columns(2)
            exercise = a.text_input("Exercise", placeholder="e.g. Bench Press", max_chars=60)
            muscle = b.selectbox("Muscle group", ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"])
            performed_on = a.date_input("Workout date", value=date.today(), max_value=date.today())
            weight = b.number_input("Total load (kg)", min_value=0.5, max_value=600.0, value=40.0, step=2.5)
            c, d, e = st.columns(3)
            sets = c.number_input("Working sets", min_value=1, max_value=12, value=3)
            reps = d.number_input("Minimum completed reps / set", min_value=1, max_value=50, value=8)
            target = e.number_input("Target reps / set", min_value=1, max_value=50, value=8)
            rpe = st.slider("Effort · RPE (1 = very easy, 10 = maximum effort)", min_value=1.0, max_value=10.0, value=7.0, step=0.5)
            notes = st.text_area("Session notes", placeholder="How did it feel?", max_chars=300)
            submitted = st.form_submit_button("Save workout ↗", type="primary", disabled=status["blocked"], use_container_width=True)
        if submitted:
            if len(exercise.strip()) < 2:
                st.error("Enter an exercise name with at least two characters.")
            else:
                try:
                    client.request("POST", "/workouts", json=dict(exercise=exercise, muscle=muscle, performed_on=performed_on.isoformat(),
                                   weight_kg=weight, sets=sets, reps=reps, target_reps=target, rpe=rpe, notes=notes))
                    st.session_state["saved"] = True
                    st.rerun()
                except ApiError as error:
                    st.error(str(error))
        if st.session_state.pop("saved", False):
            st.success("Workout saved. Your progress and recommendations are up to date.")
    with history_tab:
        if st.session_state.pop("edited", False):
            st.success("Entry updated. Your charts and training plan have been recalculated.")
        selected_muscle = st.selectbox("Filter by muscle", ["All", "Chest", "Back", "Legs", "Shoulders", "Arms", "Core"])
        search = st.text_input("Find an exercise", placeholder="Search your history")
        try:
            filtered = client.request("GET", "/workouts", params={"muscle": selected_muscle} if selected_muscle != "All" else {})
            filtered = [item for item in filtered if search.casefold() in item["exercise"].casefold()]
            if filtered:
                history = pd.DataFrame(filtered)
                st.dataframe(history[["id", "performed_on", "exercise", "muscle", "sets", "reps", "weight_kg", "rpe", "notes"]], hide_index=True, use_container_width=True)
                st.download_button("↓ Export this view as CSV", history.to_csv(index=False), "gympulse-workouts.csv", "text/csv")
                choices = {f'#{row["id"]} · {row["performed_on"]} · {row["exercise"]}': row["id"] for row in filtered}
                with st.expander("Edit an entry"):
                    selected = st.selectbox("Edit entry", list(choices), key="edit_entry")
                    row = next(item for item in filtered if item["id"] == choices[selected])
                    muscles = ["Chest", "Back", "Legs", "Shoulders", "Arms", "Core"]
                    with st.form(f'edit_workout_{row["id"]}'):
                        a, b = st.columns(2)
                        edited_exercise = a.text_input("Exercise name", value=row["exercise"], max_chars=60)
                        edited_muscle = b.selectbox("Target muscle", muscles, index=muscles.index(row["muscle"]))
                        edited_date = a.date_input("Entry date", value=date.fromisoformat(row["performed_on"]), max_value=date.today())
                        edited_weight = b.number_input("Recorded load (kg)", min_value=0.0, max_value=600.0, value=float(row["weight_kg"]), step=0.5)
                        a, b, c = st.columns(3)
                        edited_sets = a.number_input("Recorded sets", min_value=1, max_value=12, value=int(row["sets"]))
                        edited_reps = b.number_input("Recorded minimum reps", min_value=1, max_value=50, value=int(row["reps"]))
                        edited_target = c.number_input("Recorded rep target", min_value=1, max_value=50, value=int(row["target_reps"]))
                        edited_rpe = st.number_input("Recorded RPE", min_value=1.0, max_value=10.0, value=float(row["rpe"]), step=0.1)
                        edited_notes = st.text_area("Entry notes", value=row["notes"], max_chars=300)
                        save_edit = st.form_submit_button("Save changes", disabled=status["blocked"], type="primary")
                    if save_edit:
                        client.request("PUT", f'/workouts/{row["id"]}', json=dict(
                            exercise=edited_exercise, muscle=edited_muscle, performed_on=edited_date.isoformat(),
                            sets=edited_sets, reps=edited_reps, target_reps=edited_target,
                            weight_kg=edited_weight, rpe=edited_rpe, notes=edited_notes,
                        ))
                        st.session_state["edited"] = True
                        st.rerun()
                with st.expander("Remove an incorrect entry"):
                    choice = st.selectbox("Entry", list(choices))
                    confirmed = st.checkbox("I want to permanently remove this entry")
                    if st.button("Delete entry", disabled=not confirmed or status["blocked"]):
                        client.request("DELETE", f"/workouts/{choices[choice]}")
                        st.rerun()
            else:
                st.info("No workouts match those filters.")
        except ApiError as error:
            st.error(str(error))

    with import_tab:
        st.subheader("Bring your training history")
        st.caption("Upload a GymPulse export or use the template. Dates use YYYY-MM-DD and loads use kg. Up to 500 rows per file; maximum 2 MB.")
        template_path = Path(__file__).resolve().parents[1] / "data/import_template.csv"
        st.download_button("Download CSV template", template_path.read_text(encoding="utf-8"), "gympulse-import-template.csv", "text/csv")
        st.info("The whole file is validated before saving. Exact duplicates are skipped, including when you import the same file again. Imported IDs are ignored; new entries get their own IDs.")
        if message := st.session_state.pop("import_result", None):
            st.success(message)
        uploaded = st.file_uploader("Workout CSV", type=["csv"], disabled=status["blocked"])
        if uploaded is not None:
            if uploaded.size > 2_000_000:
                st.error("Choose a CSV file smaller than 2 MB.")
            else:
                try:
                    csv_text = uploaded.getvalue().decode("utf-8-sig")
                    preview = pd.read_csv(io.StringIO(csv_text), dtype=str, keep_default_na=False, nrows=5)
                    st.caption("Preview · first five rows")
                    st.dataframe(preview, hide_index=True, use_container_width=True)
                    confirmed_import = st.checkbox("Import these workout records", key="confirm_import")
                    if st.button("Import workouts", type="primary", disabled=not confirmed_import or status["blocked"]):
                        result = client.request("POST", "/imports/workouts", json={"csv_text": csv_text})
                        st.session_state["import_result"] = f'{result["created"]} entries added. {result["skipped"]} exact duplicates skipped.'
                        st.rerun()
                except UnicodeDecodeError:
                    st.error("Save the file as UTF-8 CSV, then try again.")
                except (pd.errors.ParserError, pd.errors.EmptyDataError):
                    st.error("This CSV could not be previewed. Check its column names, commas and quoted fields.")
                except ApiError as error:
                    st.error(str(error))

elif page == "Progress":
    if df.empty:
        st.info("Log your first workout to begin tracking progress.")
    else:
        exercise = st.selectbox("Choose your lift", sorted(df.exercise.unique()))
        points = df[df.exercise == exercise].sort_values(["performed_on", "id"])
        first, last, best = float(points.iloc[0].weight_kg), float(points.iloc[-1].weight_kg), float(points.weight_kg.max())
        a, b, c = st.columns(3)
        a.metric("Latest load", f"{last:g} kg", f"{last-first:+g} kg since first entry")
        b.metric("Heaviest logged load", f"{best:g} kg")
        c.metric("Exercise entries", len(points))
        st.subheader("Build your strength story")
        st.caption("Working load over time. Compare sessions with similar sets and reps.")
        fig = px.line(points, x="performed_on", y="weight_kg", markers=True, hover_data=["sets", "reps", "rpe"], color_discrete_sequence=COLORS)
        fig.update_traces(line=dict(width=3))
        fig.update_yaxes(title="Load (kg)")
        st.plotly_chart(chart_style(fig, 390), use_container_width=True)
        st.subheader("Personal records")
        st.caption("Heaviest working load logged per exercise; these are not estimated one-rep maxes.")
        records = pd.DataFrame(summary["personal_records"])
        fig = px.bar(records.sort_values("weight_kg"), x="weight_kg", y="exercise", orientation="h", color_discrete_sequence=COLORS, text_auto=True)
        fig.update_xaxes(title="Load (kg)")
        fig.update_yaxes(title=None)
        st.plotly_chart(chart_style(fig, max(300, len(records) * 48)), use_container_width=True)

else:
    st.caption("Simple, explainable progression for loaded resistance exercises. Recovery is checked before increasing weight.")
    reference = st.date_input("Plan for", value=date.today(), min_value=date.today(), max_value=date.today() + timedelta(days=30))
    if reference != date.today():
        try:
            recommendations = client.request("GET", "/recommendations", params={"as_of": reference.isoformat()})
        except ApiError as error:
            st.error(str(error))
            st.stop()
    if not recommendations:
        st.info("Log a workout first. The coach uses your latest entry for each exercise.")
    cols = st.columns(3)
    for index, item in enumerate(recommendations):
        with cols[index % 3]:
            coach_card(item)
    with st.expander("How the recommendation works"):
        st.markdown("1. **Under 2 calendar days:** recover.\n2. **14 days or longer:** restart around 90%.\n3. **RPE 9 or above:** deload around 10%.\n4. **Rep target met and RPE ≤ 7.5:** add 2.5 kg.\n5. **Otherwise:** keep the same load.")
        st.caption("Loads round to the nearest 2.5 kg, half up. This is a coursework planning heuristic, not individualized coaching. It does not assess injuries, exercise technique, or cross-exercise fatigue. Bodyweight exercises are outside its scope.")

st.markdown('<div class="footer">GYMPULSE &nbsp; / &nbsp; Built for the long game. <span style="float:right">STAY CONSISTENT ↗</span></div>', unsafe_allow_html=True)
