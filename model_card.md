# Model Card: Music Recommender Simulation

---

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Goal / Task

VibeFinder suggests songs from a small catalog based on a user's taste profile. The user describes what they want — a genre like pop or lo-fi, a mood like happy or chill, and preferences for how energetic, positive, fast, danceable, or acoustic the music should be. The system compares those preferences to every song in the catalog, assigns each song a score, and returns the top matches.

This system is built for classroom learning. It is not designed for real users or production use.

---

## 3. Data Used

The catalog contains 20 songs. Each song has the following features:

- **Genre** — the style of music (e.g. pop, rock, lo-fi, jazz, ambient)
- **Mood** — an emotional label (e.g. happy, chill, intense, sad)
- **Energy** — how intense or powerful the song feels, on a scale from 0 to 1
- **Valence** — how positive or upbeat it sounds, from 0 (dark) to 1 (bright)
- **Tempo** — the speed of the song in beats per minute
- **Danceability** — how well-suited it is for dancing, from 0 to 1
- **Acousticness** — how organic or acoustic (vs. electronic) the song sounds, from 0 to 1

**Dataset limitations:**
- The catalog is very small. With only 20 songs, most genres appear only once or twice, which limits how varied the recommendations can be.
- 9 out of 14 genres have only one song. A user who prefers blues, folk, or classical has almost no real options.
- Energy values cluster between 0.28 and 0.93. Very low energy preferences (below 0.20) have no close matches in the catalog.
- Lo-fi is the most represented genre with 3 songs, which means lo-fi users get more varied results than users of rarer genres.

---

## 4. Algorithm Summary

The system scores each song out of 10 points by adding up contributions from all seven features.

**Genre** is worth up to 2.5 points. If the song's genre exactly matches what the user wants, it gets the full 2.5. If it is a similar genre (for example, indie pop is treated as similar to pop), it gets 1.25. If there is no match, it gets 0.

**Mood** is worth up to 2.0 points. An exact match — or a close alias like "calm" treated as "chill" — gives 2.0 points. No match gives 0.

**The five audio features** (energy, valence, tempo, danceability, acousticness) together account for the remaining 5.5 points. Each one measures the gap between the song's value and the user's preference. The closer the song is to what the user wants, the more points it earns. Energy has the highest weight at 2.0 points because it is the most noticeable difference between, say, a workout playlist and a sleep playlist. Valence, danceability, acousticness, and tempo each carry less weight.

The final score is the sum of all these contributions. Songs are then ranked highest to lowest, and the top results are returned.

---

## 5. Observed Behavior and Biases

**The system can give high scores to songs that do not actually match what the user wants.**

Because the audio features — especially energy — carry significant weight, a song can score well just by having similar numbers, even if the genre and mood are completely wrong. In testing, a classical piano piece called *First Snow* scored 6.15 out of 10 against a user who wanted very quiet ambient music with no genre preference. It ranked 4th. The only reason it scored that high was that its energy level (0.19) happened to be close to the user's preference (0.15). The mood, genre, and every other feature were irrelevant — the system had no way to filter it out.

A related issue is that mood mismatches are invisible in the score. When a user requested sad rock with high energy, *Storm Runner* ranked first with a score of 7.43. That looks like a confident match — but the sad mood preference contributed zero points because no rock song in the catalog is labeled "sad." The system returned a result that ignored the mood entirely, with no indication that anything was missing.

Finally, high-energy pop users consistently see the same songs — *Gym Hero* and *Sunrise City* — in nearly every session. This happens because energy and genre together account for 4.5 of the 10 possible points, and those two songs match both features closely. Even changing the mood or valence preference does not push them out of the top results.

---

## 6. Evaluation

**Profiles tested:**
- High-energy happy pop (Baseline Pop)
- Low-energy chill lo-fi (Lo-fi Study)
- High-energy sad rock (conflicting mood and energy)
- Very low energy ambient (Ultra-Quiet Ambient)
- Genre not in the catalog at all (classical / calm)
- No genre provided — mood and audio features only
- Baseline Pop with energy lowered from 0.85 to 0.50
- Same genre as Baseline Pop but mood flipped to sad, valence lowered (Mood Flip)

**What I was checking for:** I wanted to see whether the system could handle edge cases gracefully — returning lower scores when it had less information, and clearly different results when preferences changed.

**What actually happened:** For straightforward profiles, the system worked as expected. Baseline Pop returned *Sunrise City* at 9.71 and Lo-fi Study returned *Library Rain* at 9.78 — both felt right. For edge cases, the results were less trustworthy but looked equally confident. The classical profile with no matching genre or mood still returned songs scoring above 5.0, with no signal that the recommendations were based on thin information.

**What surprised me:** Lowering energy from 0.85 to 0.50 barely changed the rankings. The top songs stayed the same because most songs in the catalog have mid-range energy values, so the system could not clearly separate them. I also did not expect a classical song to appear in the top 5 for an ambient music request — but the scoring formula had no way to block it.

---

## 7. Intended and Non-Intended Use

**This system works reasonably well when:**
- The user's preferred genre and mood both exist in the catalog
- The catalog has multiple songs in that genre to choose from
- Preferences are straightforward (e.g., high-energy pop or chill lo-fi)

**This system should NOT be used when:**
- Recommendations need to be fair or accurate for real users
- The user's genre or mood is rare or missing from the catalog
- Diverse results are important — the system tends to repeat the same songs
- The stakes are higher than a classroom exercise

---

## 8. Ideas for Improvement

1. **Add a minimum threshold for categorical matching.** A song should need to earn at least some points from genre or mood before the audio features carry much weight. This would prevent *First Snow* from ranking highly just because its energy happens to be close.

2. **Expand the catalog with more genre and mood diversity.** With only one blues song and one classical song, users with those preferences have almost no real options. Adding 5–10 songs per major genre would make recommendations more meaningful and varied.

3. **Introduce a diversity rule for top results.** If the top 3 results are all the same genre, replace one with the best match from a different genre. This would reduce the repetition that currently locks high-energy pop users into seeing *Gym Hero* and *Sunrise City* every single time.

---

## 9. Personal Reflection

The biggest thing I learned is how much one weight decision can quietly reshape everything. When I doubled the energy weight during the experiment, I expected dramatic ranking shifts — but the top results barely changed for normal profiles, and the real damage showed up in edge cases where songs with no genre or mood match suddenly floated into the top 5. That taught me that weight tuning is not just about making good results better; it is mostly about controlling what happens when things go wrong.

AI tools were genuinely useful for generating profiles, diagnosing scoring gaps, and drafting sections of the model card — things that would have taken much longer to work through manually. But I had to stay involved. At one point the analysis sounded confident about why *Gym Hero* kept appearing, but I needed to actually run the scores to confirm whether it was energy or genre doing the heavy lifting. It turned out both mattered, but in different ways for different profiles, and I would have missed that nuance if I had just accepted the explanation without checking.

What surprised me most was how realistic the recommendations felt for clean profiles, even though the system is just adding up numbers. When I ran the lo-fi profile, *Library Rain* appeared at the top and it genuinely felt like the right answer — not because the system understood music, but because enough of the right features happened to line up. That gap between "feels right" and "is actually reasoning correctly" is something I want to keep in mind.

If I extended this project, I would try adding a confidence signal alongside the score — something that tells the user how many features actually matched, so a 7.4 driven by genre and mood reads differently than a 7.4 driven by energy alone. I would also expand the catalog to have at least 3–4 songs per genre, because the current setup means a blues or folk listener is one song away from getting completely off-topic recommendations.
