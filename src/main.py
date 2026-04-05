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


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # Starter example profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print("\n" + "=" * 40)
    print("  Top Recommendations")
    print("=" * 40)

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

        print("   " + "-" * 34)


if __name__ == "__main__":
    main()
