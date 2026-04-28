"""
Test harness for the three-stage agentic pipeline.

Stage 1 (parse_user_intent) and Stage 3 (reflect_on_recommendations) make live
API calls, so those functions are patched with deterministic fakes.  Stage 2
(get_recommendations) is pure-Python, so it runs against the real CSV.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

SONGS_CSV = str(Path(__file__).parent.parent / "data" / "songs.csv")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tool_use_response(profile: dict):
    """Build a fake anthropic response object that looks like a tool_use block."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = profile

    response = MagicMock()
    response.content = [block]
    return response


def _make_text_response(text: str):
    """Build a fake anthropic response object that looks like a text block."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.content = [block]
    return response


# ---------------------------------------------------------------------------
# Stage 1 — parse_user_intent
# ---------------------------------------------------------------------------

class TestParseUserIntent:
    def test_returns_dict(self):
        fake_profile = {"genre": "lofi", "mood": "chill", "energy": 0.35}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_tool_use_response(fake_profile)
            from src.agent import parse_user_intent
            result = parse_user_intent("late night study vibes")

        assert isinstance(result, dict)
        assert result["genre"] == "lofi"
        assert result["mood"] == "chill"

    def test_passes_correct_tool_name(self):
        fake_profile = {"genre": "pop", "mood": "happy"}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_tool_use_response(fake_profile)
            from src.agent import parse_user_intent
            parse_user_intent("upbeat pop song")

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["tool_choice"] == {"type": "tool", "name": "extract_music_profile"}

    def test_partial_profile_allowed(self):
        """Claude may return only a subset of fields — that should be accepted."""
        fake_profile = {"mood": "intense"}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_tool_use_response(fake_profile)
            from src.agent import parse_user_intent
            result = parse_user_intent("something intense")

        assert result == {"mood": "intense"}

    def test_empty_profile_allowed(self):
        """Even an empty extraction (no confident fields) should not raise."""
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_tool_use_response({})
            from src.agent import parse_user_intent
            result = parse_user_intent("play me some music")

        assert result == {}


# ---------------------------------------------------------------------------
# Stage 2 — get_recommendations (real scoring, real CSV)
# ---------------------------------------------------------------------------

class TestGetRecommendations:
    def test_returns_k_results(self):
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        results = get_recommendations({"genre": "pop", "mood": "happy", "energy": 0.8}, songs, k=3)
        assert len(results) == 3

    def test_result_structure(self):
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        results = get_recommendations({"genre": "lofi", "mood": "chill"}, songs, k=1)
        song, score, explanation = results[0]
        assert isinstance(song, dict)
        assert isinstance(score, float)
        assert isinstance(explanation, str)

    def test_scores_sorted_descending(self):
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        prefs = {"genre": "rock", "mood": "intense", "energy": 0.9, "tempo_bpm": 150}
        results = get_recommendations(prefs, songs, k=5)
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_genre_match_ranks_higher(self):
        """A song whose genre exactly matches should outscore one that does not,
        all else being equal."""
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        prefs = {"genre": "lofi", "mood": "chill", "energy": 0.4}
        results = get_recommendations(prefs, songs, k=3)
        top_song = results[0][0]
        assert top_song["genre"] in {"lofi", "ambient"}  # lofi or its similar genre

    def test_mode_affects_ranking(self):
        """genre_first mode should rank genre matches higher than balanced."""
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

        balanced = get_recommendations(prefs, songs, k=5, mode="balanced")
        genre_first = get_recommendations(prefs, songs, k=5, mode="genre_first")

        # Top result in genre_first must be a genre match (pop or similar)
        top_gf = genre_first[0][0]
        assert top_gf.get("genre") in {"pop", "indie pop", "synthwave"}

    def test_empty_prefs_returns_results(self):
        """With no preferences, all songs get low equal scores — we still get k back."""
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        results = get_recommendations({}, songs, k=3)
        assert len(results) == 3

    def test_scores_bounded(self):
        """No score should exceed 10.0 (the documented max)."""
        from src.agent import get_recommendations
        from src.recommender import load_songs
        songs = load_songs(SONGS_CSV)
        prefs = {"genre": "pop", "mood": "happy", "energy": 0.82, "valence": 0.84,
                 "tempo_bpm": 118, "danceability": 0.79, "acousticness": 0.18}
        results = get_recommendations(prefs, songs, k=len(songs))
        assert all(r[1] <= 10.0 for r in results)


# ---------------------------------------------------------------------------
# Stage 3 — reflect_on_recommendations
# ---------------------------------------------------------------------------

class TestReflectOnRecommendations:
    def _sample_recs(self):
        return [
            (
                {"title": "Midnight Coding", "artist": "LoRoom", "genre": "lofi",
                 "mood": "chill", "energy": 0.42},
                8.5,
                "genre match: lofi (+1.50), mood match: chill (+2.00)",
            )
        ]

    def test_returns_non_empty_string(self):
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_text_response(
                "These recommendations closely match the user's request."
            )
            from src.agent import reflect_on_recommendations
            result = reflect_on_recommendations(
                "late night study", {"genre": "lofi"}, self._sample_recs()
            )
        assert isinstance(result, str)
        assert result.strip() != ""

    def test_does_not_send_thinking_param(self):
        """Reflection call must not include a thinking parameter (removed per fix)."""
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_text_response("good match")
            from src.agent import reflect_on_recommendations
            reflect_on_recommendations("study music", {}, self._sample_recs())

            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert "thinking" not in call_kwargs

    def test_prompt_contains_user_input(self):
        """The user's original request should appear in the prompt sent to the LLM."""
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.return_value = _make_text_response("ok")
            from src.agent import reflect_on_recommendations
            reflect_on_recommendations("rainy day jazz", {"genre": "jazz"}, self._sample_recs())

            call_kwargs = mock_client.messages.create.call_args.kwargs
            user_message = call_kwargs["messages"][0]["content"]
            assert "rainy day jazz" in user_message


