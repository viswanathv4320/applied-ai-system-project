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

See the [Potential Biases and Limitations](#potential-biases-and-limitations) section above for a full breakdown. You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this


---

## 7. `model_card_template.md`

Combines reflection and model card framing from the Module 3 guidance. :contentReference[oaicite:2]{index=2}  

```markdown
# 🎧 Model Card - Music Recommender Simulation

## 1. Model Name

Give your recommender a name, for example:

> VibeFinder 1.0

---

## 2. Intended Use

- What is this system trying to do
- Who is it for

Example:

> This model suggests 3 to 5 songs from a small catalog based on a user's preferred genre, mood, and energy level. It is for classroom exploration only, not for real users.

---

## 3. How It Works (Short Explanation)

Describe your scoring logic in plain language.

- What features of each song does it consider
- What information about the user does it use
- How does it turn those into a number

Try to avoid code in this section, treat it like an explanation to a non programmer.

---

## 4. Data

Describe your dataset.

- How many songs are in `data/songs.csv`
- Did you add or remove any songs
- What kinds of genres or moods are represented
- Whose taste does this data mostly reflect

---

## 5. Strengths

Where does your recommender work well

You can think about:
- Situations where the top results "felt right"
- Particular user profiles it served well
- Simplicity or transparency benefits

---

## 6. Limitations and Bias

Where does your recommender struggle

Some prompts:
- Does it ignore some genres or moods
- Does it treat all users as if they have the same taste shape
- Is it biased toward high energy or one genre by default
- How could this be unfair if used in a real product

---

## 7. Evaluation

How did you check your system

Examples:
- You tried multiple user profiles and wrote down whether the results matched your expectations
- You compared your simulation to what a real app like Spotify or YouTube tends to recommend
- You wrote tests for your scoring logic

You do not need a numeric metric, but if you used one, explain what it measures.

---

## 8. Future Work

If you had more time, how would you improve this recommender

Examples:

- Add support for multiple users and "group vibe" recommendations
- Balance diversity of songs instead of always picking the closest match
- Use more features, like tempo ranges or lyric themes

---

## 9. Personal Reflection

A few sentences about what you learned:

- What surprised you about how your system behaved
- How did building this change how you think about real music recommenders
- Where do you think human judgment still matters, even if the model seems "smart"

