
const COLLECTION_KEY = "filmFinderCollection";

// ========================================
// COLLECTION STORAGE
// ========================================

function getCollection() {
    try {
        const savedCollection = localStorage.getItem(COLLECTION_KEY);

        if (!savedCollection) {
            return [];
        }

        const collection = JSON.parse(savedCollection);
        return Array.isArray(collection) ? collection : [];

    } catch (error) {
        console.error("Unable to load movie collection:", error);
        return [];
    }
}


function saveCollection(collection) {
    try {
        localStorage.setItem(
            COLLECTION_KEY,
            JSON.stringify(collection)
        );

        // Notify other parts of FilmFinder that the collection changed
        window.dispatchEvent(new CustomEvent("filmFinderCollectionUpdated", {
            detail: { collection }
        }));

        return true;

    } catch (error) {
        console.error("Unable to save movie collection:", error);
        return false;
    }
}


// ========================================
// MOVIE LOOKUP
// ========================================

function getMovie(movieId) {
    return getCollection().find(
        movie => movie.movieId === movieId
    ) || null;
}


// ========================================
// MOVIE MANAGEMENT
// ========================================

function addOrUpdateMovie(movie, updates = {}) {
    const collection = getCollection();

    const existingIndex = collection.findIndex(
        saved => saved.movieId === movie.movieId
    );

    const existingMovie = existingIndex !== -1
        ? collection[existingIndex]
        : {};

    const updatedMovie = {
        ...existingMovie,
        movieId: movie.movieId,
        title: movie.title || existingMovie.title,
        genres: movie.genres || existingMovie.genres || "",
        posterUrl: movie.posterUrl || existingMovie.posterUrl || null,
        watched: existingMovie.watched || false,
        watchlist: existingMovie.watchlist || false,
        favorite: existingMovie.favorite || false,
        rating: existingMovie.rating || 0,
        selectedForRecommendations:
            existingMovie.selectedForRecommendations || false,
        ...updates
    };

    // A watched movie cannot remain on the watchlist
    if (updatedMovie.watched) {
        updatedMovie.watchlist = false;
    }

    if (existingIndex !== -1) {
        collection[existingIndex] = updatedMovie;
    } else {
        collection.push(updatedMovie);
    }

    return saveCollection(collection);
}


function updateMovie(movieId, updates) {
    const collection = getCollection();

    const movieIndex = collection.findIndex(
        movie => movie.movieId === movieId
    );

    if (movieIndex === -1) {
        return false;
    }

    collection[movieIndex] = {
        ...collection[movieIndex],
        ...updates
    };

    // Automatically remove watched movies from the watchlist
    if (collection[movieIndex].watched) {
        collection[movieIndex].watchlist = false;
    }

    return saveCollection(collection);
}


function removeMovie(movieId) {
    const collection = getCollection();

    const updatedCollection = collection.filter(
        movie => movie.movieId !== movieId
    );

    return saveCollection(updatedCollection);
}


// ========================================
// DISCOVER SELECTION MANAGEMENT
// ========================================

function setSelectedForRecommendations(movieId, selected) {
    return updateMovie(movieId, {
        selectedForRecommendations: Boolean(selected)
    });
}


function getSelectedForRecommendations() {
    return getCollection().filter(
        movie => movie.selectedForRecommendations
    );
}


function clearRecommendationSelections() {
    const collection = getCollection();

    const updatedCollection = collection.map(movie => ({
        ...movie,
        selectedForRecommendations: false
    }));

    return saveCollection(updatedCollection);
}


// ========================================
// COLLECTION PAGE DISPLAY
// ========================================

function renderCollectionPage() {
    const watchedContainer = document.getElementById("watched-movies");

    // Only run this section on the My Movies page
    if (!watchedContainer) {
        return;
    }

    const watchlistContainer = document.getElementById("watchlist-movies");
    const favoritesContainer = document.getElementById("favorite-movies");

    const collection = getCollection();

    const watchedMovies = collection.filter(movie => movie.watched);
    const watchlistMovies = collection.filter(movie => movie.watchlist);
    const favoriteMovies = collection.filter(movie => movie.favorite);

    // Update statistics
    document.getElementById("watched-count").textContent =
        watchedMovies.length;

    document.getElementById("watchlist-count").textContent =
        watchlistMovies.length;

    document.getElementById("favorites-count").textContent =
        favoriteMovies.length;

    const ratedMovies = watchedMovies.filter(movie => movie.rating > 0);

    const averageRating = ratedMovies.length > 0
        ? ratedMovies.reduce((total, movie) => total + movie.rating, 0)
            / ratedMovies.length
        : null;

    document.getElementById("average-rating").textContent =
        averageRating !== null
            ? `${averageRating.toFixed(1)} / 5`
            : "—";

    // Update section counts
    document.getElementById("watched-section-count").textContent =
        `${watchedMovies.length} movies`;

    document.getElementById("watchlist-section-count").textContent =
        `${watchlistMovies.length} movies`;

    document.getElementById("favorites-section-count").textContent =
        `${favoriteMovies.length} movies`;

    // Render each collection
    renderMovieSection(watchedContainer, watchedMovies, "watched");
    renderMovieSection(watchlistContainer, watchlistMovies, "watchlist");
    renderMovieSection(favoritesContainer, favoriteMovies, "favorite");
    
    // Notify other scripts that the collection display has been refreshed
    window.dispatchEvent(
        new CustomEvent("filmFinderCollectionRendered")
    );
}


