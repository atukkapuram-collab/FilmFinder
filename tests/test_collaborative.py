import pandas as pd

from src.collaborative import (
    load_collaborative_model,
    recommend_for_user
)

# Load model
ratings, rating_matrix, user_similarity, user_means = (
    load_collaborative_model()
)

# Test with User 1
user_id = 1
print("User's average rating:", user_means[user_id])

recommendations = recommend_for_user(
    user_id,
    ratings,
    rating_matrix,
    user_similarity,
    user_means
)

# Load movie titles
movies = pd.read_csv("data/movies.csv")

# Connect recommendations to movie titles
recommendations = recommendations.merge(
    movies[["movieId", "title"]],
    on="movieId"
)

print("\nRecommendations for User", user_id)

print(
    recommendations[
        ["title", "predicted_rating", "num_users"]
    ].to_string(index=False)
)