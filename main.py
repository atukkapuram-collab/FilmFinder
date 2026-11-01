
from src.hybrid import load_hybrid_model, recommend_hybrid


def select_movies(movies):
    """Let users select movies and rate them."""

    user_preferences = {}

    while True:

        movie_title = input(
            "\nEnter a movie you've watched "
            "(or press Enter to finish): "
        ).strip()

        if not movie_title:
            break

        # Search for matching movie titles
        search_words = movie_title.lower().split()

        movie_matches = movies[
            movies["title"].str.lower().apply(
                lambda title: all(
                    word in title for word in search_words
                )
            )
        ]

        if movie_matches.empty:
            print("Movie not found. Try another title.")
            continue

        # Let the user choose if multiple movies match
        if len(movie_matches) > 1:

            print("\nMultiple movies found:")

            for i, row in enumerate(
                movie_matches.itertuples(),
                start=1
            ):
                print(f"{i}. {row.title}")

            try:
                choice = int(input("\nChoose a movie number: "))
            except ValueError:
                print("Please enter a valid number.")
                continue

            if choice < 1 or choice > len(movie_matches):
                print("Invalid selection.")
                continue

            movie = movie_matches.iloc[choice - 1]

        else:
            movie = movie_matches.iloc[0]

        movie_id = movie["movieId"]

        if movie_id in user_preferences:
            print("You've already rated that movie.")
            continue

        # Ask the user to rate the movie
        while True:

            try:
                rating = float(
                    input(
                        f"How would you rate {movie['title']}? "
                        "(0.5–5.0): "
                    )
                )

                if rating < 0.5 or rating > 5.0:
                    print("Rating must be between 0.5 and 5.0.")
                    continue

                if rating * 2 != int(rating * 2):
                    print("Please use increments of 0.5.")
                    continue

                break

            except ValueError:
                print("Please enter a valid rating.")

        user_preferences[movie_id] = rating

        print(f"Added {movie['title']} ({rating}/5).")

    return user_preferences


def main():

    print("=" * 50)
    print("             FILMFINDER")
    print("=" * 50)

    # Load recommendation engine
    print("\nLoading recommendation engine...")

    model = load_hybrid_model()

    movies = model["movies"]

    print(f"Loaded {len(movies)} movies.")
    print("\nLet's build your movie profile!")

    # Collect user preferences
    user_preferences = select_movies(movies)

    if not user_preferences:
        print("\nPlease rate at least one movie to continue.")
        return

    print(
        f"\nYou've rated {len(user_preferences)} movies."
    )

    # Generate recommendations
    print("\nFinding movies you might enjoy...")

    recommendations = recommend_hybrid(
        user_preferences,
        model,
        limit=10
    )

    if recommendations.empty:
        print("\nWe couldn't generate recommendations.")
        return

    # Display recommendations
    print("\n" + "=" * 50)
    print("          YOUR RECOMMENDATIONS")
    print("=" * 50)

    for number, row in enumerate(
        recommendations.itertuples(index=False),
        start=1
    ):

        print(f"\n{number}. {row.title}")
        print(f"   Genres: {row.genres}")
        print(f"   Final score: {row.final_score:.5f}")

    print("\nEnjoy discovering your next movie!")


if __name__ == "__main__":
    main()
