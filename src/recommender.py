
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_recommender():
    """Load movie data and generate TF-IDF feature matrices."""

    # Load datasets
    movies = pd.read_csv(DATA_DIR / "movies.csv")
    tags = pd.read_csv(DATA_DIR / "tags.csv")
    links = pd.read_csv(DATA_DIR / "links.csv")
    metadata = pd.read_csv(
        DATA_DIR / "movies_metadata.csv",
        low_memory=False
    )

    # Combine tags for each movie
    movie_tags = (
        tags.groupby("movieId")["tag"]
        .agg(" ".join)
        .reset_index()
    )

    movies = movies.merge(
        movie_tags,
        on="movieId",
        how="left"
    )

    movies["tag"] = movies["tag"].fillna("")

    # Connect MovieLens movies to IMDb IDs
    movies = movies.merge(
        links[["movieId", "imdbId"]],
        on="movieId",
        how="left"
    )

    # Convert IMDb IDs into the format used by the metadata dataset
    movies["imdbId"] = movies["imdbId"].apply(
        lambda x: f"tt{int(x):07d}" if pd.notna(x) else None
    )

    # Prepare plot metadata
    metadata = metadata[["imdb_id", "overview"]].copy()

    metadata = metadata.dropna(subset=["imdb_id"])
    metadata["imdb_id"] = metadata["imdb_id"].astype(str).str.strip()
    metadata = metadata.drop_duplicates(subset=["imdb_id"])

    # Connect plot descriptions to movies
    movies = movies.merge(
        metadata,
        left_on="imdbId",
        right_on="imdb_id",
        how="left"
    )

    # Clean missing text
    movies["overview"] = movies["overview"].fillna("")
    movies["genres"] = (
        movies["genres"]
        .fillna("")
        .str.replace("|", " ", regex=False)
    )

    # Generate genre TF-IDF matrix
    genre_vectorizer = TfidfVectorizer()
    genre_matrix = genre_vectorizer.fit_transform(movies["genres"])

    # Generate tag TF-IDF matrix
    tag_vectorizer = TfidfVectorizer()
    tag_matrix = tag_vectorizer.fit_transform(movies["tag"])

    # Generate plot TF-IDF matrix
    plot_vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=20000,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8
    )

    plot_matrix = plot_vectorizer.fit_transform(movies["overview"])

    return movies, genre_matrix, tag_matrix, plot_matrix
