
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from src.recommender import load_recommender
from src.collaborative import (
    load_collaborative_model,
    recommend_for_new_user
)


# ==========================================
# CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

TFIDF_WEIGHT = 0.25
SEMANTIC_WEIGHT = 0.05
COLLABORATIVE_WEIGHT = 0.70

RRF_K = 60
COLLABORATIVE_LIMIT = 100


# ==========================================
# LOAD HYBRID MODEL
# ==========================================

def load_hybrid_model():
    """Load all data and models needed for hybrid recommendations."""

    # Load movie data and TF-IDF matrices
    movies, genre_matrix, tag_matrix, plot_matrix = (
        load_recommender()
    )

    # Load precomputed semantic embeddings
    embedding_path = DATA_DIR / "plot_embeddings.npy"

    if not embedding_path.exists():
        raise FileNotFoundError(
            "Saved plot embeddings were not found. "
            "Expected file: data/plot_embeddings.npy"
        )

    embeddings = np.load(embedding_path)

    # Make sure embeddings match the movie dataset
    if len(embeddings) != len(movies):
        raise ValueError(
            "The number of embeddings does not match "
            "the number of movies."
        )

    # Load collaborative filtering data
    _, rating_matrix, _, user_means = (
        load_collaborative_model()
    )

    return {
        "movies": movies,
        "genre_matrix": genre_matrix,
        "tag_matrix": tag_matrix,
        "plot_matrix": plot_matrix,
        "embeddings": embeddings,
        "rating_matrix": rating_matrix,
        "user_means": user_means
    }


# ==========================================
# HYBRID RECOMMENDATIONS
# ==========================================