// ========================================
// RENDER INDIVIDUAL MOVIE SECTIONS
// ========================================

function renderMovieSection(container, movies, category) {
    if (!container) {
        return;
    }

    // Preserve the original empty-state message
    if (movies.length === 0) {
        container.querySelectorAll(".collection-movie-card").forEach(
            card => card.remove()
        );

        const emptyState = container.querySelector(".collection-empty");

        if (emptyState) {
            emptyState.style.display = "flex";
        }

        return;
    }

    container.innerHTML = "";

    movies.forEach(movie => {
        const card = document.createElement("div");
        card.className = "collection-movie-card";

        // Poster
        if (movie.posterUrl) {
            const poster = document.createElement("img");
            poster.src = movie.posterUrl;
            poster.alt = `Poster for ${movie.title}`;
            poster.className = "collection-poster";

            poster.onerror = function () {
                poster.style.display = "none";
            };

            card.appendChild(poster);
        } else {
            const placeholder = document.createElement("div");
            placeholder.className =
                "collection-poster-placeholder poster-placeholder";

            card.appendChild(placeholder);
        }

        // Movie information
        const info = document.createElement("div");
        info.className = "collection-movie-info";

        const title = document.createElement("h3");
        title.textContent = movie.title;

        const genres = document.createElement("p");
        genres.textContent = movie.genres || "Genre unavailable";

        info.appendChild(title);
        info.appendChild(genres);

        // Rating for watched movies
        if (category === "watched") {
            const ratingSelect = document.createElement("select");
            ratingSelect.className = "movie-rating";

            const defaultOption = document.createElement("option");
            defaultOption.value = "0";
            defaultOption.textContent = "Rate movie";
            defaultOption.selected = !movie.rating;

            ratingSelect.appendChild(defaultOption);

            for (let rating = 0.5; rating <= 5; rating += 0.5) {
                const option = document.createElement("option");
                option.value = rating;
                option.textContent = `${rating} / 5`;
                option.selected = Number(movie.rating) === rating;

                ratingSelect.appendChild(option);
            }

            ratingSelect.addEventListener("change", function () {
                const success = updateMovie(movie.movieId, {
                    rating: Number(ratingSelect.value)
                });

                if (success) {
                    renderCollectionPage();
                } else {
                    alert("Unable to update movie rating.");
                }
            });

            info.appendChild(ratingSelect);
            // Selection control for personalized recommendations
            if (Number(movie.rating) > 0) {
                const selectionLabel = document.createElement("label");
                selectionLabel.className = "recommendation-movie-selection";

                const selectionCheckbox = document.createElement("input");
                selectionCheckbox.type = "checkbox";
                selectionCheckbox.className = "recommendation-movie-checkbox";
                selectionCheckbox.value = movie.movieId;
                selectionCheckbox.dataset.movieId = movie.movieId;

                const selectionText = document.createElement("span");
                selectionText.textContent = "Use for recommendations";

                selectionLabel.appendChild(selectionCheckbox);
                selectionLabel.appendChild(selectionText);

                info.appendChild(selectionLabel);
            }
        }

        // Collection category buttons
        const actions = document.createElement("div");
        actions.className = "collection-actions";

        const categories = [
            { key: "watched", label: "Watched" },
            { key: "watchlist", label: "Watchlist" },
            { key: "favorite", label: "Favorite" }
        ];

        categories.forEach(item => {
            const button = document.createElement("button");
            button.className = "collection-action";

            const active = Boolean(movie[item.key]);

            button.textContent = active
                ? `✓ ${item.label}`
                : `+ ${item.label}`;

            if (active) {
                button.classList.add("active");
            }

            button.addEventListener("click", function () {
                const updates = {
                    [item.key]: !movie[item.key]
                };

                if (item.key === "watched" && movie.watched) {
                    updates.rating = 0;
                }

                if (updateMovie(movie.movieId, updates)) {
                    renderCollectionPage();
                } else {
                    alert("Unable to update your collection.");
                }
            });

            actions.appendChild(button);
        });

        info.appendChild(actions);

        // Remove movie completely
        const removeButton = document.createElement("button");
        removeButton.className = "remove-movie";
        removeButton.textContent = "Remove from collection";

        removeButton.addEventListener("click", function () {
            if (confirm(`Remove ${movie.title} from your entire collection?`)) {
                removeMovie(movie.movieId);
                renderCollectionPage();
            }
        });

        info.appendChild(removeButton);

        card.appendChild(info);
        container.appendChild(card);
    });
}


// ========================================
// PUBLIC COLLECTION API
// ========================================

window.FilmFinderCollection = {
    getAll: getCollection,
    getMovie,
    addOrUpdate: addOrUpdateMovie,
    update: updateMovie,
    remove: removeMovie,
    setSelectedForRecommendations,
    getSelectedForRecommendations,
    clearRecommendationSelections,
    render: renderCollectionPage
};


// ========================================
// INITIALIZE COLLECTION PAGE
// ========================================

document.addEventListener("DOMContentLoaded", function () {
    renderCollectionPage();
});
