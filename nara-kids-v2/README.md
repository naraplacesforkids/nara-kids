# Nara Kids v2

A six-language mobile web app using the original WordPress export as its 2023 attractions archive. **All original article text is in English**: the six-language selector translates app navigation, controls, notices, and event interface, not full old articles or automatically imported event descriptions/titles. Automatic machine translation can be added later using a translation API and human review.

## Contents
- `activities.json`: the original 10 archived articles, preserved.
- `events.json`: upcoming date-specific events, empty until a real source is configured.
- `sources.json`: list of authorized public iCalendar (`.ics`) feeds.
- `scripts/update_events.py`: daily import, date filtering, deduplication, source attribution and error logging.
- `.github/workflows/update-events.yml`: GitHub Actions schedule at **05:15 JST daily** (scheduled runs are not guaranteed at the exact minute).

## Preview now
Upload the **contents** of this folder to Netlify Drop, or deploy the directory through Netlify. Open the site in Safari and Add to Home Screen. Places, six-language menus, saved places, and source-directory links work immediately. Events will honestly show an empty-state until connected to compatible feeds.

## Enable genuine automatic updates
1. Locate public `.ics` calendar feed(s) from event organizers in Nara. The regular public calendar web page is **not** automatically an `.ics` feed. Request consent/appropriate reuse where required. Check feed accuracy, date coverage, and licensing.
2. Edit `sources.json`, e.g.:
```
{"ical_feeds":[{"name":"Organizer name","url":"https://organizer.example/events.ics","official_url":"https://organizer.example/calendar","city":"Kashihara","all_free":false}]}
```
Only set `all_free:true` if **all** source events are definitely free. `official_url` is a backup event link, not a substitute for event details.
3. Create a GitHub repository, commit the app files including `.github/workflows`, and connect that repo to Netlify using **Add new project → Import an existing project**; set publish directory to the repository root. A manual ZIP upload to Netlify Drop **does not** activate GitHub Actions or recurring updates.
4. In GitHub, open **Actions → Update Nara Kids events → Run workflow** to test; look at logs. For ongoing scheduled updates GitHub Actions must be enabled and the workflow exist on the default branch.
5. When importer commits `events.json`, Netlify's Git integration redeploys the site. App fetches `events.json` with network-first fetching, so new items appear after redeploy.

**This build does not magically scan all Japanese municipal websites:** most publish HTML pages, not documented ICS feeds. Add a site-specific importer only after checking its format, permission, and date accuracy. The three official calendars remain linked as real-time fallbacks. Automatic feed imports are not human verification: check cancellations, pricing, eligibility and reservations from source links. Any imported titles/descriptions stay in their source language; translating those reliably requires an additional service.

## Source and privacy
The original WordPress site is untouched and can remain private. The old post contents within this downloadable app are included in its `activities.json` and become **public** when you deploy this app. Review the articles for personal information, children's photos and content rights before publishing. Original media images are not copied into this bundle.


## v2.1 municipal calendar discovery

`sources.json` now includes Kashihara, Tenri, and Sakurai City public event calendars.
`python scripts/update_events.py` checks these calendars once per run, extracts date-linked
family-friendly titles **only when the calendar clearly includes a year/month and day**,
and stores the official page URL. Listings are marked `reviewStatus: unverified`.
Cost, age restrictions, availability and booking cannot be safely inferred: verify at source.
Other calendar types (including Nara City and Nara Prefecture) are linked in the UI,
but not yet parsed. This is deliberately conservative.

The scheduled GitHub Actions workflow runs daily at ~05:15 JST **after** you upload
this folder to a GitHub repository, enable Actions and connect the repository to
Netlify continuous deployment. GitHub Actions schedule times may occasionally be delayed.
Static upload via Netlify Drop does NOT run scheduled updates. Municipal HTML layouts
can change at any time, in which case the scraper may miss events or fail.

To test: `pip install -r requirements.txt && python scripts/update_events.py`.
Check `events.json` (including `errors`, `sources`, and `updatedAt`) before relying
on the feed. If all sources fail, the task exits without overwriting the old feed.
Do not describe discovered listings as confirmed events; the event details
should always be checked at their official link.


## Version 2.2: language coverage
The 10 attraction cards now contain manually drafted short guides in Japanese, Haitian Creole, French, Nepali and Hindi; English remains the original source. The full original 2023 articles remain in English in the detail drawer, explicitly labeled as such. This is NOT a complete translation of those articles. Attraction names retain recognizable venue names. Events support optional `translations: {language: {title, description}}` fields, but the current scraper does not generate them; new events fall back to the original language. Translation should be reviewed by native speakers before public release.

Deploy: Replace the `nara-kids-v2/activities.json`, `nara-kids-v2/app.js` and `nara-kids-v2/README.md` files in your repository with the same files in this archive, then commit and push. Keep Netlify publish directory set to `nara-kids-v2`.
