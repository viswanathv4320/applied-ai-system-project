from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs from a CSV file and return them as a list of dicts with typed values."""
    float_fields = {"energy", "valence", "danceability", "acousticness"}
    int_fields = {"tempo", "tempo_bpm"}

    songs = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            song = {}

            for key, value in row.items():
                if value is None:
                    song[key] = None
                    continue

                value = value.strip()

                # Handle empty values
                if value == "":
                    song[key] = None
                    continue

                if key in float_fields:
                    song[key] = float(value)

                elif key in int_fields:
                    song[key] = int(value)

                else:
                    # Normalize categorical fields
                    song[key] = value.lower()

            songs.append(song)

    return songs

SIMILAR_GENRES = {
    "pop":      {"indie pop", "synthwave"},
    "indie pop":{"pop"},
    "rock":     {"indie pop"},
    "lofi":     {"ambient"},
    "ambient":  {"lofi"},
    "jazz":     {"lofi"},
    "synthwave":{"pop", "electronic"},
    "electronic":{"synthwave"},
}

MOOD_ALIASES = {
    "calm":      "chill",
    "mellow":    "sad",
    "sad":       "mellow",
    "focused":   "chill",
    "motivated": "intense",
}

NUMERICAL_WEIGHTS = {
    "energy":       (1.5, 1.0),
    "valence":      (1.0, 1.0),
    "danceability": (0.9, 1.0),
    "acousticness": (0.8, 1.0),
    "tempo_bpm":    (0.8, 120),
    "tempo":        (0.8, 120),
}

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score a song against user preferences (max 10.0) and return (score, reason strings)."""
    score = 0.0
    reasons = []

    # --- Genre (max 3.0) ---
    user_genre = (user_prefs.get("genre") or "").lower()
    song_genre = (song.get("genre") or "").lower()

    if user_genre and song_genre:
        if song_genre == user_genre:
            score += 3.0
            reasons.append(f"genre match: {song_genre} (+3.0)")
        elif song_genre in SIMILAR_GENRES.get(user_genre, set()):
            score += 1.5
            reasons.append(f"similar genre: {song_genre} ~ {user_genre} (+1.5)")

    # --- Mood (max 2.0) ---
    user_mood = (user_prefs.get("mood") or "").lower()
    song_mood = (song.get("mood") or "").lower()

    if user_mood and song_mood:
        resolved = MOOD_ALIASES.get(user_mood, user_mood)
        if song_mood == user_mood or song_mood == resolved:
            score += 2.0
            reasons.append(f"mood match: {song_mood} (+2.0)")

    # --- Numerical features (max 5.0 combined) ---
    for feature, (weight, range_) in NUMERICAL_WEIGHTS.items():
        pref_value = user_prefs.get(feature)
        song_value = song.get(feature)

        # Only one of tempo / tempo_bpm will be in the song dict
        if song_value is None and feature == "tempo_bpm":
            song_value = song.get("tempo")
        if song_value is None and feature == "tempo":
            song_value = song.get("tempo_bpm")

        if pref_value is None or song_value is None:
            continue

        feature_score = max(0.0, weight * (1 - abs(song_value - pref_value) / range_))
        score += feature_score
        reasons.append(f"{feature}: {song_value} vs {pref_value} → +{feature_score:.2f}")

    return round(score, 2), reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score all songs against user preferences and return the top k as (song, score, explanation) tuples."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = ", ".join(reasons) if reasons else "no matching features"
        scored.append((song, score, explanation))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
