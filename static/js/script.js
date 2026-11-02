
const searchInput = document.getElementById("movie-search");
const searchResults = document.getElementById("search-results");
const selectedMoviesContainer = document.getElementById("selected-movies");
const selectionCount = document.getElementById("selection-count");
const generateButton = document.getElementById("generate-button");
const genrePreference = document.getElementById("genre-preference");

const recommendationGrid = document.getElementById("recommendation-grid");
const recommendationsSection = document.getElementById("recommendations");
const refreshButton = document.getElementById("refresh-recommendations");

const movieModal = document.getElementById("movie-modal");
const closeModalButton = document.getElementById("modal-close");
const findSimilarButton = document.getElementById("find-similar-button");

let selectedMovies = [];
let recommendedMovieIds = new Set();
let heroPosterInterval = null;


// ========================================
// MOVIE POSTER DISPLAY
// ========================================

function createPoster(movie, className = "movie-poster") {
    const container = document.createElement("div");
    container.className = `${className} poster-placeholder`;

    if (movie.posterUrl) {
        const image = document.createElement("img");
        image.src = movie.posterUrl;
        image.alt = `Poster for ${movie.title}`;
        image.className = className;

        image.onerror = function () {
            image.remove();
            container.classList.add("poster-placeholder");
        };

        container.classList.add("has-poster");
        container.appendChild(image);
    }

    return container;
}


// ========================================
// SHARED COLLECTION HELPERS
// ========================================

function getSavedMovie(movieId) {
    return window.FilmFinderCollection?.getMovie(movieId) || null;
}


function updateCollectionButton(button, category, movie) {
    const active = Boolean(movie?.[category.key]);

    button.textContent = active
        ? `✓ ${category.label}`
        : `+ ${category.label}`;

    button.classList.toggle("active", active);
}


function createCollectionActions(movie) {
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

        updateCollectionButton(
            button,
            category,
            getSavedMovie(movie.movieId)
        );

        button.addEventListener("click", function (event) {
            event.stopPropagation();

            const currentMovie = getSavedMovie(movie.movieId);
            const currentlyActive = Boolean(
                currentMovie?.[category.key]
            );

            const success = FilmFinderCollection.addOrUpdate(movie, {
                [category.key]: !currentlyActive
            });

            if (!success) {
                alert("Unable to update your collection.");
                return;
            }

            updateCollectionButton(
                button,
                category,
                getSavedMovie(movie.movieId)
            );
        });

        actions.appendChild(button);
    });

    return actions;
}


// ========================================
// MOVIE SEARCH
// ========================================

if (searchInput && searchResults) {
    searchInput.addEventListener("input", async function () {
        const query = searchInput.value.trim();

        if (query.length < 2) {
            searchResults.innerHTML = "";
            return;
        }

        try {
            const response = await fetch(
                `/api/search?q=${encodeURIComponent(query)}`
            );

            if (!response.ok) {
                throw new Error("Movie search failed.");
            }

            const movies = await response.json();

            searchResults.innerHTML = "";

            if (movies.length === 0) {
                searchResults.textContent = "No movies found.";
                return;
            }

            movies.forEach(movie => {
                const result = document.createElement("div");
                result.className = "search-result";

                const poster = createPoster(movie, "search-poster");

                const movieInfo = document.createElement("div");
                movieInfo.className = "search-result-info";

                const title = document.createElement("span");
                title.textContent = movie.title;

                movieInfo.appendChild(title);
                movieInfo.appendChild(createCollectionActions(movie));

                result.appendChild(poster);
                result.appendChild(movieInfo);

                result.addEventListener("click", function () {
                    addMovie(movie);
                });

                searchResults.appendChild(result);
            });

        } catch (error) {
            console.error("Movie search failed:", error);
            searchResults.textContent = "Unable to search movies.";
        }
    });
}


// ========================================
// ADD MOVIE TO DISCOVER SELECTIONS
// ========================================


function addMovie(movie) {
    if (!selectedMoviesContainer) {
        return;
    }

    const alreadySelected = selectedMovies.some(
        selected => selected.movieId === movie.movieId
    );

    if (alreadySelected) {
        return;
    }

    const success = FilmFinderCollection.addOrUpdate(movie, {
        selectedForRecommendations: true
    });

    if (!success) {
        alert("Unable to save movie selection.");
        return;
    }

    if (searchInput) {
        searchInput.value = "";
    }

    if (searchResults) {
        searchResults.innerHTML = "";
    }
}



// ========================================
// LOAD SAVED DISCOVER SELECTIONS
// ========================================

function loadSelectedMovies() {
    if (!selectedMoviesContainer) {
        return;
    }

    selectedMovies = FilmFinderCollection
        .getSelectedForRecommendations()
        .map(movie => ({
            ...movie,
            rating: Number(movie.rating) || 0
        }));

    renderSelectedMovies();
}


// ========================================
// DISPLAY SELECTED MOVIES
// ========================================