def recommend_hybrid(
    user_preferences,
    model,
    limit=10,
    preferred_genre="any",
    exclude_movie_ids=None
):
    """Generate personalized recommendations using all three models."""

    movies = model["movies"]
    genre_matrix = model["genre_matrix"]
    tag_matrix = model["tag_matrix"]
    plot_matrix = model["plot_matrix"]
    embeddings = model["embeddings"]
    rating_matrix = model["rating_matrix"]
    user_means = model["user_means"]

    # Keep only valid movie ratings
    user_preferences = {
        movie_id: rating
        for movie_id, rating in user_preferences.items()
        if rating is not None
    }

    # Map MovieLens IDs to movie dataset positions
    movie_id_to_index = dict(
        zip(movies["movieId"], movies.index)
    )

    movie_indices = [
        movie_id_to_index[movie_id]
        for movie_id in user_preferences
        if movie_id in movie_id_to_index
    ]

    if not movie_indices:
        return pd.DataFrame()

    num_movies = len(movies)

    # Exclude movies the user has rated or already received
    excluded_movie_ids = set(user_preferences.keys())

    if exclude_movie_ids:
        excluded_movie_ids.update(
            int(movie_id) for movie_id in exclude_movie_ids
        )

    excluded_indices = [
        movie_id_to_index[movie_id]
        for movie_id in excluded_movie_ids
        if movie_id in movie_id_to_index
    ]

    # ======================================
    # MODEL 1: TF-IDF
    # ======================================

    genre_scores = cosine_similarity(
        genre_matrix[movie_indices],
        genre_matrix
    ).mean(axis=0)

    tag_scores = cosine_similarity(
        tag_matrix[movie_indices],
        tag_matrix
    ).mean(axis=0)

    plot_scores = cosine_similarity(
        plot_matrix[movie_indices],
        plot_matrix
    ).mean(axis=0)

    tfidf_scores = (
        0.15 * genre_scores +
        0.15 * tag_scores +
        0.70 * plot_scores
    )

    tfidf_scores[excluded_indices] = -1

    tfidf_order = np.argsort(tfidf_scores)[::-1]

    tfidf_ranks = np.empty(num_movies, dtype=int)
    tfidf_ranks[tfidf_order] = np.arange(num_movies)

    tfidf_rank_scores = (
        1 / (RRF_K + tfidf_ranks + 1)
    )

    # ======================================
    # MODEL 2: PERSONALIZED SEMANTIC
    # ======================================

    user_ratings = pd.Series(user_preferences)

    liked_movie_indices = [
        index for index in movie_indices
        if user_ratings.get(
            movies.iloc[index]["movieId"], 0
        ) >= 4
    ]

    disliked_movie_indices = [
        index for index in movie_indices
        if user_ratings.get(
            movies.iloc[index]["movieId"], 0
        ) <= 2.5
    ]

    liked_similarity = np.zeros(num_movies)
    disliked_similarity = np.zeros(num_movies)

    # Similarity to movies the user liked
    if liked_movie_indices:

        liked_weights = np.array([
            user_ratings[movies.iloc[index]["movieId"]] - 3
            for index in liked_movie_indices
        ])

        liked_similarity = np.average(
            embeddings[liked_movie_indices] @ embeddings.T,
            axis=0,
            weights=liked_weights
        )

    # Similarity to movies the user disliked
    if disliked_movie_indices:

        disliked_weights = np.array([
            3 - user_ratings[movies.iloc[index]["movieId"]]
            for index in disliked_movie_indices
        ])

        disliked_similarity = np.average(
            embeddings[disliked_movie_indices] @ embeddings.T,
            axis=0,
            weights=disliked_weights
        )

    semantic_scores = (
        liked_similarity - 0.5 * disliked_similarity
    )

    semantic_scores[excluded_indices] = -1

    semantic_order = np.argsort(semantic_scores)[::-1]

    semantic_ranks = np.empty(num_movies, dtype=int)
    semantic_ranks[semantic_order] = np.arange(num_movies)

    semantic_rank_scores = (
        1 / (RRF_K + semantic_ranks + 1)
    )

    # ======================================
    # MODEL 3: COLLABORATIVE FILTERING
    # ======================================

    collaborative_candidates = recommend_for_new_user(
        user_preferences,
        rating_matrix,
        user_means,
        limit=COLLABORATIVE_LIMIT
    )

    collaborative_rank_scores = np.zeros(num_movies)

    if not collaborative_candidates.empty:

        collaborative_candidates = (
            collaborative_candidates.sort_values(
                "predicted_rating",
                ascending=False
            )
        )

        for rank, movie_id in enumerate(
            collaborative_candidates["movieId"]
        ):

            movie_index = movie_id_to_index.get(movie_id)

            if movie_index is not None:

                collaborative_rank_scores[movie_index] = (
                    1 / (RRF_K + rank + 1)
                )

    # ======================================
    # COMBINE THE THREE MODELS
    # ======================================

    hybrid_scores = (
        TFIDF_WEIGHT * tfidf_rank_scores +
        SEMANTIC_WEIGHT * semantic_rank_scores +
        COLLABORATIVE_WEIGHT * collaborative_rank_scores
    )

    # ======================================
    # APPLY GENRE PREFERENCE
    # ======================================

    # Start with all movies eligible
    eligible_mask = np.ones(num_movies, dtype=bool)

    # Exclude movies the user has already rated
    eligible_mask[excluded_indices] = False

    # Apply the selected genre, if one was chosen
    if preferred_genre and preferred_genre.lower() != "any":

        genre_mask = (
            movies["genres"]
            .fillna("")
            .apply(
                lambda genres: preferred_genre in genres.split()
            )
            .to_numpy()
        )

        eligible_mask &= genre_mask

    # Get only eligible movie positions
    eligible_indices = np.flatnonzero(eligible_mask)

    # Return an empty result if no movies match
    if len(eligible_indices) == 0:
        return pd.DataFrame()

    # Rank eligible movies using the existing hybrid scores
    top_indices = eligible_indices[
        np.argsort(hybrid_scores[eligible_indices])[::-1][:limit]
    ]

    # Build recommendation results
    recommendations = movies.iloc[
        top_indices
    ][["movieId", "title", "genres"]].copy()

    recommendations["tfidf_score"] = (
        tfidf_rank_scores[top_indices]
    )

    recommendations["semantic_score"] = (
        semantic_rank_scores[top_indices]
    )

    recommendations["collaborative_score"] = (
        collaborative_rank_scores[top_indices]
    )

    recommendations["final_score"] = (
        hybrid_scores[top_indices]
    )

    return recommendations.reset_index(drop=True)
