"""
main.py
-------
CLI entry point for the Website Lead Generation AI.
(For the web UI version, run app.py instead.)

Pipeline:
  1. DISCOVER  -> pull businesses per (city, category) from
                  OpenStreetMap (free, no billing) + Justdial
  2. FILTER    -> split into "no website" vs "has website"
  3. ANALYZE   -> for businesses WITH a website, check reachability +
                  PageSpeed performance
  4. SCORE     -> classify each business as NO_WEBSITE / POOR_WEBSITE /
                  HEALTHY, with a 0-100 priority score
  5. EXPORT    -> write qualified leads (NO_WEBSITE + POOR_WEBSITE) to
                  a color-coded Excel file

Run:
    python main.py                     # full run across all configured cities/categories
    python main.py --city Jaipur       # limit to one city
    python main.py --category "gym"    # limit to one category
    python main.py --limit 5           # cap results per (city, category) — good for testing
"""

import argparse

import config
from src.pipeline import run_full_pipeline
from src.output import export


def parse_args():
    parser = argparse.ArgumentParser(description="AI-powered website lead generator")
    parser.add_argument("--city", type=str, default=None, help="Limit to a single city")
    parser.add_argument("--category", type=str, default=None, help="Limit to a single business category")
    parser.add_argument("--limit", type=int, default=None, help="Override results-per-query (useful for testing)")
    parser.add_argument("--skip-justdial", action="store_true", help="Only use OpenStreetMap discovery")
    parser.add_argument("--skip-performance", action="store_true",
                         help="Skip PageSpeed API calls (faster, but 'poor website' detection is weaker)")
    return parser.parse_args()


def main():
    args = parse_args()

    cities = [args.city.strip()] if args.city else config.TARGET_CITIES
    categories = [args.category.strip()] if args.category else config.TARGET_CATEGORIES
    max_results = args.limit if args.limit else config.RESULTS_PER_QUERY

    if not args.skip_performance and not config.PAGESPEED_API_KEY:
        print("[WARN] PAGESPEED_API_KEY not set — performance scoring will be skipped.")
        print("       'No website' leads will still be found fine. Add a key later for")
        print("       richer 'poor performing website' detection, or run with --skip-performance.")
        print()

    print(f"=== Website Lead Generation AI ===")
    print(f"Cities: {cities}")
    print(f"Categories: {categories}")
    print(f"Max results per (city, category): {max_results}")
    print()

    qualified = run_full_pipeline(
        cities, categories, max_results,
        use_justdial=not args.skip_justdial,
        run_performance=not args.skip_performance,
    )

    output_path = f"{config.OUTPUT_DIR}/{config.OUTPUT_FILENAME}"
    final_path = export.export_leads_to_excel(qualified, output_path)
    print(f"\n[DONE] Leads exported to: {final_path}")


if __name__ == "__main__":
    main()
