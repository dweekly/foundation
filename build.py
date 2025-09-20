#!/usr/bin/env python3
"""
Build script for David & Rebecca Weekly Foundation website.

This script:
1. Reads organization data from data/organizations.csv
2. Fetches favicons for each organization (with multiple fallback strategies)
3. Optimizes and copies images to dist/
4. Generates the portfolio HTML table
5. Combines everything into the final static site in dist/

Usage:
    python build.py              # Build the site
    python build.py --clean       # Clean dist/ and rebuild
    python build.py --refetch     # Force re-fetch all favicons
"""

import argparse
import csv
import html
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List, Optional

# Directory structure
ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
DATA_DIR = ROOT / "data"
DIST_DIR = ROOT / "dist"
SRC_IMAGES_DIR = SRC_DIR / "images"
DIST_IMAGES_DIR = DIST_DIR / "images"
FAVICON_DIR = DIST_DIR / "favicon"
CSV_PATH = DATA_DIR / "organizations.csv"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DIST_DIR.mkdir(exist_ok=True)
DIST_IMAGES_DIR.mkdir(exist_ok=True)
FAVICON_DIR.mkdir(exist_ok=True)

# User agent for better success with favicon fetching
USER_AGENT = "Mozilla/5.0 (compatible; FaviconFetcher/1.0; +https://foundation.weekly.org)"


def slugify(value: str) -> str:
    """Convert organization name to filename-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def create_request(url: str) -> urllib.request.Request:
    """Create a request with proper headers."""
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "image/*,text/html,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Cache-Control": "no-cache",
            "DNT": "1",
        },
    )


def download_favicon(url: str, dest: Path, timeout: int = 10) -> bool:
    """Download a favicon from URL to destination path."""
    try:
        req = create_request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if not data or len(data) < 100:  # Skip tiny/empty files
                return False

            # Determine file extension from content type or URL
            content_type = resp.headers.get("Content-Type", "").lower()
            suffix = ".ico"

            if "png" in content_type:
                suffix = ".png"
            elif "jpeg" in content_type or "jpg" in content_type:
                suffix = ".jpg"
            elif "svg" in content_type:
                suffix = ".svg"
            elif "webp" in content_type:
                suffix = ".webp"
            elif "gif" in content_type:
                suffix = ".gif"
            elif "x-icon" in content_type or "vnd.microsoft.icon" in content_type:
                suffix = ".ico"
            else:
                # Try to get from URL
                url_path = urllib.parse.urlparse(url).path.lower()
                for ext in [".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".ico"]:
                    if url_path.endswith(ext):
                        suffix = ext
                        break

            dest_path = dest.with_suffix(suffix)
            dest_path.write_bytes(data)
            print(f"  ✓ Saved {dest_path.name}")
            return True

    except Exception as e:
        print(f"  ✗ Failed to download {url}: {str(e)[:60]}")
        return False


def parse_html_for_icons(html_content: str, base_url: str) -> List[str]:
    """Parse HTML content to find favicon URLs using BeautifulSoup if available, else regex."""
    icon_urls = []

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # Find all link tags with rel containing 'icon'
        for link in soup.find_all(
            "link",
            rel=lambda x: (
                x and "icon" in x.lower()
                if isinstance(x, str)
                else any("icon" in r.lower() for r in x)
            ),
        ):
            href = link.get("href")
            if href:
                # Convert relative URLs to absolute
                absolute_url = urllib.parse.urljoin(base_url, href)
                icon_urls.append(absolute_url)

        # Also look for apple-touch-icon
        for link in soup.find_all(
            "link",
            rel=lambda x: (
                x and "apple-touch-icon" in x.lower()
                if isinstance(x, str)
                else any("apple-touch-icon" in r.lower() for r in x)
            ),
        ):
            href = link.get("href")
            if href:
                absolute_url = urllib.parse.urljoin(base_url, href)
                if absolute_url not in icon_urls:
                    icon_urls.append(absolute_url)

    except ImportError:
        # Fallback to regex if BeautifulSoup not available
        print("  Note: BeautifulSoup not found, using regex parsing")
        # Find link tags with rel="icon" or rel="shortcut icon"
        pattern = r'<link[^>]*rel=["\']([^"\']*icon[^"\']*)["\'"][^>]*href=["\']([^"\']+)["\']'
        for match in re.finditer(pattern, html_content, re.IGNORECASE):
            href = match.group(2)
            absolute_url = urllib.parse.urljoin(base_url, href)
            icon_urls.append(absolute_url)

        # Also try href first pattern
        pattern2 = r'<link[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']([^"\']*icon[^"\']*)["\'"]'
        for match in re.finditer(pattern2, html_content, re.IGNORECASE):
            href = match.group(1)
            absolute_url = urllib.parse.urljoin(base_url, href)
            if absolute_url not in icon_urls:
                icon_urls.append(absolute_url)

    return icon_urls


def try_common_favicon_patterns(domain: str, slug: str) -> Optional[str]:
    """Try common favicon URL patterns."""
    base_url = f"https://{domain}"
    target = FAVICON_DIR / slug

    # Common favicon locations in order of preference
    patterns = [
        "/favicon.ico",
        "/favicon.png",
        "/apple-touch-icon.png",
        "/apple-touch-icon-precomposed.png",
        "/favicon-32x32.png",
        "/favicon-16x16.png",
        "/icon.png",
        "/logo.png",
        "/images/favicon.ico",
        "/images/favicon.png",
        "/img/favicon.ico",
        "/img/favicon.png",
        "/assets/favicon.ico",
        "/assets/favicon.png",
        "/static/favicon.ico",
        "/static/favicon.png",
        "/public/favicon.ico",
        "/public/favicon.png",
    ]

    for pattern in patterns:
        url = base_url + pattern
        print(f"  Trying {pattern}...")
        if download_favicon(url, target):
            for ext in [".png", ".jpg", ".ico", ".svg", ".webp", ".gif"]:
                path = target.with_suffix(ext)
                if path.exists():
                    return path.name
        time.sleep(0.1)  # Be polite

    return None


def fetch_favicon_from_html(base_url: str, slug: str) -> Optional[str]:
    """Fetch and parse HTML to find favicon links."""
    target = FAVICON_DIR / slug

    try:
        print(f"  Fetching HTML from {base_url}...")
        req = create_request(base_url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            # Read up to 200KB of HTML
            html_content = resp.read(204800).decode("utf-8", errors="ignore")

    except Exception as e:
        print(f"  ✗ Could not fetch HTML: {str(e)[:60]}")
        return None

    # Parse HTML for icon links
    icon_urls = parse_html_for_icons(html_content, base_url)

    # Try each found icon URL
    for url in icon_urls[:10]:  # Try up to 10 icons
        print(f"  Trying icon from HTML: {url}")
        if download_favicon(url, target):
            for ext in [".png", ".jpg", ".ico", ".svg", ".webp", ".gif"]:
                path = target.with_suffix(ext)
                if path.exists():
                    return path.name
        time.sleep(0.1)  # Be polite

    return None


def fetch_favicon_google_fallback(domain: str, slug: str) -> Optional[str]:
    """Use Google's favicon service as a fallback."""
    target = FAVICON_DIR / slug
    google_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=64"

    print("  Trying Google favicon service...")
    if download_favicon(google_url, target):
        for ext in [".png", ".jpg", ".ico"]:
            path = target.with_suffix(ext)
            if path.exists():
                return path.name
    return None


