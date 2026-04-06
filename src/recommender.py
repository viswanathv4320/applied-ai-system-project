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
    popularity: int = 50
    release_decade: str = ""
    instrumentalness: float = 0.0
    vocal_presence: float = 0.5
    complexity: float = 0.5

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
    float_fields = {"energy", "valence", "danceability", "acousticness",
                    "instrumentalness", "vocal_presence", "complexity"}
    int_fields = {"tempo", "tempo_bpm", "popularity"}

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

# Used to award partial credit for nearby release eras (e.g. 2010s ≈ 2020s)
DECADE_ORDER = ["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]

# ---------------------------------------------------------------------------
# Scoring modes — Strategy pattern via config dicts.
# Each mode defines the weights for categorical features (genre, mood, decade)
# and overrides for numerical features.  All modes are calibrated to max ~10.0.
#
# Structure of each mode dict:
#   genre_exact    — points for an exact genre match
#   genre_similar  — points for a similar-genre match (half of genre_exact)
#   mood           — points for a mood match (exact or alias)
#   decade_exact   — points for matching release decade exactly
#   decade_adjacent— points for being one decade away
#   numerical      — {feature: (weight, range)} — same shape as old NUMERICAL_WEIGHTS
# ---------------------------------------------------------------------------

SCORING_MODES: Dict[str, Dict] = {

    # ---- balanced (default) ------------------------------------------------
    # Genre and mood share influence roughly equally with numericals.
    # Max: 1.5 + 2.0 + 0.4 + 6.1 = 10.0
    "balanced": {
        "genre_exact":     1.5,
        "genre_similar":   0.75,
        "mood":            2.0,
        "decade_exact":    0.4,
        "decade_adjacent": 0.2,
        "numerical": {
            "energy":           (2.0, 1.0),
            "valence":          (1.0, 1.0),
            "danceability":     (0.7, 1.0),
            "acousticness":     (0.6, 1.0),
            "tempo_bpm":        (0.8, 120),
            "tempo":            (0.8, 120),
            "instrumentalness": (0.3, 1.0),
            "vocal_presence":   (0.3, 1.0),
            "complexity":       (0.2, 1.0),
            "popularity":       (0.2, 100),
        },
    },

    # ---- genre_first -------------------------------------------------------
    # Genre is the strongest single signal; numericals are reduced.
    # Use when the user's genre preference is very deliberate.
    # Max: 3.5 + 1.5 + 0.3 + 4.7 = 10.0
    "genre_first": {
        "genre_exact":     3.5,
        "genre_similar":   1.75,
        "mood":            1.5,
        "decade_exact":    0.3,
        "decade_adjacent": 0.15,
        "numerical": {
            "energy":           (1.5, 1.0),
            "valence":          (0.8, 1.0),
            "danceability":     (0.6, 1.0),
            "acousticness":     (0.5, 1.0),
            "tempo_bpm":        (0.7, 120),
            "tempo":            (0.7, 120),
            "instrumentalness": (0.2, 1.0),
            "vocal_presence":   (0.2, 1.0),
            "complexity":       (0.1, 1.0),
            "popularity":       (0.1, 100),
        },
    },

    # ---- mood_first --------------------------------------------------------
    # Mood and valence dominate; genre is a light filter only.
    # Use when emotional tone matters more than musical style.
    # Max: 1.0 + 3.5 + 0.3 + 5.2 = 10.0
    "mood_first": {
        "genre_exact":     1.0,
        "genre_similar":   0.5,
        "mood":            3.5,
        "decade_exact":    0.3,
        "decade_adjacent": 0.15,
        "numerical": {
            "energy":           (1.8, 1.0),
            "valence":          (1.2, 1.0),   # valence boosted — tracks emotional positivity
            "danceability":     (0.6, 1.0),
            "acousticness":     (0.4, 1.0),
            "tempo_bpm":        (0.6, 120),
            "tempo":            (0.6, 120),
            "instrumentalness": (0.2, 1.0),
            "vocal_presence":   (0.2, 1.0),
            "complexity":       (0.1, 1.0),
            "popularity":       (0.1, 100),
        },
    },

    # ---- energy_focused ----------------------------------------------------
    # Energy drives everything; genre and mood are minor bonuses.
    # Use for activity-based playlists (workout, focus, sleep).
    # Max: 1.0 + 1.2 + 0.2 + 7.6 = 10.0
    "energy_focused": {
        "genre_exact":     1.0,
        "genre_similar":   0.5,
        "mood":            1.2,
        "decade_exact":    0.2,
        "decade_adjacent": 0.1,
        "numerical": {
            "energy":           (4.0, 1.0),   # heavily dominant
            "valence":          (0.9, 1.0),
            "danceability":     (0.7, 1.0),
            "acousticness":     (0.5, 1.0),
            "tempo_bpm":        (0.8, 120),
            "tempo":            (0.8, 120),
            "instrumentalness": (0.3, 1.0),
            "vocal_presence":   (0.2, 1.0),
            "complexity":       (0.1, 1.0),
            "popularity":       (0.1, 100),
        },
    },
}

# Keep NUMERICAL_WEIGHTS as a convenience alias for the default mode.
NUMERICAL_WEIGHTS = SCORING_MODES["balanced"]["numerical"]

def score_song(user_prefs: Dict, song: Dict, mode: str = "balanced") -> Tuple[float, List[str]]:
    """Score a song against user preferences using the given scoring mode (max ~10.0)."""
    cfg = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
    score = 0.0
    reasons = []

    # --- Genre ---
    user_genre = (user_prefs.get("genre") or "").lower()
    song_genre  = (song.get("genre") or "").lower()

    if user_genre and song_genre:
        if song_genre == user_genre:
            pts = cfg["genre_exact"]
            score += pts
            reasons.append(f"genre match: {song_genre} (+{pts:.2f})")
        elif song_genre in SIMILAR_GENRES.get(user_genre, set()):
            pts = cfg["genre_similar"]
            score += pts
            reasons.append(f"similar genre: {song_genre} ~ {user_genre} (+{pts:.2f})")

    # --- Mood ---
    user_mood = (user_prefs.get("mood") or "").lower()
    song_mood  = (song.get("mood") or "").lower()

    if user_mood and song_mood:
        resolved = MOOD_ALIASES.get(user_mood, user_mood)
        if song_mood == user_mood or song_mood == resolved:
            pts = cfg["mood"]
            score += pts
            reasons.append(f"mood match: {song_mood} (+{pts:.2f})")

    # --- Release Decade ---
    user_decade = (user_prefs.get("release_decade") or "").lower()
    song_decade  = (song.get("release_decade") or "").lower()

    if user_decade and song_decade and user_decade in DECADE_ORDER and song_decade in DECADE_ORDER:
        gap = abs(DECADE_ORDER.index(song_decade) - DECADE_ORDER.index(user_decade))
        if gap == 0:
            pts = cfg["decade_exact"]
            score += pts
            reasons.append(f"decade match: {song_decade} (+{pts:.2f})")
        elif gap == 1:
            pts = cfg["decade_adjacent"]
            score += pts
            reasons.append(f"adjacent decade: {song_decade} ~ {user_decade} (+{pts:.2f})")

    # --- Numerical features ---
    for feature, (weight, range_) in cfg["numerical"].items():
        pref_value = user_prefs.get(feature)
        song_value = song.get(feature)

        # Only one of tempo / tempo_bpm will be present in the song dict
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


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: str = "balanced",
) -> List[Tuple[Dict, float, str]]:
    """Score all songs and return the top k as (song, score, explanation) tuples."""
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, mode=mode)
        explanation = ", ".join(reasons) if reasons else "no matching features"
        scored.append((song, score, explanation))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
