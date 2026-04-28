import json
from pathlib import Path
import anthropic

try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs

_DEFAULT_SONGS_PATH = Path(__file__).parent.parent / "data" / "songs.csv"

client = anthropic.Anthropic()

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
                    "Music genre. One of: lofi, pop, rock, ambient, jazz, indie pop, "
                    "synthwave, electronic, folk, r&b, blues, hip-hop, classical, country."
                ),
            },
            "mood": {
                "type": "string",
                "description": "Emotional mood. One of: happy, chill, sad, intense, romantic, melancholy.",
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


def reflect_on_recommendations(
    user_input: str,
    profile: dict,
    recommendations: list,
) -> str:
    """
    Stage 3: LLM reflection on recommendation quality.

    Claude reasons about how well the extracted profile captured the user's intent,
    whether the top songs are a good match, and offers one concrete improvement.
    """
    rec_lines = "\n".join(
        f"{i + 1}. \"{r[0]['title']}\" by {r[0]['artist']} "
        f"[genre: {r[0].get('genre', '?')}, mood: {r[0].get('mood', '?')}, "
        f"energy: {r[0].get('energy', 0):.2f}] — score: {r[1]:.2f}"
        for i, r in enumerate(recommendations)
    )

    prompt = (
        f'User request: "{user_input}"\n\n'
        f"Extracted preference profile:\n{json.dumps(profile, indent=2)}\n\n"
        f"Top recommendations:\n{rec_lines}\n\n"
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
    Full agentic pipeline: natural language → profile → recommendations → LLM reflection.

    Args:
        user_input:  Free-text description of what the user wants to listen to.
        songs_path:  Path to songs CSV. Defaults to data/songs.csv.
        k:           Number of recommendations to return.
        mode:        Scoring mode — balanced | genre_first | mood_first | energy_focused.

    Returns a dict with keys: user_input, profile, recommendations, reflection.
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

    print("\nStage 3: LLM reflection on recommendation quality...")
    reflection = reflect_on_recommendations(user_input, profile, recs)
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
        "reflection": reflection,
    }


if __name__ == "__main__":
    example = "I want something relaxing to study to late at night, maybe acoustic or lo-fi vibes"
    result = run_agent(example)
    print("\n=== Final Result ===")
    print(json.dumps(result, indent=2))