def fetch_favicon(website: str, org_name: str, force_refetch: bool = False) -> Optional[str]:
    """
    Fetch favicon for an organization with multiple fallback strategies.

    Strategy:
    1. Check if we already have a cached favicon (unless force_refetch)
    2. Try to fetch and parse HTML for icon links (most accurate)
    3. Try common favicon URL patterns
    4. Use Google's favicon service as last resort
    """
    if not website:
        return None

    # Clean up website URL
    website = website.strip()
    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    parsed = urllib.parse.urlparse(website)
    domain = parsed.netloc
    if not domain:
        return None

    slug = slugify(org_name)
    target = FAVICON_DIR / slug

    # Check for existing favicon (unless force refetch)
    if not force_refetch:
        for ext in [".png", ".jpg", ".jpeg", ".ico", ".svg", ".webp", ".gif"]:
            path = target.with_suffix(ext)
            if path.exists():
                print(f"✓ Using cached favicon for {org_name}: {path.name}")
                return path.name

    print(f"\nFetching favicon for {org_name} ({domain})...")

    # Strategy 1: Parse HTML for icon links (most reliable)
    result = fetch_favicon_from_html(website, slug)
    if result:
        return result

    # Strategy 2: Try common patterns
    result = try_common_favicon_patterns(domain, slug)
    if result:
        return result

    # Strategy 3: Google favicon service
    result = fetch_favicon_google_fallback(domain, slug)
    if result:
        return result

    print(f"  ✗ Could not fetch favicon for {org_name}")
    return None


