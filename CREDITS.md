# FilmFinder — Credits & Third-Party Usage Register

**Project:** FilmFinder  
**Purpose:** Non-commercial movie discovery and recommendation application  
**Created:** October 31, 2026

This document tracks third-party resources used by FilmFinder, including datasets, APIs, images, software libraries, machine-learning models, fonts, icons, and externally sourced code.

FilmFinder aims to respect copyright, licensing requirements, attribution rules, and provider terms.

**Important:** Public accessibility does not automatically mean public domain or unrestricted reuse. Any resource marked "Pending verification" must be reviewed before public release.

---

## 1. Third-Party Resource Register

| Resource | Purpose | Source | License / Usage Status |
|---|---|---|---|
| MovieLens `ml-latest-small` | Movie information, ratings, tags, and identifiers | https://grouplens.org/datasets/movielens/ | Usage conditions documented in the included dataset README |
| The Movies Dataset | Additional movie metadata and plot information | https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset | Kaggle lists CC0; underlying data provenance and provider terms must also be considered |
| TMDB | Planned movie information and poster artwork API integration | https://developer.themoviedb.org/docs | Non-commercial API use requires attribution and compliance with TMDB terms |
| Sentence Transformers | Text embedding generation | https://www.sbert.net/ | Verify package license and version |
| `all-MiniLM-L6-v2` | Generates plot embeddings used by the hybrid recommendation system | https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 | Verify model license and attribution requirements |
| Flask | Python web application framework | https://flask.palletsprojects.com/ | BSD-3-Clause |
| Python packages | Data processing and recommendation functionality | See `requirements.txt` | Review individual package licenses |
| Fonts and icons | Interface typography and visual elements | Record individual sources when added | Verify before use |
| External code | Any copied or adapted code | Record original source | Verify source license before integration |

---

## 2. MovieLens Dataset Attribution

FilmFinder uses the **MovieLens ml-latest-small dataset**, generated September 26, 2018.

Dataset source:  
https://grouplens.org/datasets/movielens/

The dataset contains:
- 9,742 movies
- 100,836 ratings
- 3,683 tag applications
- 610 anonymized users

The original dataset README permits redistribution subject to its usage conditions.

Important conditions include:

- Do not state or imply endorsement by the University of Minnesota or GroupLens Research Group.
- Acknowledge the dataset in resulting publications.
- Redistribute the dataset only under the same usage conditions.
- Do not use the dataset for commercial or revenue-bearing purposes without prior permission from GroupLens.

**Required academic citation:**

F. Maxwell Harper and Joseph A. Konstan. 2015. The MovieLens Datasets: History and Context. ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4: 19:1–19:19.

https://doi.org/10.1145/2827872

The exact dataset README should accompany any permitted redistribution.

---

## 3. The Movies Dataset Attribution

FilmFinder uses `movies_metadata.csv` from **The Movies Dataset**, created by Rounak Banik.

Source:  
https://www.kaggle.com/datasets/rounakbanik/the-movies-dataset

Kaggle lists this dataset under the **CC0: Public Domain** license.

The dataset contains metadata for approximately 45,000 movies, including information such as:
- Movie titles
- Plot descriptions
- Release dates
- Genres
- Budgets and revenue
- Languages
- Production information
- TMDB identifiers and related metadata

### Original data sources

The dataset description identifies TMDB and GroupLens as underlying sources:

- Movie details, credits, and keywords were collected from the TMDB Open API.
- Movie links and ratings were obtained from GroupLens.

The dataset description includes the following acknowledgment:

"This product uses the TMDB API but is not endorsed or certified by TMDB."

CC0 status applies to the Kaggle dataset as listed; it should not be treated as automatically resolving every underlying provider's terms.

---

## 4. TMDB API Attribution

TMDB is a planned provider for movie information and poster images.

Official documentation:
- https://developer.themoviedb.org/docs
- https://developer.themoviedb.org/docs/image-basics
- https://developer.themoviedb.org/docs/faq

TMDB currently permits free API use for non-commercial purposes subject to its attribution requirements.

Required notice:

"This product uses the TMDB API but is not endorsed or certified by TMDB."

Before public release:

- Confirm the project's eligibility for developer API usage.
- Review the current API terms.
- Use an approved TMDB logo.
- Display required attribution prominently.
- Include attribution in the application's About or Credits section.
- Keep API credentials out of frontend JavaScript and public source control.
- Follow API rate limits and usage restrictions.

TMDB logo and attribution requirements:  
https://developer.themoviedb.org/docs/faq

---

## 5. Machine Learning and Embeddings

FilmFinder uses the Sentence Transformers model:

`sentence-transformers/all-MiniLM-L6-v2`

Model source:  
https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

The model is used to generate numerical representations of movie plot descriptions for content-based recommendations.

The resulting embeddings are stored locally in:

`data/plot_embeddings.npy`

The embedding file is generated from movie metadata rather than downloaded as an original dataset.

The model's license and applicable attribution requirements should be confirmed before distribution.

---

## 6. Software and Dependencies

FilmFinder uses Python and Flask, alongside additional packages for data processing and recommendation functionality.

For each dependency, record:

- Package name
- Installed version
- Official source
- License
- Required copyright notices
- Redistribution requirements

The complete dependency list should be maintained in `requirements.txt`.

Required license notices must be preserved when distributing the application.

---

## 7. Images, Fonts, Icons, and Other Media

Before adding external visual assets:

- Identify the original creator or provider.
- Verify the applicable license.
- Confirm permission for website display and redistribution.
- Check whether attribution is required.
- Record the exact attribution wording.
- Document where the credit appears.

Do not assume that images found through search engines are free to use.

---

## 8. External Code and Templates

For code copied or adapted from external sources:

- Record the original source URL.
- Identify the applicable license.
- Follow attribution and redistribution requirements.
- Preserve required copyright notices.
- Avoid incorporating code with unclear permissions.

---

## 9. API Security

- Keep API credentials out of frontend JavaScript.
- Store secrets in environment variables.
- Never commit API keys or tokens to public repositories.
- Use `.env` files for local development where appropriate.
- Provide an `.env.example` containing placeholder values only.
- Follow provider rate limits and usage restrictions.
- Review provider terms whenever APIs are updated.

---

## 10. Public Release Checklist

- [ ] Confirm MovieLens redistribution conditions.
- [ ] Include the MovieLens README when redistributing its data.
- [ ] Verify The Movies Dataset's source and usage requirements.
- [ ] Verify TMDB API and image usage terms.
- [ ] Add required TMDB branding and attribution.
- [ ] Review Sentence Transformers and model licensing.
- [ ] Review Python dependency licenses.
- [ ] Review fonts, icons, and other visual assets.
- [ ] Review externally sourced code.
- [ ] Include required license and copyright notices.
- [ ] Verify API credentials are secure.
- [ ] Confirm data files can be obtained by users cloning the repository.
- [ ] Recheck provider requirements before deployment.

---

## 11. Review History

| Date | Activity | Result |
|---|---|---|
| October 31, 2026 | Initial credits register created | Verification pending |
| November 1, 2026 | Identified MovieLens ml-latest-small | Original usage README reviewed |
| November 1, 2026 | Identified The Movies Dataset | Kaggle source and CC0 listing identified |
| November 1, 2026 | Documented Sentence Transformers model | License verification pending |
| November 1, 2026 | Reviewed TMDB attribution requirements | Requirements documented; integration planned |

---

**FilmFinder Commitment**

FilmFinder aims to use third-party resources responsibly, respect intellectual property, follow applicable licensing requirements, and provide appropriate attribution to creators and providers.