function renderSelectedMovies() {
    if (!selectedMoviesContainer) {
        return;
    }

    selectedMoviesContainer.innerHTML = "";

    selectedMovies.forEach(movie => {
        const movieElement = document.createElement("div");
        movieElement.className = "selected-movie";

        const movieInfo = document.createElement("div");

        const title = document.createElement("h4");
        title.textContent = movie.title;

        const genres = document.createElement("p");
        genres.textContent = movie.genres || "Genre unavailable";
        genres.className = "selected-genres";

        movieInfo.appendChild(title);
        movieInfo.appendChild(genres);

        // Rating dropdown
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
            const newRating = Number(ratingSelect.value);

            const success = FilmFinderCollection.update(movie.movieId, {
                rating: newRating
            });

            if (!success) {
                alert("Unable to save movie rating.");
                return;
            }

            movie.rating = newRating;
            updateSelectionStatus();
        });

        // Remove button
        const removeButton = document.createElement("button");
        removeButton.className = "remove-movie";
        removeButton.textContent = "×";
        removeButton.title = "Remove movie";

        removeButton.addEventListener("click", function () {
            const success =
                FilmFinderCollection.setSelectedForRecommendations(
                    movie.movieId,
                    false
                );

            if (!success) {
                alert("Unable to remove movie selection.");
                return;
            }

            selectedMovies = selectedMovies.filter(
                selected => selected.movieId !== movie.movieId
            );

            renderSelectedMovies();
        });

        const controls = document.createElement("div");
        controls.className = "selected-controls";

        controls.appendChild(ratingSelect);
        controls.appendChild(removeButton);

        const poster = createPoster(movie, "selected-poster");

        movieElement.appendChild(poster);
        movieElement.appendChild(movieInfo);
        movieElement.appendChild(controls);

        selectedMoviesContainer.appendChild(movieElement);
    });

    updateSelectionStatus();
}


// ========================================
// UPDATE SELECTION STATUS
// ========================================

function updateSelectionStatus() {
    if (!selectionCount || !generateButton) {
        return;
    }

    const ratedMovies = selectedMovies.filter(
        movie => Number(movie.rating) > 0
    );

    selectionCount.textContent =
        `${ratedMovies.length} of 5 required movies rated`;

    generateButton.disabled = ratedMovies.length < 5;
}


// ========================================
// SYNCHRONIZE COLLECTION CHANGES
// ========================================

window.addEventListener("filmFinderCollectionUpdated", function () {
    if (selectedMoviesContainer) {
        loadSelectedMovies();
    }
});


// ========================================
// GENERATE RECOMMENDATIONS
// ========================================

async function generateRecommendations(loadMore = false) {
    if (!generateButton || !recommendationGrid) {
        return;
    }

    const ratedMovies = selectedMovies.filter(
        movie => Number(movie.rating) > 0
    );

    if (ratedMovies.length < 5) {
        return;
    }

    const preferences = {};

    ratedMovies.forEach(movie => {
        preferences[movie.movieId] = Number(movie.rating);
    });

    // Reset tracking when starting a fresh recommendation search
    if (!loadMore) {
        recommendedMovieIds.clear();
    }

    generateButton.disabled = true;
    generateButton.textContent = "Finding your movies...";

    if (refreshButton) {
        refreshButton.disabled = true;
    }

    if (!loadMore) {
        recommendationGrid.innerHTML =
            "<p>Finding movies you'll love...</p>";
    }

    try {
        const response = await fetch("/api/recommend", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                preferences: preferences,
                genre: genrePreference?.value || "any",
                exclude_movie_ids: Array.from(recommendedMovieIds)
            })
        });

        const recommendations = await response.json();

        if (!response.ok) {
            throw new Error(
                recommendations.error ||
                "Recommendation request failed."
            );
        }

        displayRecommendations(recommendations, loadMore);

        if (recommendations.length === 0 && loadMore) {
            const message = document.createElement("p");
            message.textContent =
                "You've seen all the recommendations available for these preferences.";
            recommendationGrid.appendChild(message);
        }

        if (recommendationsSection) {
            recommendationsSection.scrollIntoView({
                behavior: "smooth"
            });
        }

    } catch (error) {
        console.error("Recommendation error:", error);

        if (!loadMore) {
            recommendationGrid.textContent =
                error.message || "Something went wrong.";
        } else {
            console.error("Unable to load more recommendations.");
        }

    } finally {
        generateButton.textContent =
            "Generate Recommendations →";

        generateButton.disabled = false;

        updateSelectionStatus();

        if (refreshButton) {
            refreshButton.disabled = false;
        }
    }
}



// ========================================
// DISPLAY RECOMMENDED MOVIES
// ========================================

