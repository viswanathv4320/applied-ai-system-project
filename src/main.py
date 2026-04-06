"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import re
from recommender import load_songs, recommend_songs

# Change this to switch the scoring strategy for all profiles.
# Options: "balanced" | "genre_first" | "mood_first" | "energy_focused"
SCORING_MODE = "balanced"

_FEATURE_LABELS = {
    "energy": "Energy",
    "valence": "Valence",
    "danceability": "Danceability",
    "acousticness": "Acousticness",
    "tempo_bpm": "Tempo",
    "tempo": "Tempo",
}

def _format_reason(raw: str) -> str:
    """Reformat a raw score_song reason string into consistent display text."""
    raw = raw.strip()

    # Categorical: "genre match: pop (+3.0)" / "similar genre: indie pop ~ pop (+1.5)" / "mood match: happy (+2.0)"
    cat = re.match(r"(genre match|similar genre|mood match):.+?(\(\+[\d.]+\))", raw)
    if cat:
        labels = {"genre match": "Genre match", "similar genre": "Similar genre", "mood match": "Mood match"}
        return f"{labels[cat.group(1)]} {cat.group(2)}"

    # Numerical: "energy: 0.82 vs 0.8 → +1.47"
    num = re.match(r"(\w+):\s*([\d.]+)\s*vs\s*([\d.]+)\s*→\s*\+([\d.]+)", raw)
    if num:
        feature, song_val, pref_val, pts = num.group(1), float(num.group(2)), float(num.group(3)), float(num.group(4))
        label = _FEATURE_LABELS.get(feature, feature.replace("_", " ").capitalize())
        if feature in ("tempo_bpm", "tempo"):
            return f"{label} ({int(song_val)} vs {int(pref_val)} BPM → +{pts:.2f})"
        return f"{label} close ({song_val:.2f} vs {pref_val:.2f} → +{pts:.2f})"

    # Fallback
    label, _, detail = raw.partition(":")
    return f"{label.strip().capitalize()}: {detail.strip()}" if detail else raw.capitalize()


TEST_PROFILES = [
    {
        "label": "High-Energy Pop",
        "prefs": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.85,
            "valence": 0.80,
            "tempo_bpm": 125,
            "danceability": 0.85,
            "acousticness": 0.10,
        },
    },
    {
        "label": "Late-Night Lo-fi Study",
        "prefs": {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.38,
            "valence": 0.58,
            "tempo_bpm": 78,
            "danceability": 0.60,
            "acousticness": 0.80,
        },
    },
    {
        "label": "Edge Case: Sad but Energetic Rock",
        "prefs": {
            "genre": "rock",
            "mood": "sad",
            "energy": 0.88,
            "valence": 0.20,
            "tempo_bpm": 140,
            "danceability": 0.50,
            "acousticness": 0.12,
        },
    },
    {
        "label": "Extreme: Ultra-Quiet Ambient",
        "prefs": {
            "genre": "ambient",
            "mood": "chill",
            "energy": 0.10,
            "valence": 0.60,
            "tempo_bpm": 62,
            "danceability": 0.25,
            "acousticness": 0.98,
        },
    },
    {
        "label": "Edge Case: Genre Not in Catalog",
        "prefs": {
            "genre": "classical",
            "mood": "calm",
            "energy": 0.20,
            "valence": 0.65,
            "tempo_bpm": 70,
            "danceability": 0.22,
            "acousticness": 0.95,
        },
    },
    # --- Experiment profiles ---
    {
        "label": "Baseline Pop",
        "prefs": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.85,
            "valence": 0.80,
            "tempo_bpm": 125,
            "danceability": 0.85,
            "acousticness": 0.10,
        },
    },
    {
        "label": "No Genre",
        "prefs": {
            # genre omitted — genre score will be 0 for every song
            "mood": "happy",
            "energy": 0.85,
            "valence": 0.80,
            "tempo_bpm": 125,
            "danceability": 0.85,
            "acousticness": 0.10,
        },
    },
    {
        "label": "Lower Energy",
        "prefs": {
            "genre": "pop",
            "mood": "happy",
            "energy": 0.50,  # dropped from 0.85 — tests energy sensitivity
            "valence": 0.80,
            "tempo_bpm": 125,
            "danceability": 0.85,
            "acousticness": 0.10,
        },
    },
    {
        "label": "Mood Flip",
        "prefs": {
            "genre": "pop",
            "mood": "sad",   # no catalog song has mood=sad — mood score always 0
            "energy": 0.85,
            "valence": 0.20,
            "tempo_bpm": 125,
            "danceability": 0.85,
            "acousticness": 0.10,
        },
    },
]


def _print_recommendations(recommendations: list, label: str, mode: str = "balanced") -> None:
    print("\n" + "=" * 44)
    print(f"  Profile : {label}")
    print(f"  Mode    : {mode}")
    print("=" * 44)

    for i, (song, score, explanation) in enumerate(recommendations, start=1):
        title  = song.get("title", "Unknown").title()
        artist = song.get("artist", "Unknown Artist").title()

        print(f"\n{i}. {title}")
        print(f"   Artist : {artist}")
        print(f"   Score  : {score:.2f} / 10")
        print(f"   Why    :")

        reasons = [r.strip() for r in explanation.split(", ") if r.strip()]
        for reason in reasons[:4]:
            print(f"     • {_format_reason(reason)}")

        print("   " + "-" * 36)


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    for profile in TEST_PROFILES:
        recommendations = recommend_songs(profile["prefs"], songs, k=3, mode=SCORING_MODE)
        _print_recommendations(recommendations, profile["label"], mode=SCORING_MODE)


if __name__ == "__main__":
    main()
