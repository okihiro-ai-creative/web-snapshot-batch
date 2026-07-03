"""
Web Snapshot Batch - Batch screenshot tool for multiple URLs
============================================================
Based on Web-Utility-Tool's main_p12_snapshot_webpage.py,
provides batch snapshot functionality for multiple URLs.

Usage:
  python batch_snapshot.py url1 url2 url3 ...
  python batch_snapshot.py --file urls.txt
  python batch_snapshot.py --file urls.txt --output "<output folder>"
  python batch_snapshot.py  (interactive mode)

Output:
  {OUTPUT_BASE_DIR}\{YYYYMMDD_HHMMSS}_batch\
    +-- _summary.txt          (batch execution summary)
    +-- 01_{domain}\
    |   +-- screenshot_pc.png
    |   +-- screenshot_mobile.png
    |   +-- source.html
    |   +-- source.txt
    |   +-- source.css
    +-- 02_{domain}\
    |   +-- ...
    +-- ...

NOTE: All print/argparse/summary text is in English to avoid
      UnicodeEncodeError on Windows (cp1252 encoding).

Created: 2026-05-13 / Generic distribution
"""

import sys
import os
import asyncio
import re
import argparse
import datetime
from urllib.parse import urlparse, urljoin

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


# --- Constants ---
OUTPUT_BASE_DIR = os.environ.get("WEB_SNAPSHOT_OUTPUT_DIR", os.path.join(os.getcwd(), "_Web_Snapshots"))
VIEWPORT_PC = {"width": 1280, "height": 800}
VIEWPORT_MOBILE = {"width": 375, "height": 812}
PAGE_TIMEOUT = 120000  # 120s
LOAD_WAIT = 3000       # Dynamic content load wait (ms)
SCROLL_WAIT = 2000     # Post-scroll wait (ms)


async def take_snapshot(page, url, output_dir, index, total):
    """Take a snapshot of a single URL"""
    prefix = f"[{index}/{total}]"
    try:
        print(f"\n{prefix} Accessing: {url}")
        await page.goto(url, wait_until="load", timeout=PAGE_TIMEOUT)

        print(f"{prefix} Loading dynamic content...")
        await page.evaluate("""() => {
            const images = document.querySelectorAll('img');
            images.forEach(img => {
                img.setAttribute('loading', 'eager');
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }
                if (img.dataset.srcset) {
                    img.srcset = img.dataset.srcset;
                }
            });
            window.scrollTo(0, document.body.scrollHeight);
        }""")
        await page.wait_for_timeout(LOAD_WAIT)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(SCROLL_WAIT)

        # PC screenshot
        print(f"{prefix} Taking PC screenshot...")
        await page.set_viewport_size(VIEWPORT_PC)
        await page.wait_for_timeout(1000)
        await page.screenshot(
            path=os.path.join(output_dir, "screenshot_pc.png"),
            full_page=True
        )

        # Mobile screenshot
        print(f"{prefix} Taking mobile screenshot...")
        await page.set_viewport_size(VIEWPORT_MOBILE)
        await page.wait_for_timeout(1000)
        await page.screenshot(
            path=os.path.join(output_dir, "screenshot_mobile.png"),
            full_page=True
        )

        # Extract HTML
        print(f"{prefix} Extracting HTML source...")
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'lxml')

        for attr in ['src', 'href']:
            for tag in soup.find_all(attrs={attr: True}):
                original_path = tag[attr]
                if isinstance(original_path, str) and not original_path.startswith(('http:', 'https:', 'data:', '#')):
                    absolute_path = urljoin(url, original_path)
                    tag[attr] = absolute_path

        final_html = str(soup)
        with open(os.path.join(output_dir, "source.html"), "w", encoding="utf-8") as f:
            f.write(final_html)

        # Extract Text
        print(f"{prefix} Extracting text content...")
        text_soup = BeautifulSoup(final_html, 'lxml')
        if text_soup.body:
            for tag in text_soup.body(['style', 'script']):
                tag.decompose()
            text_content = text_soup.body.get_text(separator='\n', strip=True)
            with open(os.path.join(output_dir, "source.txt"), "w", encoding="utf-8") as f:
                f.write(text_content)
        else:
            print(f"{prefix} [WARN] No <body> tag found. Skipping text extraction.")

        # Extract CSS
        print(f"{prefix} Extracting CSS source...")
        all_css = await page.evaluate('''() => {
            let css = '';
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules) {
                        css += rule.cssText + '\\n';
                    }
                } catch (e) {
                }
            }
            return css;
        }''')
        with open(os.path.join(output_dir, "source.css"), "w", encoding="utf-8") as f:
            f.write(all_css)

        print(f"{prefix} Done: {url}")
        return {"url": url, "status": "success", "output_dir": output_dir}

    except Exception as e:
        error_msg = str(e)
        print(f"{prefix} Error: {url} - {error_msg}")
        return {"url": url, "status": "error", "error": error_msg, "output_dir": output_dir}


