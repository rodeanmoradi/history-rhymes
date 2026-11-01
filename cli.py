"""Terminal version of the site: pick one of today's headlines (or pass your own) and print the lesson as JSON."""
import json
import sys

from app.news import top_headlines
from app.pipeline import run


def main():
    if len(sys.argv) > 1:
        headline = " ".join(sys.argv[1:])
    else:
        headlines = top_headlines()
        for i, h in enumerate(headlines):
            print(f"{i:>2}. {h['title']} ({h['source']})")
        headline = headlines[int(input("Select index: "))]["title"]

    result = run(headline, on_step=lambda message: print(f"  … {message}", file=sys.stderr))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
