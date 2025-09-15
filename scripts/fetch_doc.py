#!/usr/bin/env -S uv run --script

# /// script
# dependencies = [
#   "requests",
#   "pyyaml",
#   "pytz",
#   "beautifulsoup4",
# ]
# ///

import sys
import requests
import yaml
from datetime import datetime
import pytz
import argparse
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup


parser = argparse.ArgumentParser(
    description="Fetch and convert web content to markdown"
)
parser.add_argument("url", help="URL to fetch")
parser.add_argument(
    "--debug", action="store_true", help="Enable debug mode to show response headers"
)

args = parser.parse_args()
url = args.url


def dprint(msg: str):
    if args.debug:
        print(msg, file=sys.stderr)


# タイトルを元のHTMLページから取得
def fetch_html_title(original_url: str, debug: bool = False):
    try:
        if debug:
            dprint(f"=== Fetching HTML title from {original_url} ===")

        html_response = requests.get(
            original_url,
            timeout=20,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/117.0.0.0 Safari/537.36"
                )
            },
        )
        html_response.raise_for_status()
        html_response.encoding = html_response.apparent_encoding

        soup = BeautifulSoup(html_response.text, "html.parser")
        title_tag = soup.find("title")

        if title_tag and title_tag.string:
            title = title_tag.string.strip()
            if debug:
                dprint(f"Found HTML title: {title}")
            return title

    except Exception as e:
        if debug:
            dprint(f"Failed to fetch HTML title: {e}")

    return None


# Markdownからのフォールバック手法
def extract_title_from_markdown(content: str, original_url: str) -> str:
    lines = content.splitlines()

    # URLの拡張子をチェック
    is_markdown_like = any(
        original_url.lower().endswith(ext)
        for ext in [".md", ".markdown", ".txt", ".rst"]
    )

    # HTML以外のファイル（.mdなど）の場合は優先的にURLパスからタイトル生成
    if is_markdown_like:
        try:
            parsed = urlparse(original_url)

            if parsed.path and parsed.path != "/":
                path_parts = [p for p in parsed.path.split("/") if p]
                if path_parts:
                    # 最後の部分（ファイル名）を使用
                    filename = unquote(path_parts[-1])
                    title = filename.split(".")[0]  # 拡張子を除去
                    # ハイフンやアンダースコアをスペースに変換して読みやすく
                    title = title.replace("-", " ").replace("_", " ")
                    if title:
                        return title.title()

        except Exception:
            pass

    # 手法1: 任意レベルの見出しから抽出（#, ##, ###など）
    for line in lines[:10]:
        line_stripped = line.strip()
        if line_stripped.startswith("#"):
            title = line_stripped.lstrip("# ").strip()
            if title:
                return title

    # 手法2: URLからタイトルを生成（フォールバック）
    try:
        parsed = urlparse(original_url)

        if parsed.path and parsed.path != "/":
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                title = unquote(path_parts[-1])
                title = title.split(".")[0]
                title = title.replace("-", " ").replace("_", " ")
                if title:
                    return title.title()

        domain = parsed.netloc.replace("www.", "")
        if domain:
            return domain.capitalize()

    except Exception:
        pass

    return "No Title"


def is_probably_text_url(u: str) -> bool:
    """拡張子ベースでテキストと推定。ただし docs.anthropic.com は常にHTML扱い。"""
    parsed = urlparse(u)
    if parsed.netloc.endswith("docs.anthropic.com"):
        return False
    return any(
        u.lower().endswith(ext)
        for ext in [
            ".md",
            ".markdown",
            ".txt",
            ".rst",
            ".json",
            ".yaml",
            ".yml",
            ".csv",
        ]
    )


def fetch_direct(u: str):
    resp = requests.get(
        u,
        timeout=30,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/117.0.0.0 Safari/537.36"
            )
        },
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text, resp.headers.get("Content-Type", "")


def fetch_via_jina(u: str) -> str:
    jina_url = f"https://r.jina.ai/{u}"
    dprint(f"=== Using Jina Reader AI for {jina_url} ===")
    headers = {
        "X-Engine": "browser",
        "X-Retain-Images": "none",
        "X-Return-Format": "markdown",
    }
    r = requests.get(jina_url, headers=headers, timeout=60)
    r.raise_for_status()
    if args.debug:
        dprint(f"=== Response Headers for {jina_url} ===")
        for key, value in r.headers.items():
            dprint(f"{key}: {value}")
        dprint("=" * 50)
    return r.text.strip()


# 1) コンテンツ取得（テキスト直取得 or Jina）
markdown = None
fetched_as_text = False
try:
    if is_probably_text_url(url):
        dprint(f"=== Directly fetching text-like URL: {url} ===")
        body, content_type = fetch_direct(url)
        ct = content_type.lower()
        # HTMLが返ってきたらJinaにフォールバック
        if "text/html" in ct or "html;" in ct:
            dprint("Content-Type indicates HTML; falling back to Jina")
            markdown = fetch_via_jina(url)
        else:
            markdown = body.strip()
            fetched_as_text = True
            if args.debug:
                dprint(f"Content length: {len(markdown)}")
    else:
        markdown = fetch_via_jina(url)
except requests.RequestException as e:
    # 直取得が失敗した場合はJinaへフォールバック
    dprint(f"Direct fetch failed: {e}; trying Jina")
    markdown = fetch_via_jina(url)


# 2) タイトル取得
if args.debug:
    dprint("=== Extracting title ===")

try:
    if fetched_as_text:
        # テキストファイルの場合はMarkdownから、またはURLパスから
        title = extract_title_from_markdown(markdown, url)
    else:
        # HTMLページの場合はまずHTMLから、失敗したらMarkdownから
        title = fetch_html_title(url, args.debug) or extract_title_from_markdown(
            markdown, url
        )
    if args.debug:
        dprint(f"=== Extracted title: {title} ===")
except Exception as e:
    if args.debug:
        dprint(f"=== Error extracting title: {e} ===")
    title = "Error extracting title"


# 3) Frontmatter を付与して出力
jst = pytz.timezone("Asia/Tokyo")
updated_at = datetime.now(jst).isoformat()

frontmatter_data = {
    "title": title,
    "url": url,
    "updated_at": updated_at,
}
frontmatter = yaml.dump(
    frontmatter_data, default_flow_style=False, allow_unicode=True
).strip()

output = f"---\n{frontmatter}\n---\n\n{markdown}"
if args.debug:
    dprint(f"Final output length: {len(output)}")
    dprint(f"Title: {title}")
print(output)
sys.stdout.flush()
