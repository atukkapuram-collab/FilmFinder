import re
import pandas as pd
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from src.hybrid import load_hybrid_model, recommend_hybrid

app = Flask(__name__)

ALLOWED_GENRES = {
    "any",
    "Action",
    "Adventure",
    "Animation",
    "Children",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Fantasy",
    "Film-Noir",
    "Horror",
    "Musical",
    "Mystery",
    "Romance",
    "Sci-Fi",
    "Thriller",
    "War",
    "Western"
}

# Load the hybrid recommendation model once at startup
model = load_hybrid_model()

# Reuse the movie dataset loaded by the hybrid model
movies = model["movies"]

# Calculate movie popularity using MovieLens rating counts
ratings_path = Path(__file__).resolve().parent / "data" / "ratings.csv"

ratings = pd.read_csv(ratings_path)

movie_popularity = (
    ratings.groupby("movieId")
    .size()
    .reset_index(name="rating_count")
)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/discover")
def discover():
    return render_template("discover.html")

@app.route("/my-movies")
def my_movies():
    return render_template("my_movies.html")

@app.route("/about")
def about():
    return render_template("about.html")


# ========================================
# MOVIE SEARCH API
# ========================================

@app.route("/api/search")
def search_movies():
    query = request.args.get("q", "").strip()

    if len(query) < 2:
        return jsonify([])

    # Separate a trailing year or partial year from the title
    year_match = re.search(r"\s+(\d{1,4})$", query)
    year_prefix = None

    if year_match:
        year_prefix = year_match.group(1)
        query = query[:year_match.start()].strip()

    def normalize_title(title):
        title = str(title).lower().strip()

        # Remove release year for matching
        title = re.sub(r"\s*\(\d{4}\)$", "", title)

        # Convert trailing articles into standard title format
        for article in ["the", "a", "an"]:
            # Handle complete articles with or without a comma
            for suffix in [f", {article}", f" {article}"]:
                if title.endswith(suffix):
                    title = f"{article} {title[:-len(suffix)].strip()}"
                    break
            else:
                # Handle partially typed articles, such as "Matrix, Th"
                for length in range(1, len(article)):
                    for suffix in [
                        f", {article[:length]}",
                        f" {article[:length]}"
                    ]:
                        if title.endswith(suffix):
                            title = f"{article} {title[:-len(suffix)].strip()}"
                            break
                    else:
                        continue
                    break
                else:
                    continue

                break

            break

            # Handle partially typed articles, such as "Matrix, Th"
            for length in range(1, len(article)):
                partial_suffix = f", {article[:length]}"

                if title.endswith(partial_suffix):
                    title = f"{article} {title[:-len(partial_suffix)].strip()}"
                    break
            else:
                continue

            break

        return title
    query = re.sub(r"[,\\s-]+$", "", query).strip()
    normalized_query = normalize_title(query)

    results = movies.copy()

    results["normalized_title"] = results["title"].apply(
        normalize_title
    )

    matches = results[
        results["normalized_title"].str.contains(
            normalized_query,
            case=False,
            na=False,
            regex=False
        )
    ].copy()

    # If a year was provided, match movies whose release year starts with it
    if year_prefix:
        matches = matches[
            matches["title"].astype(str).str.extract(
                r"\((\d{4})\)\s*$"
            )[0].str.startswith(year_prefix, na=False)
        ]

    # Prioritize exact matches
    matches["match_rank"] = matches["normalized_title"].apply(
        lambda title: (
            0 if title == normalized_query
            else 1 if title.startswith(normalized_query)
            else 2
        )
    )

    matches = matches.sort_values(
        by=["match_rank", "title"]
    ).head(10)

    return jsonify(
        matches[["movieId", "title", "genres"]].to_dict(
            orient="records"
        )
    )

# ========================================
# POPULAR MOVIES API
# ========================================

@app.route("/api/popular")
def popular_movies():

    popular = movies.merge(
        movie_popularity,
        on="movieId",
        how="inner"
    )

    popular = popular.sort_values(
        by="rating_count",
        ascending=False
    ).head(10)

    popular["release_year"] = popular["title"].str.extract(r"\((\d{4})\)$")

    results = popular[
        ["movieId", "title", "genres", "rating_count", "overview", "release_year"]
    ].to_dict(orient="records")

    return jsonify(results)


# ========================================
# RECOMMENDATION API
# ========================================

@app.route("/api/recommend", methods=["POST"])
def generate_recommendations():

    data = request.get_json(silent=True) or {}

    preferences = data.get("preferences", {})
    genre = data.get("genre", "any")
    exclude_movie_ids = data.get("exclude_movie_ids", [])

    if not isinstance(genre, str):
        return jsonify({"error": "Invalid genre preference."}), 400

    if genre not in ALLOWED_GENRES:
        return jsonify({"error": "Unsupported genre preference."}), 400

    if not isinstance(preferences, dict):
        return jsonify({"error": "Invalid movie preferences."}), 400

    if len(preferences) < 5:
        return jsonify({
            "error": "Please rate at least five movies."
        }), 400

    try:
        user_preferences = {}

        for movie_id, rating in preferences.items():
            movie_id = int(movie_id)
            rating = float(rating)

            if not 0.5 <= rating <= 5:
                raise ValueError("Ratings must be between 0.5 and 5.")

            user_preferences[movie_id] = rating

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid movie IDs or ratings."}), 400

    # Generate personalized recommendations
    recommendations = recommend_hybrid(
        user_preferences,
        model,
        limit=10,
        preferred_genre=genre,
        exclude_movie_ids=exclude_movie_ids
    )

    if recommendations.empty:
        return jsonify({
            "error": "Unable to generate recommendations."
        }), 400

    # Convert results into JSON-friendly records
    results = recommendations[
        ["movieId", "title", "genres"]
    ].to_dict(orient="records")
    
    return jsonify(results)



if __name__ == "__main__":
    app.run(debug=True)
