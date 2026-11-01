
# FilmFinder — Credits & Third-Party Usage Register

**Project:** FilmFinder  
**Purpose:** Non-commercial movie discovery and recommendation application  
**Created:** October 31, 2026

This document tracks third-party resources used in FilmFinder, including datasets, APIs, images, software libraries, fonts, icons, and externally sourced code.

Our goal is to respect copyright, licensing requirements, attribution rules, and provider terms.

**Important:** Publicly accessible does not automatically mean public domain or free to reuse. Resources marked "Pending verification" must be reviewed before public release.

---

## 1. Third-Party Resource Register

| Resource | Purpose | Source | License / Usage Status | Attribution Status |
|---|---|---|---|---|
| MovieLens | Movie metadata, ratings, tags, and recommendation data | https://grouplens.org/datasets/movielens/ | Pending verification of exact dataset terms | Pending verification |
| TMDB | Movie information and poster artwork | https://developer.themoviedb.org/docs | Planned; verify current non-commercial API and image usage terms before integration | Required credits to be confirmed |
| Flask | Python web application framework | https://flask.palletsprojects.com/ | Verify installed version's license | Review before release |
| Python packages | Data processing and recommendation functionality | See requirements.txt | Individual package licenses must be reviewed | Review before release |
| Fonts and icons | Interface typography and visual elements | Record individual sources when added | Verify before use | As required by provider |
| External code | Any copied or adapted code | Record original source | Verify source license before integration | As required by license |

---

## 2. TMDB Attribution

TMDB is a planned provider for movie information and poster images.

Before integrating it:

- Review the current TMDB API terms.
- Confirm that FilmFinder qualifies for non-commercial API usage.
- Review image-specific usage requirements.
- Follow TMDB's required logo and attribution placement.
- Include the required disclaimer in the application.

Proposed disclaimer, subject to checking current official requirements:

"This product uses the TMDB API but is not endorsed or certified by TMDB."

Official documentation:
https://developer.themoviedb.org/docs

https://developer.themoviedb.org/docs/image-basics

---

## 3. MovieLens Attribution

FilmFinder uses MovieLens data for its recommendation system.

Before release:

- Confirm the exact dataset version.
- Review the dataset's README and usage terms.
- Record the required citation and acknowledgment.
- Confirm whether any restrictions apply to redistribution.

Source:
https://grouplens.org/datasets/movielens/

---

## 4. Software and Dependencies

All software packages used by FilmFinder must be reviewed.

For each dependency, record:

- Package name
- Installed version
- Official source
- License
- Required copyright notices
- Redistribution requirements

Include required license notices when distributing the application.

---

## 5. Images, Fonts, Icons, and Other Media

Before adding external visual assets:

- Identify the original creator or provider.
- Verify the license.
- Confirm permission for website display and redistribution.
- Check whether attribution is required.
- Record the exact attribution wording.
- Document where the credit appears.

Do not assume that images found through search engines are free to use.

---

## 6. External Code and Templates

For code copied or adapted from external sources:

- Record the original source URL.
- Identify the applicable license.
- Follow its attribution and redistribution requirements.
- Preserve required copyright notices.
- Avoid incorporating code with unclear permissions.

---

## 7. API Security

- Keep API credentials out of frontend JavaScript.
- Store secrets in environment variables.
- Never commit API keys to public repositories.
- Follow provider rate limits and usage restrictions.
- Review terms whenever an API provider updates its policies.

---

## 8. Public Release Checklist

Before publishing FilmFinder:

- [ ] Verify MovieLens dataset terms.
- [ ] Verify TMDB API and image usage terms.
- [ ] Add required TMDB branding and attribution.
- [ ] Add MovieLens acknowledgment where required.
- [ ] Review Python dependency licenses.
- [ ] Review fonts, icons, and other visual assets.
- [ ] Review externally sourced code.
- [ ] Include required license and copyright notices.
- [ ] Verify API credentials are secure.
- [ ] Recheck all provider requirements before release.

---

## 9. Review History

| Date | Activity | Result |
|---|---|---|
| October 31, 2026 | Initial credits register created | Verification still required for MovieLens, TMDB, and dependencies |

---

**FilmFinder Commitment**

FilmFinder aims to use third-party resources responsibly, respect intellectual property, follow applicable licensing requirements, and provide appropriate attribution to creators and providers.
