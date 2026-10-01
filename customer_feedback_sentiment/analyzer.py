"""CSV ingestion, polarity labeling, keyword ranking, and reporting."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from textblob import TextBlob

STOP_WORDS = {
    "about", "after", "again", "also", "and", "are", "because", "been", "before",
    "but", "can", "could", "did", "does", "every", "for", "from", "had", "has",
    "have", "here", "how", "into", "its", "just", "like", "more", "most", "much",
    "not", "our", "out", "over", "really", "same", "some", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "those", "too",
    "very", "was", "were", "what", "when", "which", "while", "with", "would",
    "you", "your",
}


def classify(text: str) -> tuple[str, float]:
    polarity = float(TextBlob(text).sentiment.polarity) if text.strip() else 0.0
    if polarity > 0.1:
        label = "positive"
    elif polarity < -0.1:
        label = "negative"
    else:
        label = "neutral"
    return label, polarity


def read_and_classify(source: Path, text_column: str) -> tuple[list[dict[str, str]], list[str]]:
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("Input CSV must include a header row.")
        if text_column not in reader.fieldnames:
            raise ValueError(
                f"Column {text_column!r} was not found. Available columns: {', '.join(reader.fieldnames)}"
            )
        source_fields = list(reader.fieldnames)
        rows = []
        for row in reader:
            label, polarity = classify(row.get(text_column, "") or "")
            row["sentiment"] = label
            row["polarity"] = f"{polarity:.3f}"
            rows.append(row)
    return rows, source_fields


def negative_keywords(rows: list[dict[str, str]], limit: int = 10) -> list[tuple[str, int]]:
    words: Counter[str] = Counter()
    for row in rows:
        if row["sentiment"] != "negative":
            continue
        tokens = re.findall(r"[a-zA-Z]{3,}", row.get("feedback", "").lower())
        words.update(token for token in tokens if token not in STOP_WORDS)
    return words.most_common(limit)


def build_summary(rows: list[dict[str, str]], text_column: str) -> dict[str, Any]:
    counts = Counter(row["sentiment"] for row in rows)
    polarities = [float(row["polarity"]) for row in rows]
    negative_rows = [
        {**row, "feedback": row.get(text_column, "")}
        for row in rows
        if row["sentiment"] == "negative"
    ]
    return {
        "total": len(rows),
        "positive": counts["positive"],
        "neutral": counts["neutral"],
        "negative": counts["negative"],
        "average_polarity": mean(polarities) if polarities else 0.0,
        "negative_keywords": negative_keywords(negative_rows),
    }


def save_tagged(rows: list[dict[str, str]], source_fields: list[str], output: Path) -> None:
    fields = source_fields + ["sentiment", "polarity"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def render_report(summary: dict[str, Any], text_column: str) -> str:
    total = summary["total"] or 1
    lines = [
        "# Customer Feedback Sentiment Report",
        "",
        f"- **Feedback rows:** {summary['total']}",
        f"- **Text column:** {text_column}",
        f"- **Average polarity:** {summary['average_polarity']:.3f}",
        "",
        "| Label | Count | Share |",
        "| --- | ---: | ---: |",
    ]
    for label in ("positive", "neutral", "negative"):
        count = summary[label]
        lines.append(f"| {label.title()} | {count} | {count / total * 100:.1f}% |")
    lines.extend(["", "## Frequent terms in negative feedback", ""])
    if summary["negative_keywords"]:
        lines.extend(f"- {word}: {count}" for word, count in summary["negative_keywords"])
    else:
        lines.append("No negative feedback terms found.")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Polarity is a lightweight English-language heuristic. Review examples and the source text before using this summary to make customer or product decisions.",
            "",
        ]
    )
    return "\n".join(lines)
