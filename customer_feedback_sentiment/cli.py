"""Command-line interface for sentiment tagging."""

from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import build_summary, read_and_classify, render_report, save_tagged


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Tag English feedback sentiment and summarize themes.")
    result.add_argument("input", type=Path)
    result.add_argument("--text-column", default="feedback")
    result.add_argument("--output", type=Path, help="Tagged CSV output path")
    result.add_argument("--report", type=Path, help="Markdown summary output path")
    return result


def main() -> int:
    args = parser().parse_args()
    source = args.input.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".csv":
        raise SystemExit("Input must be an existing CSV file.")
    output = args.output.expanduser().resolve() if args.output else source.with_name(
        f"{source.stem}.tagged.csv"
    )
    report = args.report.expanduser().resolve() if args.report else source.with_name(
        f"{source.stem}.sentiment.md"
    )
    if output == source:
        raise SystemExit("Output cannot overwrite the input CSV.")
    try:
        rows, source_fields = read_and_classify(source, args.text_column)
        summary = build_summary(rows, args.text_column)
        save_tagged(rows, source_fields, output)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(render_report(summary, args.text_column), encoding="utf-8")
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"Tagged {summary['total']} row(s): {summary['positive']} positive, "
        f"{summary['neutral']} neutral, {summary['negative']} negative."
    )
    print(f"Tagged CSV: {output}")
    print(f"Summary: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
