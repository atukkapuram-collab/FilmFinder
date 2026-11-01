from pathlib import Path

import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def load_collaborative_model(ratings=None):

    if ratings is None:
        project_root = Path(__file__).resolve().parent.parent
        ratings = pd.read_csv(project_root / "data" / "ratings.csv")

    # Create user-movie rating matrix
    rating_matrix = ratings.pivot(
        index="userId",
        columns="movieId",
        values="rating"
    )

    # Calculate each user's average rating
    user_means = rating_matrix.mean(axis=1)

    # Center ratings around each user's average
    centered_matrix = rating_matrix.sub(
        user_means,
        axis=0
    )

    # Replace missing ratings with 0
    centered_matrix = centered_matrix.fillna(0)

    # Calculate similarity between users
    user_similarity = cosine_similarity(
        centered_matrix
    )

    # Convert similarity scores into a DataFrame
    user_similarity = pd.DataFrame(
        user_similarity,
        index=rating_matrix.index,
        columns=rating_matrix.index
    )

    return ratings, rating_matrix, user_similarity, user_means

def recommend_for_user(
    user_id,
    ratings,
    rating_matrix,
    user_similarity,
    user_means,
    limit=10,
    neighbor_count=50
):

    # Get similarity scores for the selected user
    similar_users = user_similarity[user_id].drop(user_id)

    # Sort users by similarity
    similar_users = similar_users.sort_values(
        ascending=False
    )

    # Keep only users with positive similarity
    similar_users = similar_users[similar_users > 0]

    # Select the top N most similar users, based on the configured neighbor count
    similar_users = similar_users.head(neighbor_count)

    # Get movies the selected user hasn't rated
    user_ratings = rating_matrix.loc[user_id]

    unrated_movies = user_ratings[user_ratings.isna()].index

    # Calculate recommendations using similar users
    recommendations = {}

    for movie_id in unrated_movies:

        # Find similar users who rated this movie
        movie_ratings = rating_matrix[movie_id].dropna()

        relevant_users = similar_users.index.intersection(
            movie_ratings.index
        )

        if len(relevant_users) < 3:
            continue

        # Weighted average of their ratings
        weights = similar_users[relevant_users]
        scores = movie_ratings[relevant_users]

        # Calculate how much each similar user deviates
        # from their personal average
        rating_deviations = (
            scores - user_means[relevant_users]
        )

        # Calculate the weighted average deviation
        weighted_deviation = (
            (weights * rating_deviations).sum()
            / weights.abs().sum()
        )

        # Reduce extreme adjustments when fewer users rated a movie
        shrinkage = len(relevant_users) / (len(relevant_users) + 10)

        weighted_deviation *= shrinkage

        # Adjust the target user's average rating
        predicted_rating = (
            user_means[user_id] + weighted_deviation
        )
        # Keep predictions within the 0.5–5.0 rating scale
        #print(
        #    f"Movie {movie_id}: "
        #    f"raw prediction = {predicted_rating:.3f}"
        #)

        predicted_rating = max(0.5, min(5.0, predicted_rating))       
        
        recommendations[movie_id] = {
            "predicted_rating": predicted_rating,
            "num_users": len(relevant_users)
        }

    # Sort recommendations by predicted rating
    top_movies = sorted(
        recommendations.items(),
        key=lambda x: x[1]["predicted_rating"],
        reverse=True
    )[:limit]

    return pd.DataFrame([
        {
            "movieId": movie_id,
            "predicted_rating": data["predicted_rating"],
            "num_users": data["num_users"]
        }
        for movie_id, data in top_movies
    ])


def recommend_for_new_user(
    user_preferences,
    rating_matrix,
    user_means,
    limit=10,
    neighbor_count=50,
    min_overlap=2
):

    # Keep only movies that the new user actually rated
    profile_ratings = pd.Series({
        movie_id: rating
        for movie_id, rating in user_preferences.items()
        if rating is not None and movie_id in rating_matrix.columns
    })

    # Require at least two rated movies
    if len(profile_ratings) < min_overlap:
        return pd.DataFrame()

    # Calculate the new user's average rating
    profile_mean = profile_ratings.mean()

    # Find existing users with similar rating patterns
    similarities = {}

    for user_id, user_ratings in rating_matrix.iterrows():

        # Find movies both users have rated
        common_movies = profile_ratings.index.intersection(
            user_ratings.dropna().index
        )

        if len(common_movies) < min_overlap:
            continue

        # Center ratings around each user's personal average
        new_user_values = (
            profile_ratings.loc[common_movies].to_numpy()
            - profile_mean
        )

        existing_user_values = (
            user_ratings.loc[common_movies].to_numpy()
            - user_means[user_id]
        )

        # Skip users whose ratings have no variation
        if (
            np.linalg.norm(new_user_values) == 0
            or np.linalg.norm(existing_user_values) == 0
        ):
            continue

        # Calculate similarity between rating patterns
        similarity = cosine_similarity(
            [new_user_values],
            [existing_user_values]
        )[0][0]

        # Reduce similarity when users share very few ratings
        similarity *= len(common_movies) / (
            len(common_movies) + 5
        )

        if similarity > 0:
            similarities[user_id] = similarity

    # Select the most similar users
    similar_users = pd.Series(similarities).sort_values(
        ascending=False
    ).head(neighbor_count)

    if similar_users.empty:
        return pd.DataFrame()

    # Exclude every movie the new user already selected
    selected_movies = set(user_preferences.keys())

    recommendations = {}

    # Evaluate movies the user has not selected
    for movie_id in rating_matrix.columns:

        if movie_id in selected_movies:
            continue

        # Find similar users who rated this movie
        movie_ratings = rating_matrix[movie_id].dropna()

        relevant_users = similar_users.index.intersection(
            movie_ratings.index
        )

        if len(relevant_users) < 3:
            continue

        # Get similarity weights and movie ratings
        weights = similar_users[relevant_users]
        scores = movie_ratings[relevant_users]

        # Calculate how much each user deviates from their average
        rating_deviations = (
            scores - user_means[relevant_users]
        )

        # Calculate weighted average deviation
        weighted_deviation = (
            (weights * rating_deviations).sum()
            / weights.abs().sum()
        )

        # Reduce extreme predictions when fewer users rated a movie
        shrinkage = len(relevant_users) / (
            len(relevant_users) + 10
        )

        weighted_deviation *= shrinkage

        # Predict the new user's rating
        predicted_rating = (
            profile_mean + weighted_deviation
        )

        # Keep predictions within the 0.5–5.0 rating scale
        predicted_rating = max(
            0.5,
            min(5.0, predicted_rating)
        )

        recommendations[movie_id] = {
            "predicted_rating": predicted_rating,
            "num_users": len(relevant_users)
        }

    # Sort recommendations by predicted rating
    top_movies = sorted(
        recommendations.items(),
        key=lambda x: x[1]["predicted_rating"],
        reverse=True
    )[:limit]

    return pd.DataFrame([
        {
            "movieId": movie_id,
            "predicted_rating": data["predicted_rating"],
            "num_users": data["num_users"]
        }
        for movie_id, data in top_movies
    ])



