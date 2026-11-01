
import numpy as np
import pandas as pd

from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from src.recommender import load_recommender
from src.collaborative import (
    load_collaborative_model,
    recommend_for_new_user
)


# ==========================================
# 1. CONFIGURATION
# ==========================================

RANDOM_SEED = 42

TRAIN_SIZE = 0.70
VALIDATION_SIZE = 0.15
TEST_SIZE = 0.15

SAMPLE_SIZE = 100
TOP_K = 10

RELEVANCE_THRESHOLD = 4.0
COLLABORATIVE_LIMIT = 100

# Search weights in increments of 5%
WEIGHT_STEP = 0.05

rng = np.random.default_rng(RANDOM_SEED)


# ==========================================
# 2. LOAD MOVIE DATA AND MODELS
# ==========================================

print("Loading movie dataset and TF-IDF models...")

movies, genre_matrix, tag_matrix, plot_matrix = load_recommender()

print("\nLoading movie embeddings...")

embedding_path = Path("data/plot_embeddings.npy")

if embedding_path.exists():

    embeddings = np.load(embedding_path)

else:

    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    embeddings = model.encode(
        movies["overview"].tolist(),
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    np.save(embedding_path, embeddings)


# ==========================================
# 3. SPLIT RATINGS INTO THREE DATASETS
# ==========================================

print("\nPreparing training, validation, and testing data...")

ratings = pd.read_csv("data/ratings.csv")

train_parts = []
validation_parts = []
test_parts = []

for user_id, user_ratings in ratings.groupby("userId"):

    shuffled_indices = rng.permutation(len(user_ratings))

    validation_count = max(
        1,
        int(len(user_ratings) * VALIDATION_SIZE)
    )

    test_count = max(
        1,
        int(len(user_ratings) * TEST_SIZE)
    )

    validation_indices = shuffled_indices[:validation_count]

    test_indices = shuffled_indices[
        validation_count:validation_count + test_count
    ]

    train_indices = shuffled_indices[
        validation_count + test_count:
    ]

    train_parts.append(user_ratings.iloc[train_indices])

    validation_parts.append(
        user_ratings.iloc[validation_indices]
    )

    test_parts.append(user_ratings.iloc[test_indices])


train_ratings = pd.concat(train_parts)
validation_ratings = pd.concat(validation_parts)
test_ratings = pd.concat(test_parts)

print("Training ratings:", len(train_ratings))
print("Validation ratings:", len(validation_ratings))
print("Testing ratings:", len(test_ratings))


# ==========================================
# 4. BUILD COLLABORATIVE MODEL
# ==========================================

print("\nBuilding collaborative filtering model...")

_, rating_matrix, _, user_means = load_collaborative_model(
    train_ratings
)


# ==========================================
# 5. EVALUATION METRICS
# ==========================================

def calculate_metrics(recommendations, relevant_movies):

    recommendations = recommendations[:TOP_K]

    hits = [
        1 if movie_id in relevant_movies else 0
        for movie_id in recommendations
    ]

    # Precision@10
    precision = sum(hits) / TOP_K

    # Recall@10
    recall = (
        sum(hits) / len(relevant_movies)
        if relevant_movies
        else 0
    )

    # Discounted Cumulative Gain
    dcg = sum(
        hit / np.log2(rank + 2)
        for rank, hit in enumerate(hits)
    )

    # Ideal DCG
    ideal_hits = min(len(relevant_movies), TOP_K)

    idcg = sum(
        1 / np.log2(rank + 2)
        for rank in range(ideal_hits)
    )

    # NDCG@10
    ndcg = dcg / idcg if idcg > 0 else 0

    return precision, recall, ndcg


# ==========================================
# 6. SELECT EVALUATION USERS
# ==========================================

eligible_users = []

for user_id in validation_ratings["userId"].unique():

    user_train = train_ratings[
        train_ratings["userId"] == user_id
    ]

    user_validation = validation_ratings[
        validation_ratings["userId"] == user_id
    ]

    relevant_movies = set(
        user_validation.loc[
            user_validation["rating"] >= RELEVANCE_THRESHOLD,
            "movieId"
        ]
    )

    if len(user_train) >= 2 and len(relevant_movies) > 0:
        eligible_users.append(user_id)


sample_count = min(SAMPLE_SIZE, len(eligible_users))

evaluation_users = rng.choice(
    eligible_users,
    size=sample_count,
    replace=False
)

# ==========================================
# 6B. DIAGNOSE USER PROFILE DATA
# ==========================================

print("\n--- USER PROFILE DIAGNOSTICS ---")

positive_counts = []

for user_id in evaluation_users:

    user_train = train_ratings[
        train_ratings["userId"] == user_id
    ]

    liked_count = (user_train["rating"] >= 4).sum()

    positive_counts.append(liked_count)

print("Average positively rated training movies:",
      np.mean(positive_counts))

print("Median positively rated training movies:",
      np.median(positive_counts))

print("Users with 0 liked movies:",
      sum(count == 0 for count in positive_counts))

print("Users with 1-2 liked movies:",
      sum(1 <= count <= 2 for count in positive_counts))

print("Users with 3-5 liked movies:",
      sum(3 <= count <= 5 for count in positive_counts))

print("Users with 6+ liked movies:",
      sum(count >= 6 for count in positive_counts))

print("\nPreparing recommendations for", sample_count, "users...")


# ==========================================
# 7. PREPARE MOVIE ID MAPPING
# ==========================================

movie_id_to_index = dict(
    zip(movies["movieId"], movies.index)
)

num_movies = len(movies)

# RRF smoothing constant
k = 60


# ==========================================
# 8. GENERATE RECOMMENDATION SCORES
# ==========================================

user_records = []

for user_number, user_id in enumerate(
    evaluation_users,
    start=1
):

    user_train = train_ratings[
        train_ratings["userId"] == user_id
    ]

    user_preferences = dict(
        zip(
            user_train["movieId"],
            user_train["rating"]
        )
    )

    movie_indices = movies.index[
        movies["movieId"].isin(user_preferences.keys())
    ].tolist()

    if not movie_indices:
        continue


    # --------------------------------------
    # MODEL 1: TF-IDF
    # --------------------------------------

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

    tfidf_scores[movie_indices] = -1

    tfidf_order = np.argsort(tfidf_scores)[::-1]

    tfidf_ranks = np.empty(num_movies, dtype=int)
    tfidf_ranks[tfidf_order] = np.arange(num_movies)

    tfidf_rank_scores = (
        1 / (k + tfidf_ranks + 1)
    )



    # --------------------------------------
    # MODEL 2: SEMANTIC EMBEDDINGS
    # --------------------------------------

    # Original semantic model: all rated movies equally weighted
    semantic_scores = (
        embeddings[movie_indices] @ embeddings.T
    ).mean(axis=0)

    semantic_scores[movie_indices] = -1

    semantic_order = np.argsort(semantic_scores)[::-1]

    semantic_ranks = np.empty(num_movies, dtype=int)
    semantic_ranks[semantic_order] = np.arange(num_movies)

    semantic_rank_scores = (
        1 / (k + semantic_ranks + 1)
    )

    # --------------------------------------
    # MODEL 2B: PERSONALIZED SEMANTIC
    # --------------------------------------

    user_ratings = user_train.set_index("movieId")["rating"]

    # Separate positively and negatively rated movies
    liked_movie_indices = [
        index for index in movie_indices
        if user_ratings.get(movies.iloc[index]["movieId"], 0) >= 4
    ]

    disliked_movie_indices = [
        index for index in movie_indices
        if user_ratings.get(movies.iloc[index]["movieId"], 0) <= 2.5
    ]

    # Start with zero similarity scores
    liked_similarity = np.zeros(num_movies)
    disliked_similarity = np.zeros(num_movies)

    # Calculate similarity to positively rated movies
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

    # Calculate similarity to negatively rated movies
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

    # Reward similarity to liked movies and penalize
    # similarity to disliked movies
    positive_semantic_scores = (
        liked_similarity - 0.5 * disliked_similarity
    )

    # Exclude movies the user has already rated
    positive_semantic_scores[movie_indices] = -1

    positive_semantic_order = np.argsort(
        positive_semantic_scores
    )[::-1]

    positive_semantic_ranks = np.empty(num_movies, dtype=int)

    positive_semantic_ranks[positive_semantic_order] = np.arange(
        num_movies
    )

    positive_semantic_rank_scores = (
        1 / (k + positive_semantic_ranks + 1)
    )

    # --------------------------------------
    # MODEL 3: COLLABORATIVE FILTERING
    # --------------------------------------

    neighbor_matrix = rating_matrix.drop(
        index=user_id,
        errors="ignore"
    )

    neighbor_means = user_means.drop(
        index=user_id,
        errors="ignore"
    )

    collaborative_candidates = recommend_for_new_user(
        user_preferences,
        neighbor_matrix,
        neighbor_means,
        limit=COLLABORATIVE_LIMIT
    )

    collaborative_rank_scores = np.zeros(num_movies)

    if not collaborative_candidates.empty:

        collaborative_order = (
            collaborative_candidates
            .sort_values(
                "predicted_rating",
                ascending=False
            )
        )

        for rank, movie_id in enumerate(
            collaborative_order["movieId"]
        ):

            movie_index = movie_id_to_index.get(movie_id)

            if movie_index is not None:

                collaborative_rank_scores[movie_index] = (
                    1 / (k + rank + 1)
                )


    # --------------------------------------
    # SAVE USER DATA FOR REPEATED EVALUATION
    # --------------------------------------

    validation_relevant = set(
        validation_ratings.loc[
            (validation_ratings["userId"] == user_id) &
            (validation_ratings["rating"] >= RELEVANCE_THRESHOLD),
            "movieId"
        ]
    )

    test_relevant = set(
        test_ratings.loc[
            (test_ratings["userId"] == user_id) &
            (test_ratings["rating"] >= RELEVANCE_THRESHOLD),
            "movieId"
        ]
    )

    # Individual model rankings
    tfidf_recommendations = (
        movies.iloc[tfidf_order[:TOP_K]]["movieId"].tolist()
    )

    semantic_recommendations = (
        movies.iloc[semantic_order[:TOP_K]]["movieId"].tolist()
    )

    if collaborative_candidates.empty:

        collaborative_recommendations = []

    else:

        collaborative_recommendations = (
            collaborative_candidates
            .sort_values(
                "predicted_rating",
                ascending=False
            )["movieId"]
            .head(TOP_K)
            .tolist()
        )

    positive_semantic_recommendations = movies.iloc[
        positive_semantic_order[:TOP_K]
    ]["movieId"].tolist()

    user_records.append({
        "user_id": user_id,
        "excluded_indices": movie_indices,

        "tfidf_scores": tfidf_rank_scores,
        "semantic_scores": semantic_rank_scores,
        "positive_semantic_scores": positive_semantic_rank_scores,
        "collaborative_scores": collaborative_rank_scores,

        "tfidf_recommendations": tfidf_recommendations,
        "semantic_recommendations": semantic_recommendations,
        "positive_semantic_recommendations": positive_semantic_recommendations,
        "collaborative_recommendations": collaborative_recommendations,

        "validation_relevant": validation_relevant,
        "test_relevant": test_relevant
    })

    if user_number % 10 == 0:
        print(
            f"Prepared {user_number}/{sample_count} users..."
        )


actual_users = len(user_records)

print("\nSuccessfully prepared", actual_users, "users.")

# ==========================================
# 8B. INSPECT SEMANTIC RECOMMENDATIONS
# ==========================================

print("\n--- SEMANTIC RECOMMENDATION INSPECTION ---")

for record in user_records[:3]:

    user_id = record["user_id"]

    user_train = train_ratings[
        train_ratings["userId"] == user_id
    ]

    liked_movies = user_train[
        user_train["rating"] >= 4
    ].sort_values(
        "rating",
        ascending=False
    ).head(10)

    print(f"\nUSER {user_id}")

    print("\nMovies the user liked:")

    for _, row in liked_movies.iterrows():

        title = movies.loc[
            movies["movieId"] == row["movieId"],
            "title"
        ].iloc[0]

        print(f"  {title} ({row['rating']} stars)")

    print("\nPositive semantic recommendations:")

    for movie_id in record["positive_semantic_recommendations"]:

        title = movies.loc[
            movies["movieId"] == movie_id,
            "title"
        ].iloc[0]

        print(f"  {title}")

# ==========================================
# 9. GENERATE WEIGHT COMBINATIONS
# ==========================================

print("\nGenerating hybrid weight combinations...")

steps = round(1 / WEIGHT_STEP)

weight_combinations = []

for tfidf_step in range(steps + 1):

    for semantic_step in range(
        steps - tfidf_step + 1
    ):

        collaborative_step = (
            steps - tfidf_step - semantic_step
        )

        weights = (
            tfidf_step / steps,
            semantic_step / steps,
            collaborative_step / steps
        )

        weight_combinations.append(weights)


# Include exact equal weights as an additional baseline
equal_weights = (1 / 3, 1 / 3, 1 / 3)

if equal_weights not in weight_combinations:
    weight_combinations.append(equal_weights)

print("Configurations to test:", len(weight_combinations))


# ==========================================
# 10. HELPER: GET TOP RECOMMENDATIONS
# ==========================================

def get_top_recommendations(scores, excluded_indices):

    scores = scores.copy()

    scores[excluded_indices] = -1

    top_indices = np.argsort(scores)[::-1][:TOP_K]

    return movies.iloc[top_indices]["movieId"].tolist()


# ==========================================
# 11. EVALUATE A HYBRID CONFIGURATION
# ==========================================

def evaluate_hybrid(weights, split):

    tfidf_weight, semantic_weight, collaborative_weight = weights

    all_metrics = []

    recommended_movies = set()

    for record in user_records:

        if split == "validation":
            relevant_movies = record["validation_relevant"]

        else:
            relevant_movies = record["test_relevant"]

        hybrid_scores = (
            tfidf_weight * record["tfidf_scores"] +
            semantic_weight * record["positive_semantic_scores"] +
            collaborative_weight * record["collaborative_scores"]
        )

        recommendations = get_top_recommendations(
            hybrid_scores,
            record["excluded_indices"]
        )

        metrics = calculate_metrics(
            recommendations,
            relevant_movies
        )

        all_metrics.append(metrics)

        recommended_movies.update(recommendations)

    metrics_array = np.array(all_metrics)

    return {
        "Precision@10": metrics_array[:, 0].mean(),
        "Recall@10": metrics_array[:, 1].mean(),
        "NDCG@10": metrics_array[:, 2].mean(),
        "Catalog Coverage": len(recommended_movies) / len(movies)
    }


# ==========================================
# 12. GRID SEARCH
# ==========================================

print("\n" + "=" * 75)
print("OPTIMIZING HYBRID MODEL WEIGHTS")
print("=" * 75)

search_results = []

for number, weights in enumerate(
    weight_combinations,
    start=1
):

    metrics = evaluate_hybrid(
        weights,
        "validation"
    )

    search_results.append({
        "TF-IDF": weights[0],
        "Semantic": weights[1],
        "Collaborative": weights[2],
        **metrics
    })

    if number % 25 == 0:
        print(
            f"Tested {number}/{len(weight_combinations)} configurations..."
        )


search_df = pd.DataFrame(search_results)

# Optimize for validation NDCG@10
search_df = search_df.sort_values(
    "NDCG@10",
    ascending=False
).reset_index(drop=True)

best_weights = (
    search_df.iloc[0]["TF-IDF"],
    search_df.iloc[0]["Semantic"],
    search_df.iloc[0]["Collaborative"]
)


# ==========================================
# 13. DISPLAY OPTIMIZATION RESULTS
# ==========================================

print("\n" + "=" * 75)
print("TOP 10 HYBRID CONFIGURATIONS")
print("=" * 75)

print(
    search_df.head(10).to_string(
        index=False,
        formatters={
            "TF-IDF": "{:.0%}".format,
            "Semantic": "{:.0%}".format,
            "Collaborative": "{:.0%}".format,
            "Precision@10": "{:.4f}".format,
            "Recall@10": "{:.4f}".format,
            "NDCG@10": "{:.4f}".format,
            "Catalog Coverage": "{:.2%}".format
        }
    )
)

print("\nBEST WEIGHTS FOUND:")
print(f"TF-IDF:        {best_weights[0]:.0%}")
print(f"Semantic:      {best_weights[1]:.0%}")
print(f"Collaborative: {best_weights[2]:.0%}")



# ==========================================
# 14. EVALUATE ALL FOUR MODELS
# ==========================================

print("\n" + "=" * 75)
print("FINAL MODEL COMPARISON")
print("=" * 75)

def evaluate_recommendation_list(recommendations):

    all_metrics = []

    recommended_movies = set()

    for record in user_records:

        relevant_movies = record["test_relevant"]

        user_recommendations = recommendations(record)

        metrics = calculate_metrics(
            user_recommendations,
            relevant_movies
        )

        all_metrics.append(metrics)

        recommended_movies.update(user_recommendations)
        
    metrics_array = np.array(all_metrics)

    return {
        "Precision@10": metrics_array[:, 0].mean(),
        "Recall@10": metrics_array[:, 1].mean(),
        "NDCG@10": metrics_array[:, 2].mean(),
        "Catalog Coverage": (
            len(recommended_movies) / len(movies)
        )
    }


# ------------------------------------------
# MODEL 1: TF-IDF
# ------------------------------------------

tfidf_metrics = evaluate_recommendation_list(
    lambda record: record["tfidf_recommendations"]
)


# ------------------------------------------
# MODEL 2: SEMANTIC
# ------------------------------------------

semantic_metrics = evaluate_recommendation_list(
    lambda record: record["semantic_recommendations"]
)

positive_semantic_metrics = evaluate_recommendation_list(
    lambda record: record["positive_semantic_recommendations"]
)

# ------------------------------------------
# MODEL 3: COLLABORATIVE
# ------------------------------------------

collaborative_metrics = evaluate_recommendation_list(
    lambda record: record["collaborative_recommendations"]
)


# ------------------------------------------
# MODEL 4: OPTIMIZED HYBRID
# ------------------------------------------

def get_optimized_hybrid_recommendations(record):

    tfidf_weight, semantic_weight, collaborative_weight = best_weights

    hybrid_scores = (
        tfidf_weight * record["tfidf_scores"] +
        semantic_weight * record["positive_semantic_scores"] +
        collaborative_weight * record["collaborative_scores"]
    )

    return get_top_recommendations(
        hybrid_scores,
        record["excluded_indices"]
    )


hybrid_metrics = evaluate_recommendation_list(
    get_optimized_hybrid_recommendations
)


# ------------------------------------------
# COMBINE RESULTS
# ------------------------------------------

test_results = pd.DataFrame([
    {
        "Model": "TF-IDF",
        **tfidf_metrics
    },
    {
        "Model": "Semantic",
        **semantic_metrics
    },
    {
        "Model": "Personalized Semantic",
        **positive_semantic_metrics
    },
    {
        "Model": "Collaborative",
        **collaborative_metrics
    },
    {
        "Model": "Optimized Hybrid",
        **hybrid_metrics
    }
])


# Sort by NDCG@10
test_results = test_results.sort_values(
    "NDCG@10",
    ascending=False
).reset_index(drop=True)


print(
    test_results.to_string(
        index=False,
        formatters={
            "Precision@10": "{:.4f}".format,
            "Recall@10": "{:.4f}".format,
            "NDCG@10": "{:.4f}".format,
            "Catalog Coverage": "{:.2%}".format
        }
    )
)


# ==========================================
# 15. FINAL ANALYSIS
# ==========================================

print("\n" + "=" * 75)
print("FILMFINDER FINAL EVALUATION")
print("=" * 75)

print("Users evaluated:", actual_users)
print("Training/validation/testing split: 70/15/15")
print("Configurations tested:", len(weight_combinations))
print("Relevance threshold:", RELEVANCE_THRESHOLD)
print("Recommendations per user:", TOP_K)

print("\nOptimized hybrid weights:")
print(f"TF-IDF:        {best_weights[0]:.0%}")
print(f"Semantic:      {best_weights[1]:.0%}")
print(f"Collaborative: {best_weights[2]:.0%}")


# Compare optimized hybrid against collaborative filtering
collaborative_ndcg = collaborative_metrics["NDCG@10"]
hybrid_ndcg = hybrid_metrics["NDCG@10"]

print("\nHYBRID VS. COLLABORATIVE FILTERING")

print(
    f"Collaborative NDCG@10: {collaborative_ndcg:.4f}"
)

print(
    f"Hybrid NDCG@10:         {hybrid_ndcg:.4f}"
)

difference = hybrid_ndcg - collaborative_ndcg

print(f"Difference:             {difference:+.4f}")

if difference > 0:

    print(
        "\nThe optimized hybrid outperformed collaborative filtering "
        "on NDCG@10."
    )

elif difference < 0:

    print(
        "\nCollaborative filtering outperformed the optimized hybrid "
        "on NDCG@10."
    )

else:

    print(
        "\nBoth models achieved the same NDCG@10."
    )


print("\nEvaluation complete!")
