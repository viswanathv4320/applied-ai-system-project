import os
import streamlit as st

from src.agent import run_agent, check_guardrails
from src.recommender import load_songs, recommend_songs


st.set_page_config(
    page_title="AI Music Recommender",
    page_icon="🎵",
    layout="wide",
)


st.markdown(
    """
    <style>
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 0rem;
    }

    .subtitle {
        color: #6b7280;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }

    .song-card {
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 1.4rem;
        margin-bottom: 1rem;
        background-color: #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .song-title {
        font-size: 1.5rem;
        font-weight: 750;
        margin-bottom: 0.2rem;
    }

    .song-meta {
        color: #6b7280;
        font-size: 0.95rem;
        margin-bottom: 0.8rem;
    }

    .score-box {
        text-align: center;
        font-size: 2rem;
        font-weight: 800;
        color: #ff4b4b;
    }

    .small-label {
        color: #6b7280;
        font-size: 0.85rem;
        font-weight: 600;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_demo_profile(user_input: str) -> dict:
    text = user_input.lower()

    if "dance" in text or "party" in text or "high energy" in text:
        return {
            "genre": "electronic",
            "mood": "happy",
            "energy": 0.9,
            "valence": 0.8,
            "tempo_bpm": 130,
            "danceability": 0.95,
            "acousticness": 0.1,
        }

    if "bollywood" in text or "romantic" in text:
        return {
            "genre": "bollywood",
            "mood": "romantic",
            "energy": 0.4,
            "valence": 0.7,
            "tempo_bpm": 90,
            "danceability": 0.45,
            "acousticness": 0.6,
        }

    if "study" in text or "relax" in text or "late night" in text or "sad" in text:
        return {
            "mood": "melancholy",
            "energy": 0.2,
            "valence": 0.1,
            "tempo_bpm": 65,
            "danceability": 0.2,
            "acousticness": 0.85,
        }

    return {
        "mood": "moody",
        "energy": 0.45,
        "valence": 0.45,
        "tempo_bpm": 90,
        "danceability": 0.5,
        "acousticness": 0.5,
    }


def run_demo_agent(user_input: str, k: int, mode: str) -> dict:
    songs = load_songs("data/songs.csv")
    profile = get_demo_profile(user_input)

    recs = recommend_songs(profile, songs, k=k, mode=mode)
    warnings = check_guardrails(profile, recs)

    return {
        "user_input": user_input,
        "profile": profile,
        "recommendations": [
            {
                "title": song["title"],
                "artist": song["artist"],
                "genre": song.get("genre"),
                "mood": song.get("mood"),
                "score": score,
                "explanation": explanation,
                "energy": song.get("energy"),
                "valence": song.get("valence"),
                "danceability": song.get("danceability"),
                "acousticness": song.get("acousticness"),
            }
            for song, score, explanation in recs
        ],
        "warnings": warnings,
        "reflection": (
            "Demo mode used a rule-based profile extractor instead of Claude. "
            "The deterministic scoring engine and guardrails still ran on the real song catalog. "
            "This lets the app work even when API credits or billing are unavailable."
        ),
    }


def format_feature_name(name: str) -> str:
    return name.replace("_", " ").title()


def show_profile(profile: dict):
    st.subheader("Extracted Preference Profile")

    cols = st.columns(4)

    for i, (key, value) in enumerate(profile.items()):
        with cols[i % 4]:
            st.metric(format_feature_name(key), value)

    numeric_features = [
        "energy",
        "valence",
        "danceability",
        "acousticness",
    ]

    st.write("Profile shape")

    for feature in numeric_features:
        if feature in profile:
            st.caption(format_feature_name(feature))
            st.progress(float(profile[feature]))


def confidence_label(score: float) -> tuple[str, str]:
    if score >= 7.0:
        return "High confidence match", "success"
    if score >= 5.5:
        return "Moderate confidence match", "warning"
    return "Low confidence match", "error"


def show_recommendations(result: dict, show_reasons: bool):
    st.subheader("Recommendations")

    top_score = result["recommendations"][0]["score"]
    label, level = confidence_label(top_score)

    if level == "success":
        st.success(label)
    elif level == "warning":
        st.warning(label)
    else:
        st.error(label)

    for idx, rec in enumerate(result["recommendations"], start=1):
        with st.container():
            st.markdown('<div class="song-card">', unsafe_allow_html=True)

            left, right = st.columns([5, 1])

            with left:
                title = str(rec["title"]).title()
                artist = str(rec["artist"]).title()
                genre = str(rec.get("genre", "?")).title()
                mood = str(rec.get("mood", "?")).title()

                st.markdown(
                    f'<div class="song-title">{idx}. {title}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="song-meta">{artist} • {genre} • {mood}</div>',
                    unsafe_allow_html=True,
                )

                feature_cols = st.columns(4)

                feature_map = {
                    "energy": "Energy",
                    "valence": "Valence",
                    "danceability": "Danceability",
                    "acousticness": "Acousticness",
                }

                for j, (key, label) in enumerate(feature_map.items()):
                    value = rec.get(key)
                    if value is not None:
                        with feature_cols[j]:
                            st.caption(label)
                            st.progress(float(value))
                            st.write(f"{float(value):.2f}")

            with right:
                st.markdown(
                    f"""
                    <div class="small-label">Score</div>
                    <div class="score-box">{rec["score"]:.2f}</div>
                    <div class="small-label">out of 10</div>
                    """,
                    unsafe_allow_html=True,
                )

            if show_reasons:
                with st.expander("Technical scoring details"):
                    reasons = rec["explanation"].split(", ")
                    for reason in reasons:
                        st.write(f"• {reason}")

            st.markdown("</div>", unsafe_allow_html=True)


def show_guardrails(result: dict):
    st.subheader("Guardrails")

    if result["warnings"]:
        for warning in result["warnings"]:
            st.warning(warning)
    else:
        st.success("No major recommendation issues detected.")


def show_reflection(result: dict):
    st.subheader("AI Reflection")

    with st.expander("Why these recommendations?", expanded=True):
        st.write(result["reflection"])


with st.sidebar:
    st.title("Controls")

    mode = st.selectbox(
        "Scoring mode",
        ["balanced", "genre_first", "mood_first", "energy_focused"],
    )

    k = st.slider("Number of recommendations", 3, 10, 4)

    demo_mode = st.toggle(
        "Demo mode",
        value=True,
        help="Runs without Claude API. Uses a rule-based profile extractor.",
    )

    st.divider()

    st.subheader("Display options")

    show_extracted_profile = st.checkbox("Show extracted profile", value=True)
    show_reasons = st.checkbox("Show technical scoring details", value=False)
    show_guardrail_section = st.checkbox("Show guardrails", value=True)
    show_ai_reflection = st.checkbox("Show AI reflection", value=True)

    st.divider()

    st.subheader("Pipeline")

    st.caption("1. Parse natural language request")
    st.caption("2. Extract music preference profile")
    st.caption("3. Score catalog deterministically")
    st.caption("4. Check guardrails")
    st.caption("5. Reflect on recommendation quality")

    st.divider()

    st.subheader("System status")

    if demo_mode:
        st.info("Demo mode is ON. Claude API will not be called.")
    elif os.getenv("ANTHROPIC_API_KEY"):
        st.success("Anthropic API key detected.")
    else:
        st.error("Missing ANTHROPIC_API_KEY.")


st.markdown('<div class="main-title">🎵 AI Music Recommender</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Natural language music recommendations with deterministic scoring, guardrails, and AI reflection.</div>',
    unsafe_allow_html=True,
)

examples = [
    "something sad and acoustic for a late night",
    "high energy dance music",
    "romantic bollywood songs",
    "relaxing music to study late at night",
]

query_col, button_col = st.columns([5, 1])

with query_col:
    user_input = st.text_input(
        "What do you want to listen to?",
        placeholder="Example: something sad and acoustic for a late night",
    )

with button_col:
    st.write("")
    st.write("")
    recommend_clicked = st.button("Recommend", type="primary", use_container_width=True)

st.write("Try an example:")

example_cols = st.columns(len(examples))

for i, example in enumerate(examples):
    with example_cols[i]:
        if st.button(example, use_container_width=True):
            st.session_state["selected_example"] = example

if "selected_example" in st.session_state:
    user_input = st.session_state["selected_example"]
    st.info(f'Selected example: "{user_input}"')

if recommend_clicked:
    if not user_input.strip():
        st.warning("Please enter a music request.")
        st.stop()

    with st.spinner("Running recommendation pipeline..."):
        try:
            if demo_mode:
                result = run_demo_agent(user_input, k=k, mode=mode)
            else:
                result = run_agent(user_input, k=k, mode=mode)

        except Exception as exc:
            st.error("The recommendation pipeline failed.")
            st.exception(exc)
            st.stop()

    st.divider()

    if show_extracted_profile:
        show_profile(result["profile"])
        st.divider()

    show_recommendations(result, show_reasons)

    st.divider()

    if show_guardrail_section:
        show_guardrails(result)
        st.divider()

    if show_ai_reflection:
        show_reflection(result)