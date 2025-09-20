# David & Rebecca Weekly Foundation Website

Static website for the David & Rebecca Weekly Foundation, showcasing our structured approach to philanthropy with a 1/3 local, 1/3 national, 1/3 international giving model.

## Quick Start

```bash
# Set up Python environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Build the website
python3 build.py

# Test locally
cd dist && python3 -m http.server 8000
# Visit http://localhost:8000
```

## Project Structure

- `src/` - Source HTML and CSS files
- `data/` - Organization data in CSV format
- `dist/` - Generated static website (deploy this directory)
- `build.py` - Build script that generates the site

## Adding Organizations

1. Edit `data/organizations.csv` with organization details
2. Run `python3 build.py` to rebuild the site
3. The build script will automatically fetch favicons

See `data/README.md` for detailed instructions on the CSV format.

## Deployment

The `dist/` directory contains a complete static website ready for deployment to:
- Cloudflare Pages
- GitHub Pages
- Netlify
- Any static hosting service

Simply upload the contents of `dist/` to your hosting provider.

## Features

- **Automatic Favicon Fetching**: The build script intelligently fetches organization favicons with multiple fallback strategies
- **Structured Data**: Includes Schema.org markup for better SEO
- **Responsive Design**: Mobile-friendly layout
- **Clean URLs**: Static site requires no server-side processing

## Development

```bash
# Clean rebuild (removes dist/ and refetches everything)
python3 build.py --clean

# Force refetch all favicons (useful if logos have changed)
python3 build.py --refetch
```

## License

Copyright © David & Rebecca Weekly. All rights reserved.