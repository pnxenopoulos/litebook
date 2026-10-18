"""Run the same representative suite with order creation inside the timed region."""

import sys

from benchmarks.book import main

if __name__ == "__main__":
    sys.argv.extend(["--mode", "create-add"])
    main()
