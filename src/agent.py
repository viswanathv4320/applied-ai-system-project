import json
import logging
from pathlib import Path
import anthropic

try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs

_DEFAULT_SONGS_PATH = Path(__file__).parent.parent / "data" / "songs.csv"

client = anthropic.Anthropic()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
)
logger = logging.getLogger(__name__)

# Tool definition for Stage 1 profile extraction.
# Fields are all optional — Claude only populates what it can confidently infer
# from the user's description, rather than guessing missing values.
_EXTRACT_TOOL = {
    "name": "extract_music_profile",
    "description": (
        "Extract music preference features from the user's description. "
        "Only include fields you can confidently infer — omit fields that are genuinely unclear."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "genre": {
                "type": "string",
                "description": (
                    "Music genre. One of: pop, indie pop, indie rock, r&b, hip-hop, "
                    "electronic, bollywood."
                ),
            },
            "mood": {
                "type": "string",
                "description": "Emotional mood. One of: happy, intense, melancholy, romantic, confident, moody, motivated.",
            },
            "energy": {
                "type": "number",
                "description": "Energy level: 0.0 = very calm, 1.0 = very energetic.",
            },
            "valence": {
                "type": "number",
                "description": "Positivity: 0.0 = dark/sad, 1.0 = bright/happy.",
            },
            "tempo_bpm": {
                "type": "integer",
                "description": "Tempo in BPM. Typical ranges: slow=60-80, medium=90-120, fast=130-160.",
            },
            "danceability": {
                "type": "number",
                "description": "How danceable: 0.0 = not danceable, 1.0 = very danceable.",
            },
            "acousticness": {
                "type": "number",
                "description": "Acoustic vs electronic: 0.0 = fully electronic, 1.0 = fully acoustic.",
            },
        },
        "required": [],
        "additionalProperties": False,
    },
}


def parse_user_intent(natural_language: str) -> dict:
    """
    Stage 1: Natural language → user_prefs dict.

    Uses tool_choice to force structured extraction. Only fields the model
    can confidently infer from the description are populated.
    """
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=(
            "You extract music preference profiles from natural language descriptions. "
            "Infer feature values from context — for example, 'late night study' implies "
            "low energy (~0.3), high acousticness (~0.7), chill mood, slow tempo. "
            "Only populate fields you can confidently infer; omit the rest."
        ),
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "extract_music_profile"},
        messages=[{"role": "user", "content": natural_language}],
    )
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    return dict(tool_use_block.input)


def get_recommendations(user_prefs: dict, songs: list, k: int = 3, mode: str = "balanced"):
    """
    Stage 2: Profile → ranked song recommendations.

    Delegates entirely to the deterministic scorer in recommender.py.
    Returns a list of (song_dict, score, explanation) tuples.
    """
    return recommend_songs(user_prefs, songs, k=k, mode=mode)


def check_guardrails(profile: dict, recommendations: list) -> list[str]:
    """
    Guardrails: fast rule-based checks that run after scoring, before LLM reflection.

    Checks for three failure modes:
      1. Low confidence  — top score below 6.0 means the best match is weak
      2. Mood gap        — user requested a mood that no top-k song matched
      3. Genre gap       — user requested a genre that no top-k song matched

    Returns a list of warning strings. Empty list means all clear.
    These warnings are passed to Stage 3 so the LLM reflection is aware of them,
    and are also printed directly so they are visible in the output.
    """
    warnings = []

    # Check 1 — low confidence
    top_score = recommendations[0][1] if recommendations else 0.0
    if top_score < 6.0:
        msg = f"Low confidence — best match scores only {top_score:.2f}/10"
        warnings.append(msg)
        logger.warning("GUARDRAIL: %s", msg)

    # Check 2 — mood gap
    user_mood = (profile.get("mood") or "").lower()
    if user_mood:
        top_moods = [r[0].get("mood", "").lower() for r in recommendations]
        if user_mood not in top_moods:
            msg = f"Mood gap — '{user_mood}' not matched in any top-{len(recommendations)} result"
            warnings.append(msg)
            logger.warning("GUARDRAIL: %s", msg)

    # Check 3 — genre gap
    user_genre = (profile.get("genre") or "").lower()
    if user_genre:
        top_genres = [r[0].get("genre", "").lower() for r in recommendations]
        if user_genre not in top_genres:
            msg = f"Genre gap — '{user_genre}' not matched in any top-{len(recommendations)} result"
            warnings.append(msg)
            logger.warning("GUARDRAIL: %s", msg)

    return warnings


