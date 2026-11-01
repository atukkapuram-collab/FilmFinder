
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.collaborative import load_collaborative_model


# ==========================================
# 1. LOAD AND SPLIT DATA
# ==========================================

ratings = pd.read_csv("data/ratings.csv")

# First, separate the final testing set (15%)
development_ratings, test_ratings = train_test_split(
    ratings,
    test_size=0.15,
    random_state=42
)

# Split the remaining 85% into training (70%) and validation (15%)
train_ratings, validation_ratings = train_test_split(
    development_ratings,
    test_size=3 / 17,
    random_state=42
)

print("Training ratings:", len(train_ratings))
print("Validation ratings:", len(validation_ratings))
print("Testing ratings:", len(test_ratings))


# ==========================================
# 2. CREATE PREDICTION FUNCTION
# ==========================================

def predict_ratings(
    evaluation_data,
    rating_matrix,
    user_similarity,
    user_means,
    global_mean,
    neighbor_count
):

    actual_ratings = []
    predicted_ratings = []
    baseline_predictions = []

    collaborative_predictions = 0

    for row in evaluation_data.itertuples(index=False):

        user_id = row.userId
        movie_id = row.movieId
        actual_rating = row.rating

        # Use the user's average as the baseline.
        # If the user is unknown, use the global average.
        if user_id in rating_matrix.index:
            baseline_rating = user_means[user_id]
        else:
            baseline_rating = global_mean

        predicted_rating = baseline_rating

        # Attempt collaborative prediction if user and movie are known
        if (
            user_id in rating_matrix.index
            and movie_id in rating_matrix.columns
        ):

            # Find the most similar users
            similar_users = user_similarity[user_id].drop(user_id)

            similar_users = similar_users.sort_values(ascending=False)
            similar_users = similar_users[
                similar_users > 0
            ].head(neighbor_count)

            # Find users who rated this movie
            movie_ratings = rating_matrix[movie_id].dropna()

            relevant_users = similar_users.index.intersection(
                movie_ratings.index
            )

            # Require at least 3 relevant users
            if len(relevant_users) >= 3:

                weights = similar_users[relevant_users]
                scores = movie_ratings[relevant_users]

                # Calculate rating deviations
                rating_deviations = (
                    scores - user_means[relevant_users]
                )

                # Calculate weighted deviation
                weighted_deviation = (
                    (weights * rating_deviations).sum()
                    / weights.abs().sum()
                )

                # Apply shrinkage
                shrinkage = len(relevant_users) / (
                    len(relevant_users) + 10
                )

                weighted_deviation *= shrinkage

                # Calculate personalized prediction
                predicted_rating = (
                    baseline_rating + weighted_deviation
                )

                collaborative_predictions += 1

        # Keep prediction within rating scale
        predicted_rating = max(
            0.5,
            min(5.0, predicted_rating)
        )

        actual_ratings.append(actual_rating)
        predicted_ratings.append(predicted_rating)
        baseline_predictions.append(baseline_rating)

    return (
        actual_ratings,
        predicted_ratings,
        baseline_predictions,
        collaborative_predictions
    )


# ==========================================
# 3. TUNE NEIGHBOR COUNT ON VALIDATION DATA
# ==========================================

# Train using training data ONLY
_, rating_matrix, user_similarity, user_means = (
    load_collaborative_model(train_ratings)
)

global_mean = train_ratings["rating"].mean()

neighbor_counts = [5, 10, 15, 20, 30, 50]

results = []

print("\n========== VALIDATION EXPERIMENTS ==========")

for neighbor_count in neighbor_counts:

    actual, predicted, baseline, cf_count = predict_ratings(
        validation_ratings,
        rating_matrix,
        user_similarity,
        user_means,
        global_mean,
        neighbor_count
    )

    mae = mean_absolute_error(actual, predicted)

    rmse = np.sqrt(
        mean_squared_error(actual, predicted)
    )

    baseline_mae = mean_absolute_error(actual, baseline)

    coverage = cf_count / len(actual) * 100

    results.append({
        "Neighbors": neighbor_count,
        "MAE": mae,
        "RMSE": rmse,
        "CF Coverage (%)": coverage,
        "Baseline MAE": baseline_mae
    })


results_df = pd.DataFrame(results)

print(
    results_df.to_string(
        index=False,
        formatters={
            "MAE": "{:.3f}".format,
            "RMSE": "{:.3f}".format,
            "CF Coverage (%)": "{:.1f}".format,
            "Baseline MAE": "{:.3f}".format
        }
    )
)


# ==========================================
# 4. SELECT BEST NEIGHBOR COUNT
# ==========================================

best_result = results_df.loc[
    results_df["MAE"].idxmin()
]

best_neighbor_count = int(best_result["Neighbors"])

print("\n========== SELECTED CONFIGURATION ==========")

print("Best neighbor count:", best_neighbor_count)
print(f"Validation MAE: {best_result['MAE']:.3f}")
print(f"Validation RMSE: {best_result['RMSE']:.3f}")


# ==========================================
# 5. RETRAIN USING TRAINING + VALIDATION
# ==========================================

final_training_ratings = pd.concat(
    [train_ratings, validation_ratings]
)

_, final_matrix, final_similarity, final_means = (
    load_collaborative_model(final_training_ratings)
)

final_global_mean = final_training_ratings["rating"].mean()


# ==========================================
# 6. FINAL EVALUATION ON TEST DATA
# ==========================================

actual, predicted, baseline, cf_count = predict_ratings(
    test_ratings,
    final_matrix,
    final_similarity,
    final_means,
    final_global_mean,
    best_neighbor_count
)

final_mae = mean_absolute_error(actual, predicted)

final_rmse = np.sqrt(
    mean_squared_error(actual, predicted)
)

baseline_mae = mean_absolute_error(actual, baseline)

baseline_rmse = np.sqrt(
    mean_squared_error(actual, baseline)
)

final_coverage = cf_count / len(actual) * 100


# ==========================================
# 7. DISPLAY FINAL RESULTS
# ==========================================

print("\n========== FINAL TEST RESULTS ==========")

print("Selected neighbors:", best_neighbor_count)
print("Test predictions:", len(actual))
print(f"Collaborative filtering coverage: {final_coverage:.1f}%")

print("\nCollaborative Filtering:")
print(f"MAE:  {final_mae:.3f}")
print(f"RMSE: {final_rmse:.3f}")

print("\nUser Average Baseline:")
print(f"MAE:  {baseline_mae:.3f}")
print(f"RMSE: {baseline_rmse:.3f}")
