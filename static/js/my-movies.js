
document.addEventListener("DOMContentLoaded", function () {
    const recommendedMovieIds = new Set();

    const recommendAllButton = document.getElementById("recommend-all-button");
    const chooseMoviesButton = document.getElementById("select-recommendation-movies");
    const recommendSelectedButton = document.getElementById("recommend-selected-button");
    const selectionStatus = document.getElementById("recommendation-selection-status");
    const resultsContainer = document.getElementById("collection-recommendation-results");
    const watchedContainer = document.getElementById("watched-movies");

    if (
        !recommendAllButton ||
        !chooseMoviesButton ||
        !recommendSelectedButton ||
        !selectionStatus ||
        !resultsContainer ||
        !watchedContainer
    ) {
        return;
    }

    const SELECTION_STORAGE_KEY = "filmFinderRecommendationSelections";

    function loadSavedSelections() {
        try {
            const saved = JSON.parse(
                localStorage.getItem(SELECTION_STORAGE_KEY) || "[]"
            );

            return new Set(saved.map(String));
        } catch (error) {
            return new Set();
        }
    }

    const selectedMovieIds = loadSavedSelections();
    const selectionHistory = [];

    let selectionMode = selectedMovieIds.size > 0;
    let activeRecommendationMode = null;
    let requestSequence = 0;
    let lastPreferenceSignature = null;

    // ========================================
    // MOVIE SELECTION
    // ========================================

    function getRatedWatchedMovies() {
        return FilmFinderCollection.getAll().filter(movie =>
            movie.watched && Number(movie.rating) > 0
        );
    }

    function getSelectedRatedMovies() {
        return getRatedWatchedMovies().filter(movie =>
            selectedMovieIds.has(String(movie.movieId))
        );
    }

    function saveSelectedMovies() {
        localStorage.setItem(
            SELECTION_STORAGE_KEY,
            JSON.stringify(Array.from(selectedMovieIds))
        );
    }

    function updateSelectionStatus() {
        const count = selectedMovieIds.size;

        selectionStatus.textContent =
            count === 0
                ? "No movies selected."
                : `${count} movie${count === 1 ? "" : "s"} selected.`;

        recommendSelectedButton.disabled = count < 5;

        const undoButton = document.getElementById("undo-selection");

        if (undoButton) {
            undoButton.disabled = selectionHistory.length === 0;
        }
    }

    function saveSelectionHistory() {
        selectionHistory.push(new Set(selectedMovieIds));
    }

    function undoSelectionChange() {
        if (selectionHistory.length === 0) {
            return;
        }

        const previousSelection = selectionHistory.pop();

        selectedMovieIds.clear();

        previousSelection.forEach(movieId => {
            selectedMovieIds.add(movieId);
        });

        saveSelectedMovies();
        syncCheckboxes();

        if (activeRecommendationMode === "selected") {
            requestRecommendations(
                getSelectedRatedMovies(),
                "selected",
                true
            );
        }
    }

    function syncCheckboxes() {
        watchedContainer
            .querySelectorAll(".recommendation-movie-checkbox")
            .forEach(checkbox => {
                const movieId = String(checkbox.dataset.movieId);
                checkbox.checked = selectedMovieIds.has(movieId);
            });

        updateSelectionStatus();
    }

    function setSelectionMode(enabled) {
        selectionMode = enabled;

        watchedContainer.classList.toggle(
            "recommendation-selection-mode",
            selectionMode
        );

        chooseMoviesButton.textContent = selectionMode
            ? "Done Selecting"
            : "Choose Movies";

        syncCheckboxes();
    }

    // ========================================
    // RECOMMENDATION HELPERS
    // ========================================

    function getPreferenceSignature(movies) {
        return JSON.stringify(
            movies
                .map(movie => ({
                    movieId: String(movie.movieId),
                    rating: Number(movie.rating)
                }))
                .sort((a, b) => a.movieId.localeCompare(b.movieId))
        );
    }

    function showMessage(message) {
        resultsContainer.innerHTML = "";

        const paragraph = document.createElement("p");
        paragraph.textContent = message;

        resultsContainer.appendChild(paragraph);
    }

    function getMoviesForMode(mode) {
        return mode === "collection"
            ? getRatedWatchedMovies()
            : getSelectedRatedMovies();
    }

    // ========================================
    // GENERATE RECOMMENDATIONS
    // ========================================

    async function requestRecommendations(movies, mode, replaceResults = false) {
        // Switching modes always starts a fresh recommendation session
        if (activeRecommendationMode !== mode) {
            replaceResults = true;
        }

        activeRecommendationMode = mode;

        if (replaceResults) {
            recommendedMovieIds.clear();
            resultsContainer.innerHTML = "";
        }

        // A new request makes any older pending response outdated
        const currentRequest = ++requestSequence;

        const preferences = {};

        movies.forEach(movie => {
            preferences[movie.movieId] = Number(movie.rating);
        });

        lastPreferenceSignature = getPreferenceSignature(movies);

        if (movies.length < 5) {
            showMessage(
                mode === "collection"
                    ? `You need at least 5 rated watched movies. You currently have ${movies.length}.`
                    : `You need at least 5 selected rated watched movies. You currently have ${movies.length}.`
            );
            return;
        }

        let loadingMessage = document.createElement("p");
        loadingMessage.id = "recommendation-loading";
        loadingMessage.textContent = "Finding movies you'll love...";

        resultsContainer.appendChild(loadingMessage);

        recommendAllButton.disabled = true;
        recommendSelectedButton.disabled = true;

        try {
            const response = await fetch("/api/recommend", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    preferences: preferences,
                    genre: "any",
                    exclude_movie_ids: Array.from(recommendedMovieIds)
                })
            });

            const recommendations = await response.json();

            // Ignore responses from requests that have since been replaced
            if (currentRequest !== requestSequence) {
                return;
            }

            if (!response.ok) {
                throw new Error(
                    recommendations.error || "Recommendation request failed."
                );
            }

            if (loadingMessage.isConnected) {
                loadingMessage.remove();
            }

            if (recommendations.length === 0) {
                const message = document.createElement("p");
                message.textContent =
                    recommendedMovieIds.size > 0
                        ? "No more recommendations are available for these preferences."
                        : "No recommendations were found. Try rating different movies.";

                resultsContainer.appendChild(message);
                return;
            }

            if (!resultsContainer.querySelector("h3")) {
                const heading = document.createElement("h3");
                heading.textContent = "Your Recommendations";
                resultsContainer.appendChild(heading);
            }

            recommendations.forEach(movie => {
                recommendedMovieIds.add(String(movie.movieId));

                const card = document.createElement("div");
                card.className = "recommendation-card";

                // Movie poster
                const poster = document.createElement("div");
                poster.className = "recommendation-poster";

                if (movie.posterUrl) {
                    const image = document.createElement("img");
                    image.src = movie.posterUrl;
                    image.alt = `Poster for ${movie.title}`;

                    image.onerror = function () {
                        image.remove();
                        poster.classList.add("poster-placeholder");
                    };

                    poster.appendChild(image);
                } else {
                    poster.classList.add("poster-placeholder");
                }

                // Movie information
                const info = document.createElement("div");
                info.className = "recommendation-info";

                const title = document.createElement("h3");
                title.textContent = movie.title;

                const genres = document.createElement("p");
                genres.textContent = movie.genres || "Genre unavailable";

                info.appendChild(title);
                info.appendChild(genres);

                // Collection actions
                const actions = document.createElement("div");
                actions.className = "collection-actions";

                const categories = [
                    { key: "watchlist", label: "Watchlist" },
                    { key: "watched", label: "Watched" },
                    { key: "favorite", label: "Favorite" }
                ];

                categories.forEach(category => {
                    const button = document.createElement("button");
                    button.className = "collection-action";

                    function updateButton() {
                        const savedMovie = FilmFinderCollection.getMovie(movie.movieId);
                        const isActive = Boolean(savedMovie?.[category.key]);

                        button.textContent = isActive
                            ? `${category.label} ✓`
                            : `+ ${category.label}`;

                        button.classList.toggle("active", isActive);
                    }

                    updateButton();

                    button.addEventListener("click", function () {
                        const savedMovie = FilmFinderCollection.getMovie(movie.movieId);
                        const currentlyActive = Boolean(
                            savedMovie?.[category.key]
                        );

                        const success = FilmFinderCollection.addOrUpdate(movie, {
                            [category.key]: !currentlyActive
                        });

                        if (!success) {
                            alert("Unable to update your collection.");
                            return;
                        }

                        updateButton();
                    });

                    actions.appendChild(button);
                });

                info.appendChild(actions);
                card.appendChild(poster);
                card.appendChild(info);

                resultsContainer.appendChild(card);
            });

            resultsContainer.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        } catch (error) {
            if (currentRequest !== requestSequence) {
                return;
            }

            console.error("Collection recommendation error:", error);

            const errorMessage = document.createElement("p");
            errorMessage.textContent =
                error.message || "Unable to generate recommendations.";

            resultsContainer.appendChild(errorMessage);

        } finally {
            if (currentRequest === requestSequence) {
                recommendAllButton.disabled = false;
                updateSelectionStatus();
            }
        }
    }

    // ========================================
    // BUTTON EVENTS
    // ========================================

    recommendAllButton.addEventListener("click", function () {
        const movies = getRatedWatchedMovies();

        requestRecommendations(
            movies,
            "collection",
            activeRecommendationMode !== "collection"
        );
    });

    chooseMoviesButton.addEventListener("click", function () {
        setSelectionMode(!selectionMode);
    });

    watchedContainer.addEventListener("change", function (event) {
        if (!event.target.matches(".recommendation-movie-checkbox")) {
            return;
        }

        const movieId = String(event.target.dataset.movieId);

        // Save the previous selection for Undo
        saveSelectionHistory();

        if (event.target.checked) {
            selectedMovieIds.add(movieId);
        } else {
            selectedMovieIds.delete(movieId);
        }

        saveSelectedMovies();
        updateSelectionStatus();

        // Refresh recommendations if selected-movie mode is active
        if (activeRecommendationMode === "selected") {
            requestRecommendations(
                getSelectedRatedMovies(),
                "selected",
                true
            );
        }
    });

    const clearSelectedMoviesButton =
        document.getElementById("clear-selected-movies");

    const undoSelectionButton =
        document.getElementById("undo-selection");

    clearSelectedMoviesButton.addEventListener("click", function () {
        if (selectedMovieIds.size === 0) {
            return;
        }

        saveSelectionHistory();

        selectedMovieIds.clear();

        saveSelectedMovies();
        syncCheckboxes();

        if (activeRecommendationMode === "selected") {
            requestRecommendations([], "selected", true);
        }
    });

    undoSelectionButton.addEventListener("click", function () {
        undoSelectionChange();
    });

    recommendSelectedButton.addEventListener("click", function () {
        requestRecommendations(
            getSelectedRatedMovies(),
            "selected",
            activeRecommendationMode !== "selected"
        );
    });

    // ========================================
    // COLLECTION UPDATE EVENTS
    // ========================================

    window.addEventListener("filmFinderCollectionUpdated", function () {
        const validIds = new Set(
            getRatedWatchedMovies().map(movie => String(movie.movieId))
        );

        for (const movieId of selectedMovieIds) {
            if (!validIds.has(movieId)) {
                selectedMovieIds.delete(movieId);
            }
        }

        syncCheckboxes();

        // Recalculate only if the movies or ratings relevant to the
        // currently active recommendation mode have changed
        if (activeRecommendationMode) {
            const currentMovies = getMoviesForMode(activeRecommendationMode);
            const currentSignature = getPreferenceSignature(currentMovies);

            if (currentSignature !== lastPreferenceSignature) {
                requestRecommendations(
                    currentMovies,
                    activeRecommendationMode,
                    true
                );
            }
        }
    });

    window.addEventListener("filmFinderCollectionRendered", function () {
        syncCheckboxes();
    });

    // Remove saved selections that are no longer rated watched movies
    const validMovieIds = new Set(
        getRatedWatchedMovies().map(movie => String(movie.movieId))
    );

    for (const movieId of selectedMovieIds) {
        if (!validMovieIds.has(movieId)) {
            selectedMovieIds.delete(movieId);
        }
    }

    saveSelectedMovies();

    // Restore selection mode and checkbox states
    setSelectionMode(selectedMovieIds.size > 0);
});
