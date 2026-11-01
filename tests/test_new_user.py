
import pandas as pd

from src.collaborative import (
    load_collaborative_model,
    recommend_for_new_user
)


# Load the MovieLens collaborative-filtering data
print("Loading collaborative model...")

ratings, rating_matrix, user_similarity, user_means = (
    load_collaborative_model()
)


# Simulate a new user's movie preferences
# These are MovieLens movieId values
user_preferences = {
    1: 5.0,      # Toy Story
    296: 2.0,    # Pulp Fiction
    356: 4.0,    # Forrest Gump
    318: 5.0,    # Shawshank Redemption
    2571: 2.0    # The Matrix
}


# Generate collaborative recommendations
print("\nGenerating recommendations for a new user...")

recommendations = recommend_for_new_user(
    user_preferences,
    rating_matrix,
    user_means,
    limit=10
)

# Analyze prediction results
if not recommendations.empty:

    print("\n========== MODEL DIAGNOSTICS ==========")

    print(
        f"Average predicted rating: "
        f"{recommendations['predicted_rating'].mean():.3f}"
    )

    print(
        f"Lowest predicted rating: "
        f"{recommendations['predicted_rating'].min():.3f}"
    )

    print(
        f"Highest predicted rating: "
        f"{recommendations['predicted_rating'].max():.3f}"
    )

    print(
        f"Predictions at 5.0: "
        f"{(recommendations['predicted_rating'] == 5.0).sum()}"
    )

    print(
        f"Average supporting users: "
        f"{recommendations['num_users'].mean():.1f}"
    )

# Display recommendations
movies = pd.read_csv("data/movies.csv")

if recommendations.empty:
    print("\nNo recommendations could be generated.")
else:

    recommendations = recommendations.merge(
        movies[["movieId", "title"]],
        on="movieId",
        how="left"
    )

    print("\nNEW USER COLLABORATIVE RECOMMENDATIONS")
    print("=" * 55)

    for row in recommendations.itertuples(index=False):

        print(f"\n{row.title}")
        print(f"Predicted rating: {row.predicted_rating:.2f}/5")
        print(f"Users supporting prediction: {row.num_users}")
