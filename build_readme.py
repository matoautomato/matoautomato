import re
from datetime import datetime
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup

FEED_URL = "https://terminalvelocity.blog/index.xml"
GITHUB_USER = "matoautomato"
README = Path(__file__).parent / "README.md"


def replace_section(content, section, new_text):
    pattern = re.compile(
        rf"(<!-- {section} starts -->).*?(<!-- {section} ends -->)",
        re.DOTALL,
    )
    return pattern.sub(rf"\1\n{new_text}\n\2", content)


def fetch_posts(feed_url, count=4):
    feed = feedparser.parse(feed_url)
    posts = [e for e in feed.entries if "/posts/" in e.link][:count]
    lines = []
    for post in posts:
        date = datetime(*post.published_parsed[:3]).strftime("%Y-%m-%d")
        lines.append(f"- [{post.title}]({post.link}) – {date}")
    return "\n".join(lines)


def fetch_latest_note(feed_url):
    feed = feedparser.parse(feed_url)
    notes = [e for e in feed.entries if "/notes/" in e.link]
    if not notes:
        return "*No notes yet.*"

    note = notes[0]
    title = note.title
    url = note.link
    date = datetime(*note.published_parsed[:3]).strftime("%Y-%m-%d")

    # Get text content from the feed
    text = ""
    if hasattr(note, "content"):
        text = note.content[0].value
    elif hasattr(note, "summary"):
        text = note.summary

    # Scrape the rendered page for images the theme injects from the page bundle
    images = []
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        article = soup.find("article") or soup.find("main") or soup
        for img in article.find_all("img"):
            src = img.get("src", "")
            if src and "/images/mato_color" not in src:
                if not src.startswith("http"):
                    src = f"https://terminalvelocity.blog{src}"
                images.append(src)
    except requests.RequestException:
        pass

    # Build the note markdown
    parts = [f"**[{title}]({url})** – {date}", ""]

    # Strip HTML tags from text content for clean markdown
    if text:
        text_clean = BeautifulSoup(text, "html.parser").get_text().strip()
        if text_clean:
            parts.append(text_clean)
            parts.append("")

    for img_url in images:
        parts.append(f"[![{title}]({img_url})]({url})")
        parts.append("")

    return "\n".join(parts).rstrip()


def fetch_projects(username, count=6):
    resp = requests.get(
        f"https://api.github.com/users/{username}/repos",
        params={"sort": "pushed", "per_page": count},
        timeout=10,
    )
    resp.raise_for_status()
    repos = resp.json()

    lines = []
    for repo in repos:
        if repo["fork"] or repo["name"] == username:
            continue
        name = repo["name"]
        url = repo["html_url"]
        desc = repo.get("description") or ""
        pushed = repo["pushed_at"][:10]
        line = f"- [{name}]({url})"
        if desc:
            line += f" – {desc}"
        line += f" (updated {pushed})"
        lines.append(line)
    return "\n".join(lines)


def main():
    content = README.read_text()
    content = replace_section(content, "posts", fetch_posts(FEED_URL))
    content = replace_section(content, "note", fetch_latest_note(FEED_URL))
    content = replace_section(content, "projects", fetch_projects(GITHUB_USER))
    README.write_text(content)
    print("README updated.")


if __name__ == "__main__":
    main()