def optimize_image(src_path: Path, dest_path: Path, max_width: int = None):
    """Optimize and resize an image for web display."""
    # For now, just copy the image
    # In production, you'd use PIL/Pillow to resize and optimize
    shutil.copy2(src_path, dest_path)

    # Try to use ImageMagick if available for basic optimization
    if max_width and shutil.which("convert"):
        try:
            subprocess.run(
                [
                    "convert",
                    str(dest_path),
                    "-resize",
                    f"{max_width}x{max_width}>",
                    "-quality",
                    "85",
                    "-strip",
                    str(dest_path),
                ],
                capture_output=True,
                timeout=5,
            )
            print(f"  ✓ Optimized {dest_path.name}")
        except Exception:
            pass  # If optimization fails, we still have the copied image


def copy_and_optimize_images():
    """Copy and optimize images from src to dist."""
    if not SRC_IMAGES_DIR.exists():
        return

    print("\n📸 Processing images...")

    # Image optimization settings
    image_sizes = {
        "favicon512.png": None,  # Don't resize favicon
        "d-and-b.jpg": 1200,  # Hero image
        "monje1.jpg": 800,
        "monje2.jpg": 800,
        "IMG_0705.jpeg": 800,  # JAAGO images
        "IMG_0706.jpeg": 800,
        "IMG_0707.jpeg": 800,
    }

    for img_file in SRC_IMAGES_DIR.iterdir():
        if img_file.is_file() and img_file.suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
        ]:
            dest_path = DIST_IMAGES_DIR / img_file.name
            max_width = image_sizes.get(img_file.name)
            optimize_image(img_file, dest_path, max_width)
            print(f"  ✓ Copied {img_file.name}")


def generate_portfolio_html(rows: List[dict], force_refetch: bool = False) -> str:
    """Generate the portfolio table HTML from organization data."""
    table_rows = []

    for row in rows:
        org = row["Org"]
        website = (row.get("Website") or "").strip()

        # Fetch favicon
        icon_filename = fetch_favicon(website, org, force_refetch)
        if icon_filename:
            icon_html = f'<img class="favicon" src="favicon/{icon_filename}" alt="" aria-hidden="true" loading="lazy">'
        else:
            icon_html = '<span class="favicon-fallback" aria-hidden="true">🌐</span>'

        # Build organization name with link
        name = html.escape(org)
        if website:
            href = website if website.startswith(("http://", "https://")) else "https://" + website
            name_html = f'<a class="org-name" href="{html.escape(href)}" target="_blank" rel="noreferrer">{name}</a>'
        else:
            name_html = f'<span class="org-name">{name}</span>'

        # Get organization details
        summary = (row.get("Summary") or "Details coming soon.").strip() or "Details coming soon."
        reason_key = (row.get("Reason") or "").strip().lower()
        scope = (row.get("Class") or "").strip()
        why = (
            row.get("Why") or ""
        ).strip() or "Personal note coming soon while we document this grant."
        cn = (row.get("CharityNavigator") or "").strip()
        gs = (row.get("GuideStar") or "").strip()

        # Map scope to emoji
        scope_emoji, scope_label = {
            "Local": ("🏘️", "Local Giving"),
            "National": ("🇺🇸", "National Giving"),
            "Global": ("🌍", "Global Giving"),
        }.get(scope, ("❓", "Undesignated"))

        # Map category to emoji
        cat_emoji, cat_label = {
            "education": ("🎓", "Education"),
            "environment": ("🌿", "Environment"),
            "homeless": ("🏠", "Housing & Stability"),
            "church": ("🙏", "Faith & Community"),
            "food": ("🍎", "Food Security"),
            "justice": ("⚖️", "Justice"),
            "health": ("🩺", "Health"),
        }.get(reason_key, ("❓", row.get("Reason") or "Focus pending"))

        # Build badges HTML
        cn_html = (
            f'<a class="badge-link" href="{html.escape(cn)}" target="_blank" rel="noreferrer">'
            f'<img class="badge-image" src="images/cn.png" alt="Charity Navigator logo" loading="lazy"></a>'
            if cn
            else '<span class="badge-empty" aria-hidden="true"></span>'
        )
        gs_html = (
            f'<a class="badge-link" href="{html.escape(gs)}" target="_blank" rel="noreferrer">'
            f'<img class="badge-image" src="images/gs.jpeg" alt="GuideStar logo" loading="lazy"></a>'
            if gs
            else '<span class="badge-empty" aria-hidden="true"></span>'
        )

        # Build card content
        card_content = (
            f'<div class="org-card">{icon_html}<div class="org-card-content">'
            f'<div>{name_html}</div><span class="summary">{html.escape(summary)}</span>'
            f"</div></div>"
        )

        # Add table row
        table_rows.append(
            "    <tr>\n"
            f'      <td class="org">{card_content}</td>\n'
            f'      <td class="scope"><span class="emoji" title="{html.escape(scope_label)}">{scope_emoji}</span></td>\n'
            f'      <td class="category"><span class="emoji" title="{html.escape(cat_label)}">{cat_emoji}</span></td>\n'
            f'      <td class="ratings">{cn_html}{gs_html}</td>\n'
            f'      <td class="notes"><span class="why">{html.escape(why)}</span></td>\n'
            "    </tr>"
        )

    return "\n".join(table_rows) + "\n"


