# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Each song has seven features: `genre`, `mood`, `energy`, `valence`, `tempo`, `danceability`, and `acousticness`. The user provides a profile with preferred values for the same features. The system scores every song against that profile, ranks them, and returns the top K matches.

---

### Algorithm Recipe

**System flow:**
1. Load all songs from `songs.csv`
2. For each song, compute a score out of 10 (see rules below)
3. Sort all songs by score, highest first
4. Return the top K songs

**Scoring rules — total = genre + mood + numerical scores**

**Genre (max 3.0 pts)**
- Exact match → 3.0
- Similar genre (e.g. pop ~ indie pop) → 1.5
- No match → 0.0

**Mood (max 2.0 pts)**
- Exact match or known alias (e.g. calm ~ chill, sad ~ mellow) → 2.0
- No match → 0.0

**Numerical features (max 5.0 pts combined)**

Each of the five numerical features uses:
```
feature_score = max(0, weight × (1 − |song_value − preferred_value| / range))
```

| Feature | Weight | Range |
|---|---|---|
| energy | 1.5 | 1.0 |
| valence | 1.0 | 1.0 |
| danceability | 0.9 | 1.0 |
| tempo | 0.8 | 120 BPM |
| acousticness | 0.8 | 1.0 |

Closer to the preferred value = higher score. `max(0, ...)` ensures scores never go negative.

---

### Potential Biases and Limitations

- **Genre over-weighting** — genre alone is worth 30% of the total score. A song with the wrong genre will rank low even if it matches every other feature closely.
- **Strict categorical matching** — mood is all-or-nothing. Songs with similar but differently-labeled moods (e.g. "focused" vs "chill") are treated as unrelated.
- **Limited feature representation** — numerical features like energy and valence are simplified proxies. They can't capture lyrics, timbre, or the full texture of a song.
- **No learning from user behavior** — the profile is static. The system does not update based on what the user skips, replays, or saves.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

- **Small catalog** — with only 20 songs, genres like blues, classical, and folk have a single entry each. Users who prefer those styles will always get cross-genre songs filling out their top results.
- **No categorical penalty** — the scoring formula rewards proximity but never penalizes a mismatch. A song with the completely wrong genre and mood can still score above 6/10 if its audio features happen to be close, which produces misleadingly confident recommendations.
- **Static user profile** — preferences are fixed at query time. The system does not learn from what the user skips, replays, or saves.
- **Energy clustering** — most catalog songs sit between 0.28 and 0.93 energy, with a mean of 0.58. Very low energy preferences (below 0.20) have no genuinely close matches, so the system returns the least-far-away option without signaling the gap.
- **Mood label gaps** — some moods a user might want (e.g. "sad", "nostalgic") have few or no matching songs in the catalog, making those preferences invisible to the ranker.

---

## Reflection

### Comparison 1 — High-Energy Pop vs. Same Profile With No Genre

When the user prefers high-energy happy pop, Sunrise City comes out on top with a score of 9.71. When the genre preference is removed and everything else stays the same, Sunrise City still ranks first — but with a score of 8.21 instead.

The ranking barely changed, but the scores below the top spot got much closer together. Gym Hero, which normally gets a bonus for being a pop song, lost that bonus and fell closer to songs from completely different genres. The system became less decisive — it still knew which song was best, but it was less sure about everything else. Removing genre did not break the results, but it quietly made the whole ranking less reliable.

---

### Comparison 2 — Happy Pop vs. Sad Pop (Mood Flip)

When the user prefers happy pop with high energy, the top results are Sunrise City, Rooftop Lights, and Gym Hero. When the mood is changed to sad and the emotional tone (valence) is lowered to reflect a sadder preference, the exact same songs still show up at the top.

This happens because none of the songs in the catalog are labeled "sad," so the mood preference never matches anything and contributes zero points to every song. The genre and energy preferences still work fine, so pop songs with high energy win regardless of whether the user wanted something happy or sad. The system has no way to tell the difference between "pop for a party" and "pop after a bad day" when the right emotional label is missing from the catalog.

---

### Comparison 3 — Lo-fi Study vs. Ultra-Quiet Ambient

A lo-fi user gets Library Rain as their top result with a score of 9.78. An ambient user gets Spacewalk Thoughts at 9.20. Both top results feel right — the system correctly identified a different best match for each profile.

The difference shows up in results #2 and #3. The lo-fi user gets Midnight Coding and Focus Flow — both real lo-fi songs. The ambient user gets Library Rain and Midnight Coding — which are lo-fi songs, not ambient ones. This happens because there is only one ambient song in the catalog. Once Spacewalk Thoughts is taken, the system has nothing else to offer, so it reaches for lo-fi as the closest similar style. The recommendations look fine on the surface, but the ambient user is quietly getting lo-fi songs because the catalog ran out of ambient options.

---

### Comparison 4 — Sad Energetic Rock vs. Lo-fi Study

The rock user gets Storm Runner at 7.43. The lo-fi user gets Library Rain at 9.78. The lo-fi result looks much more confident, and it is — but not just because the lo-fi song is a better match. It is also because there are three lo-fi songs in the catalog, giving the system real options. There is only one rock song, and it has the wrong mood (intense instead of sad), so the mood part of the score contributes nothing.

Storm Runner still ranks first because genre matched and energy was close. But the score of 7.43 gives no indication that the user's sad mood preference went completely unmet. From the outside, a 7.43 looks like a solid recommendation. In reality, it is the system's best guess with very little to work with.

