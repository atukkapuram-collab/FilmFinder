
import numpy as np
from src.recommender import load_recommender

print("\nLoading movie dataset...")
movies, genre_matrix, tag_matrix, plot_matrix = load_recommender()

print("\nLoading embeddings...")
embeddings = np.load("data/plot_embeddings.npy")

# --------------------------------------
# 1. CHECK DATASET ALIGNMENT
# --------------------------------------

print("\n" + "=" * 55)
print("1. DATASET ALIGNMENT")
print("=" * 55)

print("Number of movies:", len(movies))
print("Number of embeddings:", len(embeddings))
print("Embedding dimensions:", embeddings.shape)

print("Unique movie IDs:", movies["movieId"].nunique())
print("Duplicate movie IDs:", movies["movieId"].duplicated().sum())

if len(movies) == len(embeddings):
    print("Row count check: PASSED")
else:
    print("Row count check: FAILED")

# --------------------------------------
# 2. CHECK EMBEDDING QUALITY
# --------------------------------------

print("\n" + "=" * 55)
print("2. EMBEDDING QUALITY")
print("=" * 55)

print("Data type:", embeddings.dtype)
print("Contains NaN:", np.isnan(embeddings).any())
print("Contains infinite values:", np.isinf(embeddings).any())

norms = np.linalg.norm(embeddings, axis=1)

print("Minimum vector norm:", norms.min())
print("Maximum vector norm:", norms.max())
print("Average vector norm:", norms.mean())

print("Zero vectors:", np.sum(norms == 0))
print("Very small vectors:", np.sum(norms < 1e-8))

# --------------------------------------
# 3. CHECK SIMILARITY DISTRIBUTION
# --------------------------------------

print("\n" + "=" * 55)
print("3. SIMILARITY DISTRIBUTION")
print("=" * 55)

# Randomly select 500 movies
rng = np.random.default_rng(42)

sample_indices = rng.choice(
    len(embeddings),
    size=min(500, len(embeddings)),
    replace=False
)

sample_embeddings = embeddings[sample_indices]

# Calculate cosine similarities
sample_norms = np.linalg.norm(
    sample_embeddings,
    axis=1,
    keepdims=True
)

normalized_embeddings = np.divide(
    sample_embeddings,
    sample_norms,
    out=np.zeros_like(sample_embeddings),
    where=sample_norms != 0
)

similarities = (
    normalized_embeddings @ normalized_embeddings.T
)

# Remove comparisons of movies against themselves
similarities = similarities[
    ~np.eye(len(similarities), dtype=bool)
]

print("Minimum similarity:", similarities.min())
print("Maximum similarity:", similarities.max())
print("Average similarity:", similarities.mean())
print("Median similarity:", np.median(similarities))

print("25th percentile:", np.percentile(similarities, 25))
print("75th percentile:", np.percentile(similarities, 75))

# --------------------------------------
# 4. CHECK MISSING PLOT DESCRIPTIONS
# --------------------------------------

print("\n" + "=" * 55)
print("4. MISSING PLOT DESCRIPTIONS")
print("=" * 55)

missing_overviews = movies["overview"].eq("").sum()

print("Movies without plot descriptions:", missing_overviews)
print("Movies with plot descriptions:", len(movies) - missing_overviews)

print("\nDiagnostic complete!")
