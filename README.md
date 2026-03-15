# Open Hukamnama

<p align="center">
  <img src="assets/logo.png" alt="Open Hukamnama logo" width="220" />
</p>

## Overview

Open Hukamnama is a lightweight, self-hostable tool for selecting and publishing the daily Hukamnama from the Guru Granth Sahib.

This project began in 2006 at Gursikh Sabha Canada in Toronto, Ontario, Canada. Its original purpose was to give the granthi a straightforward interface for selecting the daily morning prayer: the Hukamnama, traditionally taken as the first stanza on a randomly opened page from the Guru Granth Sahib.

In its earliest form, the workflow was manual. A phone call would be made, and a technician would update flat files to publish the selection. Over time, that evolved into a more standalone, lightweight, mobile-friendly system that can be self-hosted and operated with much less technical involvement.

The project is now being open sourced and made freely available for anyone who would like to use, adapt, or host it for their own community.

## What This Repo Contains

- A FastAPI backend that serves scripture data and stores the current Hukamnama selection
- A static selector frontend for choosing the shabad range
- A SQLite source database containing Guru Granth Sahib content
- A small flat-file state layer used by the current selection workflow
- Docker and Docker Compose configuration for local or self-hosted deployment

## Project Layout

```text
.
├── api.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── data
│   ├── source
│   │   └── GGS.sqlite
│   └── variables
│       ├── shabadsSTART.txt
│       ├── shabadsEND.txt
│       └── shabadsUPDATED.txt
└── select
    ├── index.html
    ├── manifest.json
    ├── sw.js
    └── static assets
```

## How It Works

### Selector Flow

1. A user opens the selector UI in the browser.
2. The user logs in through the backend authentication endpoint using the configured selector credentials.
3. The frontend requests shabads for a given ang/page using `GET /getShabads/{myPage}`.
4. The user selects the desired row range.
5. The frontend submits the selected start and end IDs to `POST /submit/`.
6. The backend writes the active selection into flat files under `data/variables/`.
7. Other consumers can read the current Hukamnama using `GET /hukamnama`.

### Current Storage Model

Source data:
- `data/source/GGS.sqlite`

Generated state:
- `data/variables/shabadsSTART.txt`
- `data/variables/shabadsEND.txt`
- `data/variables/shabadsUPDATED.txt`

## Getting Started

### Requirements

- Docker
- Docker Compose

### Run With Docker

Start the application with the default selector credentials:

```bash
docker compose up --build
```

Start the application with custom selector credentials:

```bash
SELECT_USERNAME=myuser SELECT_PASSWORD=mypass SESSION_SECRET=replace-this docker compose up --build
```

Once the container is running, open:

- [http://localhost/](http://localhost/)

### Stop The Application

```bash
docker compose down
```

## Configuration

### Docker Environment Variables

The selector UI login is configured through Docker environment variables:

- `SELECT_USERNAME`
- `SELECT_PASSWORD`
- `SESSION_SECRET`

If these are not provided, the app defaults to:

```text
SELECT_USERNAME=sevadar
SELECT_PASSWORD=gursikh905
SESSION_SECRET=change-me-in-production
```

### Important Note About Authentication

The selector now uses backend login with a signed session cookie. `SESSION_SECRET` should be changed in any non-trivial deployment.

## Data Attribution

Portions of the data in this repository were collected from SikhiToTheMax, a project developed by Khalis Foundation.

SikhiToTheMax is described by Khalis Foundation as being powered by BaniDB.

Sources:

- [SikhiToTheMax](https://www.sikhitothemax.org/)
- [Khalis Foundation](https://khalisfoundation.org/portfolio/sikhitothemax/)
- [BaniDB partner reference](https://www.banidb.com/partners/sikhitothemax/)

This repository is an independent, derived project and is not affiliated with or endorsed by Khalis Foundation or SikhiToTheMax.

Please refer to the original sources for authoritative and most up-to-date content.

## API Reference

Base URL in Docker:

```text
http://localhost/
```

### `GET /`

Redirects the browser to the selector frontend.

Behavior:
- Returns an HTTP redirect to `/select/`

Typical use:
- Browser entrypoint for the app

### `GET /select/`

Serves the static selector frontend from the `select/` directory.

Behavior:
- Returns the HTML and related static assets for the selector UI

Typical use:
- Manual shabad selection workflow in the browser

### `POST /login`

Validates selector credentials and creates a signed session cookie.

Request body:

```json
{
  "username": "sevadar",
  "password": "gursikh905"
}
```

Example response:

```json
{
  "authenticated": true
}
```

Notes:
- Credentials are validated against `SELECT_USERNAME` and `SELECT_PASSWORD`
- On success, the backend sets an HTTP-only session cookie

### `POST /logout`

Clears the current session cookie.

Example response:

```json
{
  "authenticated": false
}
```

### `GET /session`

Returns whether the current request has a valid authenticated session.

Example response:

```json
{
  "authenticated": true
}
```

### `GET /getShabads/{myPage}`

Fetches shabad rows for the requested page and the next page from the SQLite source database.

Path parameter:
- `myPage`: integer starting ang/page number

Behavior:
- Queries the `shabads` table where `pageNum >= myPage` and `pageNum <= myPage + 1`
- Returns only `id`, `pageNum`, and `shabadP`
- Replaces `&lt;&gt;` with `<>` in returned string values

Example request:

```text
GET /getShabads/702
```

Example response:

```json
[
  {
    "id": 2719,
    "pageNum": 702,
    "shabadP": "..."
  },
  {
    "id": 2720,
    "pageNum": 702,
    "shabadP": "..."
  }
]
```

Used by:
- The selector frontend to populate the DataTable

Authentication:
- Requires a valid session cookie

### `GET /updatedHukamnama`

Returns the last update string stored in the generated state files.

Behavior:
- Reads `data/variables/shabadsUPDATED.txt`
- Returns the first line as the `updated` field

Example response:

```json
{
  "updated": "Last Updated - 2025-03-15 14:21:04"
}
```

### `GET /hukamnama`

Builds the current Hukamnama payload using the selected start and end shabad IDs stored in flat files.

Behavior:
- Reads `data/variables/shabadsSTART.txt`
- Reads `data/variables/shabadsEND.txt`
- Queries the `shabads` table for rows where `id >= start` and `id <= end`
- Concatenates matching `shabadE` values into `shabadEnglish`
- Concatenates matching `shabadP` values into `shabadPunjabi`
- Truncates English text to 1100 characters plus `...`
- Truncates Punjabi text to 700 characters plus `...`
- Returns the `page` from the first matched row
- Replaces `&lt;&gt;` with `<>` in the Punjabi output

Example response:

```json
{
  "page": "702",
  "shabadEnglish": "One Universal Creator God ...",
  "shabadPunjabi": "..."
}
```

Notes:
- This endpoint depends on valid values already being present in the selector state files
- If the chosen range is empty or invalid, the endpoint may fail because it expects at least one matching row

### `POST /submit/`

Stores the shabad range selected in the frontend and updates the last-updated timestamp.

Request body:

```json
{
  "firstShabad": "2719",
  "lastShabad": "2725"
}
```

Behavior:
- Writes `firstShabad` to `data/variables/shabadsSTART.txt`
- Writes `lastShabad` to `data/variables/shabadsEND.txt`
- Writes a US/Eastern timestamp to `data/variables/shabadsUPDATED.txt`

Example response:

```json
{
  "firstShabad": "2719",
  "lastShabad": "2725"
}
```

Used by:
- The selector frontend after the user selects rows and submits them

Authentication:
- Requires a valid session cookie

## Notes

- The current architecture still uses flat files for the active selection state.
- That state model is simple and portable, but it is likely to be refactored in the future.
- The frontend is currently a static HTML app served by FastAPI.