def reflect_on_recommendations(
    user_input: str,
    profile: dict,
    recommendations: list,
    warnings: list[str] = None,
) -> str:
    """
    Stage 3: LLM reflection on recommendation quality.

    Claude reasons about how well the extracted profile captured the user's intent,
    whether the top songs are a good match, and offers one concrete improvement.
    Guardrail warnings are included in the prompt so Claude is aware of known issues.
    """
    rec_lines = "\n".join(
        f"{i + 1}. \"{r[0]['title']}\" by {r[0]['artist']} "
        f"[genre: {r[0].get('genre', '?')}, mood: {r[0].get('mood', '?')}, "
        f"energy: {r[0].get('energy', 0):.2f}] — score: {r[1]:.2f}"
        for i, r in enumerate(recommendations)
    )

    guardrail_section = ""
    if warnings:
        guardrail_section = (
            "\n\nGuardrail warnings already detected:\n"
            + "\n".join(f"  - {w}" for w in warnings)
            + "\nPlease factor these into your reflection.\n"
        )

    prompt = (
        f'User request: "{user_input}"\n\n'
        f"Extracted preference profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Top recommendations:\n{rec_lines}"
        f"{guardrail_section}\n\n"
        "Please reflect concisely (3-4 sentences) on: "
        "(1) how well these recommendations match the user's stated intent, "
        "(2) any notable gaps or mismatches in the profile extraction, and "
        "(3) one concrete change to the profile or scoring mode that would improve the match."
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return next(b.text for b in response.content if b.type == "text")


def run_agent(
    user_input: str,
    songs_path: str = None,
    k: int = 3,
    mode: str = "balanced",
) -> dict:
    """
    Full agentic pipeline: natural language → profile → recommendations → guardrails → LLM reflection.

    Args:
        user_input:  Free-text description of what the user wants to listen to.
        songs_path:  Path to songs CSV. Defaults to data/songs.csv.
        k:           Number of recommendations to return.
        mode:        Scoring mode — balanced | genre_first | mood_first | energy_focused.

    Returns a dict with keys: user_input, profile, recommendations, warnings, reflection.
    """
    if songs_path is None:
        songs_path = str(_DEFAULT_SONGS_PATH)

    songs = load_songs(songs_path)

    print("Stage 1: Extracting preference profile from natural language...")
    profile = parse_user_intent(user_input)
    print(f"  Profile: {json.dumps(profile, indent=2)}")

    print(f"\nStage 2: Scoring {len(songs)} songs (mode={mode})...")
    recs = get_recommendations(profile, songs, k=k, mode=mode)
    for i, (song, score, _) in enumerate(recs):
        print(f"  {i + 1}. {song['title']} by {song['artist']} — score: {score:.2f}")

    print("\nGuardrails: Checking recommendation quality...")
    warnings = check_guardrails(profile, recs)
    if warnings:
        for w in warnings:
            print(f"  ⚠️  {w}")
    else:
        print("  ✓ No issues detected")

    print("\nStage 3: LLM reflection on recommendation quality...")
    reflection = reflect_on_recommendations(user_input, profile, recs, warnings)
    print(f"\n  {reflection}")

    return {
        "user_input": user_input,
        "profile": profile,
        "recommendations": [
            {
                "title": r[0]["title"],
                "artist": r[0]["artist"],
                "genre": r[0].get("genre"),
                "mood": r[0].get("mood"),
                "score": r[1],
                "explanation": r[2],
            }
            for r in recs
        ],
        "warnings": warnings,
        "reflection": reflection,
    }


if __name__ == "__main__":
    example = "I want something relaxing to study to late at night, maybe acoustic or lo-fi vibes"
    result = run_agent(example)
    print("\n=== Final Result ===")
    print(json.dumps(result, indent=2))