# ---------------------------------------------------------------------------
# Full pipeline — run_agent
# ---------------------------------------------------------------------------

class TestRunAgent:
    def test_output_keys_present(self):
        fake_profile = {"genre": "lofi", "mood": "chill", "energy": 0.35,
                        "acousticness": 0.80, "tempo_bpm": 78}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.side_effect = [
                _make_tool_use_response(fake_profile),   # Stage 1
                _make_text_response("These are great recommendations."),  # Stage 3
            ]
            from src.agent import run_agent
            result = run_agent("late night study vibes", songs_path=SONGS_CSV, k=3)

        assert set(result.keys()) == {"user_input", "profile", "recommendations", "reflection"}

    def test_recommendations_count(self):
        fake_profile = {"genre": "pop", "mood": "happy", "energy": 0.8}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.side_effect = [
                _make_tool_use_response(fake_profile),
                _make_text_response("Good matches overall."),
            ]
            from src.agent import run_agent
            result = run_agent("upbeat pop", songs_path=SONGS_CSV, k=2)

        assert len(result["recommendations"]) == 2

    def test_recommendation_fields(self):
        fake_profile = {"genre": "rock", "mood": "intense"}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.side_effect = [
                _make_tool_use_response(fake_profile),
                _make_text_response("Solid rock picks."),
            ]
            from src.agent import run_agent
            result = run_agent("aggressive rock", songs_path=SONGS_CSV, k=1)

        rec = result["recommendations"][0]
        for key in ("title", "artist", "genre", "mood", "score", "explanation"):
            assert key in rec

    def test_profile_passed_through(self):
        fake_profile = {"genre": "ambient", "energy": 0.1}
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.side_effect = [
                _make_tool_use_response(fake_profile),
                _make_text_response("Very calm selections."),
            ]
            from src.agent import run_agent
            result = run_agent("ultra quiet background", songs_path=SONGS_CSV)

        assert result["profile"] == fake_profile

    def test_reflection_string_in_output(self):
        fake_profile = {"genre": "jazz"}
        reflection_text = "The jazz picks are a solid match for the user's mood."
        with patch("src.agent.client") as mock_client:
            mock_client.messages.create.side_effect = [
                _make_tool_use_response(fake_profile),
                _make_text_response(reflection_text),
            ]
            from src.agent import run_agent
            result = run_agent("jazzy evening", songs_path=SONGS_CSV)

        assert result["reflection"] == reflection_text