function displayRecommendations(recommendations, append = false) {
    if (!recommendationGrid) {
        return;
    }

    // Clear existing cards only for a fresh recommendation search
    if (!append) {
        recommendationGrid.innerHTML = "";
    }

    recommendations.forEach(movie => {
        // Prevent duplicate recommendations
        if (recommendedMovieIds.has(movie.movieId)) {
            return;
        }

        recommendedMovieIds.add(movie.movieId);

        const card = document.createElement("div");
        card.className = "recommendation-card";

        const info = document.createElement("div");
        info.className = "recommendation-info";

        const title = document.createElement("h3");
        title.textContent = movie.title;

        const genres = document.createElement("p");
        genres.textContent = movie.genres || "Genre unavailable";

        info.appendChild(title);
        info.appendChild(genres);
        info.appendChild(createCollectionActions(movie));

        const poster = createPoster(
            movie,
            "recommendation-poster"
        );

        card.appendChild(poster);
        card.appendChild(info);

        recommendationGrid.appendChild(card);
    });
}



// ========================================
// LOAD POPULAR MOVIES
// ========================================

async function loadPopularMovies() {
    const homeContainer =
        document.getElementById("home-popular-grid");

    const discoverContainer =
        document.getElementById("popular-movies");

    const container = homeContainer || discoverContainer;

    if (!container) {
        return;
    }

    try {
        const response = await fetch("/api/popular");

        if (!response.ok) {
            throw new Error("Could not load popular movies.");
        }

        const popularMovies = await response.json();

        // Load posters into the Home hero carousel
        const heroCarousel = document.getElementById(
            "hero-poster-carousel"
        );

        if (heroCarousel) {
            const heroMovies = popularMovies
                .filter(movie => movie.posterUrl)
                .slice(0, 12);

            heroCarousel.innerHTML = "";

            const posters = [];

            for (let i = 0; i < 3; i++) {
                const image = document.createElement("img");
                image.className = "hero-poster";
                image.alt = "Movie poster";

                heroCarousel.appendChild(image);
                posters.push(image);
            }

            if (heroMovies.length > 0) {
                let activeIndex = 0;

                function updateHeroPosters() {
                    const positions = [
                        { offset: 0, className: "is-active" },
                        { offset: 1, className: "is-next" },
                        { offset: -1, className: "is-previous" }
                    ];

                    posters.forEach((poster, index) => {
                        const movieIndex =
                            (activeIndex + positions[index].offset +
                            heroMovies.length) % heroMovies.length;

                        const movie = heroMovies[movieIndex];

                        poster.src = movie.posterUrl;
                        poster.alt = `Poster for ${movie.title}`;

                        poster.className =
                            `hero-poster ${positions[index].className}`;
                    });

                    activeIndex = (activeIndex + 1) % heroMovies.length;
                }

                updateHeroPosters();

                clearInterval(heroPosterInterval);

                if (heroMovies.length > 1) {
                    heroPosterInterval = setInterval(
                        updateHeroPosters,
                        3500
                    );
                }
            }
        }

        container.innerHTML = "";

        popularMovies.forEach(movie => {
            const card = document.createElement("div");
            card.className = "movie-card";

            const poster = createPoster(movie);

            const title = document.createElement("h4");
            title.textContent = movie.title;

            card.appendChild(poster);
            card.appendChild(title);

            card.addEventListener("click", () => {
                if (homeContainer) {
                    const modal =
                        document.getElementById("movie-modal");

                    const modalTitle =
                        document.getElementById("modal-movie-title");

                    const modalGenres =
                        document.getElementById("modal-movie-genres");

                    const modalYear =
                        document.getElementById("modal-movie-year");

                    const modalOverview =
                        document.getElementById("modal-movie-overview");

                    if (!modal) {
                        return;
                    }

                    modalTitle.textContent = movie.title;

                    modalYear.textContent = movie.release_year
                        ? movie.release_year
                        : "Release year unavailable";

                    modalGenres.textContent = movie.genres
                        .split(" ")
                        .join(", ");

                    modalOverview.textContent = movie.overview
                        ? movie.overview
                        : "No plot summary is available for this movie.";

                    modal.classList.add("active");
                    modal.setAttribute("aria-hidden", "false");

                } else {
                    addMovie(movie);
                }
            });

            container.appendChild(card);
        });

    } catch (error) {
        console.error("Error loading popular movies:", error);
        container.textContent = "Unable to load popular movies.";
    }
}


// ========================================
// HOME MOVIE DETAILS MODAL
// ========================================

if (movieModal) {
    if (closeModalButton) {
        closeModalButton.addEventListener("click", () => {
            movieModal.classList.remove("active");
            movieModal.setAttribute("aria-hidden", "true");
        });
    }

    movieModal.addEventListener("click", event => {
        if (event.target === movieModal) {
            movieModal.classList.remove("active");
            movieModal.setAttribute("aria-hidden", "true");
        }
    });

    if (findSimilarButton) {
        findSimilarButton.addEventListener("click", () => {
            window.location.href = "/discover";
        });
    }
}


// ========================================
// INITIALIZATION
// ========================================

loadPopularMovies();

if (generateButton) {
    generateButton.addEventListener(
        "click",
        generateRecommendations
    );
}

if (refreshButton) {
    refreshButton.addEventListener(
        "click",
        () => generateRecommendations(true)
    );
}

if (selectedMoviesContainer) {
    loadSelectedMovies();
}