def build_site(args):
    """Main build function."""
    print("🔨 Building David & Rebecca Weekly Foundation website...\n")

    # Clean if requested
    if args.clean:
        print("🧹 Cleaning dist directory...")
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
        DIST_DIR.mkdir(exist_ok=True)
        FAVICON_DIR.mkdir(exist_ok=True)
        DIST_IMAGES_DIR.mkdir(exist_ok=True)

    # Check for CSV file
    if not CSV_PATH.exists():
        print(f"❌ Error: CSV file not found at {CSV_PATH}")
        print(f"\nPlease create {CSV_PATH} with organization data.")
        print(
            "Required columns: Org, Amount, Reason, Class, Why, EIN, Website, CharityNavigator, GuideStar, Summary"
        )
        sys.exit(1)

    # Read and process CSV
    print(f"📊 Reading organization data from {CSV_PATH}...")
    lines = [line for line in CSV_PATH.read_text().splitlines() if line.strip()]
    rows = [r for r in csv.DictReader(lines) if r.get("Org")]

    # Sort rows by class and preserve original order within class
    order_map = {"Local": 0, "National": 1, "Global": 2}
    rows = [
        r
        for idx, r in sorted(
            enumerate(rows), key=lambda item: (order_map.get(item[1]["Class"], 99), item[0])
        )
    ]

    print(f"✓ Found {len(rows)} organizations")

    # Copy and optimize images
    copy_and_optimize_images()

    # Check for BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        _ = BeautifulSoup  # Reference to avoid unused import warning
        print("\n✓ BeautifulSoup found - using enhanced favicon parsing")
    except ImportError:
        print("\n💡 Tip: Install BeautifulSoup for better favicon detection:")
        print("  pip install beautifulsoup4")

    # Generate portfolio HTML
    print("\n🎨 Generating portfolio table and fetching favicons...")
    portfolio_html = generate_portfolio_html(rows, args.refetch)

    # Save portfolio table fragment
    portfolio_path = DIST_DIR / "portfolio_table.html"
    portfolio_path.write_text(portfolio_html)
    print(f"\n✓ Generated portfolio table with {len(rows)} organizations")

    # Read source HTML and CSS
    if not (SRC_DIR / "index.html").exists():
        print(f"❌ Error: Source HTML not found at {SRC_DIR / 'index.html'}")
        sys.exit(1)

    print("\n📦 Assembling final site...")

    # Read source HTML
    source_html = (SRC_DIR / "index.html").read_text()

    # Find where to insert the portfolio table
    # Look for the tbody tag inside the portfolio table
    tbody_start = source_html.find("<tbody>", source_html.find('class="portfolio-table"'))
    tbody_end = source_html.find("</tbody>", tbody_start)

    if tbody_start != -1 and tbody_end != -1:
        # Replace the tbody content with our generated rows
        tbody_start += len("<tbody>")
        final_html = (
            source_html[:tbody_start]
            + "\n"
            + portfolio_html.rstrip()
            + "\n"
            + "                "  # Proper indentation
            + source_html[tbody_end:]
        )
    else:
        # Fallback: just copy the original HTML
        print("⚠️  Warning: Could not find portfolio table tbody in source HTML")
        final_html = source_html

    # Write the final HTML
    (DIST_DIR / "index.html").write_text(final_html)

    # Copy CSS to dist
    shutil.copy2(SRC_DIR / "styles.css", DIST_DIR / "styles.css")

    print("✓ Assembled final HTML with portfolio table")
    print("✓ Copied CSS")

    # Count successful favicon fetches
    if FAVICON_DIR.exists():
        favicon_count = len(list(FAVICON_DIR.iterdir()))
        print(f"✓ Fetched {favicon_count} favicons")

    print(f"\n✅ Build complete! Static site generated in {DIST_DIR}/")
    print(f"\n📝 To test locally: cd {DIST_DIR} && python3 -m http.server 8000")
    print(
        f"☁️  To deploy: Upload contents of {DIST_DIR}/ to your hosting provider (e.g., Cloudflare Pages)"
    )


def main():
    parser = argparse.ArgumentParser(description="Build the foundation website")
    parser.add_argument(
        "--clean", action="store_true", help="Clean dist/ directory before building"
    )
    parser.add_argument("--refetch", action="store_true", help="Force re-fetch all favicons")
    args = parser.parse_args()

    try:
        build_site(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
