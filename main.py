"""CLI entry point."""
import argparse
import json
from src.screener import screen_directory

def main():
    parser = argparse.ArgumentParser(description="Screen and rank resumes for Python + AI engineering roles.")
    parser.add_argument("--input", required=True, help="Directory containing PDF/DOCX/TXT resumes")
    parser.add_argument("--output", default="output/results.json", help="Path to JSON output")
    args = parser.parse_args()
    result = screen_directory(args.input, args.output)
    print(json.dumps(result["batch_summary"], indent=2))
    print(f"Results written to: {args.output}")

if __name__ == "__main__":
    main()