async def run_batch(urls, custom_output_dir=None):
    """Run batch snapshots for multiple URLs"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    base_dir = custom_output_dir if custom_output_dir else OUTPUT_BASE_DIR
    batch_dir = os.path.join(base_dir, f"{timestamp}_batch")
    os.makedirs(batch_dir, exist_ok=True)

    total = len(urls)
    results = []

    print(f"\n{'='*60}")
    print(f" Web Snapshot Batch")
    print(f" Target URLs: {total}")
    print(f" Output Dir: {batch_dir}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        for i, url in enumerate(urls, 1):
            # Create per-URL subfolder
            domain = urlparse(url).netloc
            sanitized_domain = re.sub(r'[^a-zA-Z0-9.-]', '_', domain)
            # Include URL path for uniqueness
            path_part = urlparse(url).path.strip('/')
            sanitized_path = re.sub(r'[^a-zA-Z0-9_-]', '_', path_part)
            if sanitized_path:
                folder_name = f"{i:02d}_{sanitized_domain}_{sanitized_path[:50]}"
            else:
                folder_name = f"{i:02d}_{sanitized_domain}"

            output_dir = os.path.join(batch_dir, folder_name)
            os.makedirs(output_dir, exist_ok=True)

            # Save URL as metadata
            with open(os.path.join(output_dir, "_url.txt"), "w", encoding="utf-8") as f:
                f.write(url)

            page = await browser.new_page()
            result = await take_snapshot(page, url, output_dir, i, total)
            results.append(result)
            await page.close()

        await browser.close()

    # Generate summary file
    summary_path = os.path.join(batch_dir, "_summary.txt")
    success_count = sum(1 for r in results if r["status"] == "success")
    error_count = sum(1 for r in results if r["status"] == "error")

    summary_lines = [
        f"Web Snapshot Batch Summary",
        f"Timestamp: {timestamp}",
        f"Total: {total} / Success: {success_count} / Fail: {error_count}",
        f"Output Dir: {batch_dir}",
        "",
        "--- Details ---",
        "",
    ]
    for r in results:
        status_icon = "OK" if r["status"] == "success" else "NG"
        summary_lines.append(f"[{status_icon}] {r['url']}")
        summary_lines.append(f"   Folder: {os.path.basename(r['output_dir'])}")
        if r["status"] == "error":
            summary_lines.append(f"   Error: {r.get('error', 'unknown')}")
        summary_lines.append("")

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    # Final report
    print(f"\n{'='*60}")
    print(f" Batch Completed")
    print(f" Success: {success_count} / Fail: {error_count} / Total: {total}")
    print(f" Output Dir: {batch_dir}")
    print(f" Summary: {summary_path}")
    print(f"{'='*60}")

    return batch_dir, results


def parse_urls(args):
    """Get URL list from args or file"""
    urls = []

    if args.file:
        # Read URLs from file
        if not os.path.exists(args.file):
            print(f"[ERROR] File not found: {args.file}")
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.startswith(('http://', 'https://')):
                    urls.append(line)
        if not urls:
            print("[ERROR] No valid URLs found in file.")
            sys.exit(1)
    elif args.urls:
        urls = args.urls
    else:
        # Interactive mode
        print("Enter URLs to snapshot (empty line to finish):")
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                break
            if line.startswith(('http://', 'https://')):
                urls.append(line)
            else:
                print(f"  [SKIP] Invalid URL: {line}")
        if not urls:
            print("[ERROR] No valid URLs entered.")
            sys.exit(1)

    return urls


def main():
    parser = argparse.ArgumentParser(
        description="Batch snapshot tool for multiple URLs"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="URLs to snapshot (multiple allowed)"
    )
    parser.add_argument(
        "--file", "-f",
        help="Path to URL list file (one URL per line)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output base directory (default: 02_Workspace/_Web_Snapshots)"
    )

    args = parser.parse_args()
    urls = parse_urls(args)

    # Deduplicate URLs (preserve order)
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    if len(unique_urls) != len(urls):
        print(f"[INFO] Deduplicated: {len(urls)} -> {len(unique_urls)}")

    asyncio.run(run_batch(unique_urls, args.output))


if __name__ == "__main__":
    main()
