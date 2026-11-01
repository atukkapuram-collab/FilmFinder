import numpy as np
from src.recommender import load_recommender
from sentence_transformers import SentenceTransformer

# Load the current movie dataset
movies, _, _, _ = load_recommender()

# Load saved embeddings
embeddings = np.load("data/plot_embeddings.npy")

print("\n--- BASIC CHECKS ---")
print("Movies:", len(movies))
print("Embeddings:", len(embeddings))

# Display the first 10 movies in their current order
print("\n--- FIRST 10 MOVIES ---")
for i in range(10):
    print(f"{i}: {movies.iloc[i]['movieId']} | {movies.iloc[i]['title']}")

# Check whether movie IDs are unique
print("\n--- MOVIE ID CHECK ---")
print("Unique movie IDs:", movies["movieId"].nunique())
print("Total movie rows:", len(movies))

print("\n--- EMBEDDING ALIGNMENT TEST ---")

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Test several positions throughout the dataset
test_indices = [0, 1, 100, 1000, 5000, 9741]

# Get the plot descriptions at those positions
test_overviews = movies.iloc[test_indices]["overview"].tolist()

# Generate fresh embeddings
fresh_embeddings = model.encode(
    test_overviews,
    convert_to_numpy=True,
    normalize_embeddings=True
)

# Compare fresh embeddings with saved embeddings
for i, index in enumerate(test_indices):

    similarity = np.dot(
        embeddings[index],
        fresh_embeddings[i]
    )

    print(
        f"{movies.iloc[index]['title']}: "
        f"similarity = {similarity:.6f}"
    )