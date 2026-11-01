import pandas as pd
import numpy as np
from pathlib import Path

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from src.recommender import load_recommender

from src.collaborative import (
    load_collaborative_model,
    recommend_for_new_user
)


# ==========================================
# 1. LOAD MODELS AND DATA
# ==========================================

# Load TF-IDF recommender
print("Loading movie dataset and TF-IDF models...")

movies, genre_matrix, tag_matrix, plot_matrix = load_recommender()


# Load collaborative filtering model
print("\nLoading collaborative filtering model...")

_, rating_matrix, _, user_means = load_collaborative_model()


# Load or generate semantic embeddings
embedding_path = Path("data/plot_embeddings.npy")

if embedding_path.exists():

    print("\nLoading saved movie embeddings...")
    embeddings = np.load(embedding_path)

else:

    print("\nLoading Sentence Transformer model...")

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("\nGenerating movie plot embeddings...")

    embeddings = model.encode(
        movies["overview"].tolist(),
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    np.save(embedding_path, embeddings)

    print("Embeddings saved successfully!")


# ==========================================
# 2. SELECT MOVIES AND RATINGS
# ==========================================

def select_movies():

    user_preferences = {}

    while True:

        movie_title = input(
            "\nEnter a movie you like (or press Enter to finish): "
        )

        if movie_title == "":
            break

        search_words = movie_title.lower().split()

        movie_matches = movies[
            movies["title"].str.lower().apply(
                lambda title: all(word in title for word in search_words)
            )
        ]

        if movie_matches.empty:
            print("Movie not found!")
            continue

        if len(movie_matches) > 1:

            print("\nMultiple movies found:")

            for i, title in enumerate(movie_matches["title"], start=1):
                print(f"{i}. {title}")

            try:
                choice = int(input("Choose a movie: "))
            except ValueError:
                print("Please enter a valid number!")
                continue

            if choice < 1 or choice > len(movie_matches):
                print("Invalid selection!")
                continue

            selected_movie = movie_matches.iloc[choice - 1]

        else:
            selected_movie = movie_matches.iloc[0]

        movie_id = int(selected_movie["movieId"])
        movie_title = selected_movie["title"]

        if movie_id in user_preferences:
            print("You've already selected that movie!")
            continue

        # Ask for an optional rating
        while True:

            rating_input = input(
                "Rate this movie from 1–5 (or press Enter to skip): "
            )

            if rating_input == "":
                rating = None
                break

            try:
                rating = float(rating_input)
            except ValueError:
                print("Please enter a number from 1–5!")
                continue

            if not 1 <= rating <= 5:
                print("Rating must be between 1 and 5!")
                continue

            break

        user_preferences[movie_id] = rating

        if rating is None:
            print(f"Added: {movie_title} (No rating)")
        else:
            print(f"Added: {movie_title} ({rating}/5)")

    return user_preferences


# ==========================================
# 3. GENERATE RECOMMENDATIONS
# ==========================================

def compare_recommendations(
    movie_indices,
    user_preferences,
    limit=10
):

    # --------------------------------------
    # MODEL 1: TF-IDF
    # --------------------------------------

    genre_scores = cosine_similarity(
        genre_matrix[movie_indices], genre_matrix
    ).mean(axis=0)

    tag_scores = cosine_similarity(
        tag_matrix[movie_indices], tag_matrix
    ).mean(axis=0)

    plot_scores = cosine_similarity(
        plot_matrix[movie_indices], plot_matrix
    ).mean(axis=0)

    tfidf_scores = (
        0.15 * genre_scores +
        0.15 * tag_scores +
        0.70 * plot_scores
    )


    # --------------------------------------
    # MODEL 2: SEMANTIC EMBEDDINGS
    # --------------------------------------

    semantic_scores = (
        embeddings[movie_indices] @ embeddings.T
    ).mean(axis=0)


    # --------------------------------------
    # MODEL 3: COLLABORATIVE FILTERING
    # --------------------------------------

    # Request a larger candidate pool for hybrid ranking
    collaborative_candidates = recommend_for_new_user(
        user_preferences,
        rating_matrix,
        user_means,
        limit=100
    )

    # Keep a separate top-10 list for display
    collaborative_recommendations = (
        collaborative_candidates.head(limit).copy()
    )


    # --------------------------------------
    # EXCLUDE SELECTED MOVIES
    # --------------------------------------

    tfidf_scores[movie_indices] = -1
    semantic_scores[movie_indices] = -1


    # --------------------------------------
    # MODEL 4: THREE-MODEL HYBRID RANK FUSION
    # --------------------------------------

    # Rank movies according to TF-IDF and semantic scores
    tfidf_order = np.argsort(tfidf_scores)[::-1]
    semantic_order = np.argsort(semantic_scores)[::-1]

    num_movies = len(movies)

    # Convert rankings into rank positions
    tfidf_ranks = np.empty(num_movies, dtype=int)
    semantic_ranks = np.empty(num_movies, dtype=int)

    tfidf_ranks[tfidf_order] = np.arange(num_movies)
    semantic_ranks[semantic_order] = np.arange(num_movies)

    # Reciprocal Rank Fusion smoothing constant
    k = 60

    # Convert content-based rankings into RRF scores
    tfidf_rank_scores = 1 / (k + tfidf_ranks + 1)
    semantic_rank_scores = 1 / (k + semantic_ranks + 1)


    # --------------------------------------
    # COLLABORATIVE RANK SCORES
    # --------------------------------------

    # Start with zero contribution from collaborative filtering
    collaborative_rank_scores = np.zeros(num_movies)

    if not collaborative_candidates.empty:

        # Sort collaborative candidates by predicted rating
        collaborative_order = (
            collaborative_candidates
            .sort_values(
                "predicted_rating",
                ascending=False
            )
        )

        # Map MovieLens movie IDs to dataframe row indices
        movie_id_to_index = pd.Series(
            movies.index,
            index=movies["movieId"]
        )

        # Assign reciprocal rank scores to collaborative candidates
        for rank, movie_id in enumerate(
            collaborative_order["movieId"]
        ):

            if movie_id in movie_id_to_index.index:

                movie_index = movie_id_to_index.loc[movie_id]

                collaborative_rank_scores[movie_index] = (
                    1 / (k + rank + 1)
                )


    # --------------------------------------
    # COMBINE ALL THREE MODELS
    # --------------------------------------

    hybrid_scores = (
        (1 / 3) * tfidf_rank_scores +
        (1 / 3) * semantic_rank_scores +
        (1 / 3) * collaborative_rank_scores
    )

    # Exclude all selected movies from the final recommendations
    hybrid_scores[movie_indices] = -1

    # Get final hybrid recommendations
    hybrid_indices = np.argsort(hybrid_scores)[::-1][:limit]


    # ======================================
    # 4. DISPLAY RECOMMENDATIONS
    # ======================================

    # Display TF-IDF recommendations
    print("\n" + "=" * 55)
    print("MODEL 1: TF-IDF RECOMMENDATIONS")
    print("=" * 55)

    for i, index in enumerate(tfidf_order[:limit], start=1):
        print(
            f"{i}. {movies.iloc[index]['title']} "
            f"| Score: {tfidf_scores[index]:.3f}"
        )


    # Display semantic recommendations
    print("\n" + "=" * 55)
    print("MODEL 2: SEMANTIC EMBEDDING RECOMMENDATIONS")
    print("=" * 55)

    for i, index in enumerate(semantic_order[:limit], start=1):
        print(
            f"{i}. {movies.iloc[index]['title']} "
            f"| Score: {semantic_scores[index]:.3f}"
        )


    # Display collaborative recommendations
    print("\n" + "=" * 55)
    print("MODEL 3: COLLABORATIVE FILTERING RECOMMENDATIONS")
    print("=" * 55)

    if collaborative_recommendations.empty:

        print("Not enough rating information for recommendations.")

    else:

        collaborative_display = (
            collaborative_recommendations.merge(
                movies[["movieId", "title"]],
                on="movieId",
                how="left"
            )
        )

        for i, row in enumerate(
            collaborative_display.itertuples(index=False),
            start=1
        ):
            print(
                f"{i}. {row.title} "
                f"| Predicted Rating: {row.predicted_rating:.2f}/5 "
                f"| Supporting Users: {row.num_users}"
            )


    # Display hybrid recommendations
    print("\n" + "=" * 55)
    print("MODEL 4: THREE-MODEL HYBRID RECOMMENDATIONS")
    print("=" * 55)

    for i, index in enumerate(hybrid_indices, start=1):
        print(
            f"{i}. {movies.iloc[index]['title']} "
            f"| Hybrid Score: {hybrid_scores[index]:.4f}"
        )


# ==========================================
# 5. RUN COMPARISON
# ==========================================

def main():

    user_preferences = select_movies()

    if not user_preferences:
        print("Please select at least one movie!")
        return

    # Convert MovieLens IDs into movie dataframe indices
    movie_indices = movies.index[
        movies["movieId"].isin(user_preferences.keys())
    ].tolist()

    # Count rated and unrated movies
    rated_count = sum(
        rating is not None
        for rating in user_preferences.values()
    )

    print(f"\nSelected movies: {len(user_preferences)}")
    print(f"Movies rated: {rated_count}")
    print(f"Movies without ratings: {len(user_preferences) - rated_count}")

    print("\nGenerating recommendations...")

    compare_recommendations(
        movie_indices,
        user_preferences
    )


if __name__ == "__main__":
    main()
