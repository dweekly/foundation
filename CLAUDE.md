# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the David & Rebecca Weekly Foundation website - a static HTML site showcasing structured philanthropy with a 1/3 local, 1/3 national, 1/3 international giving model. The site is built with vanilla HTML/CSS and uses Python scripts for generating dynamic content.

## Key Commands

### Build the website
```bash
python3 build.py              # Build the site
python3 build.py --clean      # Clean dist/ and rebuild
python3 build.py --refetch    # Force re-fetch all favicons
```

### Run local development server
```bash
cd dist && python3 -m http.server 8000
```
View the site at http://localhost:8000

## Directory Structure

```
/
├── src/                    # Source files
│   ├── index.html         # Main website template
│   └── styles.css         # Site styling
├── data/                  # Input data
│   ├── organizations.csv  # Organization data
│   └── README.md         # Instructions for adding orgs
├── dist/                  # Generated static site (deploy this)
│   ├── index.html
│   ├── styles.css
│   ├── portfolio_table.html
│   ├── favicon/          # Auto-fetched favicons
│   └── assets/           # Static assets
└── build.py              # Build script

```

## Architecture

### Data Flow
1. Organization data is maintained in `data/organizations.csv`
2. `build.py` processes the CSV and fetches favicons with multiple fallback strategies
3. Generated static site is output to `dist/` directory
4. Deploy the contents of `dist/` to hosting (e.g., Cloudflare Pages)

### Favicon Fetching Strategy
The build script tries multiple strategies to fetch favicons:
1. Common URL patterns (/favicon.ico, /apple-touch-icon.png, etc.)
2. Parse HTML for <link> tags with icon references
3. Google's favicon service as final fallback

### Content Structure
- Hero section with foundation mission
- Why Structured Giving philosophy section
- Impact Highlights featuring JAAGO Foundation school and Monje Lab sponsorship
- Portfolio Overview table grouped by Local/National/Global
- How We Give guide on donor advised funds
- FAQ section
- Contact information

## Deployment

To deploy to Cloudflare Pages or similar:
1. Run `python3 build.py --clean` to generate fresh build
2. Upload the contents of `dist/` directory
3. No server-side processing needed - it's all static files

## Development Notes

- The site uses semantic HTML with structured data (Schema.org)
- Organization classification: Local (Bay Area), National (US), Global (International)
- Reason categories map to emojis: education (🎓), environment (🌿), homeless (🏠), church (🙏), food (🍎), justice (⚖️), health (🩺)
- Edit organization data in `data/organizations.csv`, not the generated files