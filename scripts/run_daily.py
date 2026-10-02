"""Daily news scraper entry point.

Runs every configured news spider sequentially in one Python process and
exits non-zero only when the whole run is broken, so a single misbehaving
outlet never takes down the others.

Usage (from the repository root):

    uv run python scripts/run_daily.py
    uv run python scripts/run_daily.py fana etv
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Line-buffered UTF-8 so progress shows up in the GitHub Actions log as it
# happens, and so the emoji status markers do not blow up on the cp1252
# default encoding Windows uses for redirected output.
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True, errors="replace")

# -----------------------------
# PATH BOOTSTRAP
# -----------------------------
# Runs correctly from any working directory, so GitHub Actions does not
# have to cd into the Scrapy project first.
#
#   <root>/scripts/run_daily.py
#   <root>/scraper/scrapy.cfg
#   <root>/scraper/scraper/settings.py
#   <root>/db/
#
# `<root>/scraper` goes on the path so `scraper.settings` and
# `scraper.spiders` resolve; `<root>` goes on the path so `db` resolves.
ROOT = Path(__file__).resolve().parents[1]
SCRAPER_PROJECT = ROOT / "scraper"

for _path in (str(SCRAPER_PROJECT), str(ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)


from scrapy.crawler import CrawlerRunner  # noqa: E402
from scrapy.utils.log import configure_logging  # noqa: E402
from scrapy.utils.project import get_project_settings  # noqa: E402
from twisted.python.failure import Failure  # noqa: E402

# Scrapy requires the asyncio reactor, and `verify_installed_reactor()` runs
# on the first crawl. Installing anything from `twisted.internet` first would
# lock in the default SelectReactor and the crawl deferred would never fire,
# so this must happen before the reactor import below.
from scrapy.utils.reactor import install_reactor  # noqa: E402

install_reactor("twisted.internet.asyncioreactor.AsyncioSelectorReactor")

from twisted.internet import defer, reactor  # noqa: E402

# -----------------------------
# SCRAPER LIST
# -----------------------------
# (human readable outlet name, Scrapy spider name)
#
# To add an outlet: create the spider, add its source config, then add one
# line here. The GitHub Actions workflow needs no change.
SCRAPERS = [
    ("fana", "fana"),
    ("etv", "etv"),
]

# Commented out until the spiders exist. Do not enable a name that has no
# matching spider file, it will be reported as a failure every night.
#
# SCRAPERS += [
#     ("ena", "ena"),
#     ("reporter", "reporter"),
#     ("addis_standard", "addis_standard"),
#     ("addis_fortune", "addis_fortune"),
# ]


def build_settings():
    """Load scraper/scraper/settings.py without depending on the cwd.

    get_project_settings() finds scrapy.cfg by walking up from the current
    directory, which breaks when the runner is invoked from the repo root.
    Point SCRAPY_SETTINGS_MODULE at the dotted path instead.
    """
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", "scraper.settings")
    return get_project_settings()


def _watchdog_timeout(deferred) -> None:
    """Abort the run if the crawls have not finished in time."""
    print(f"\n⏱️  Timed out after {overall_timeout}s, aborting.")
    deferred.addErrback(lambda _: None)
    reactor.stop()


# -----------------------------
# RUN ONE SPIDER
# -----------------------------
def run_spider(runner: CrawlerRunner, spider_name: str) -> defer.Deferred:
    """Queue a single spider. The deferred fires when the crawl finishes.

    Scrapy can only run one crawl per reactor at a time, so the caller
    chains these sequentially rather than starting them all at once.
    """
    return runner.crawl(spider_name)


# -----------------------------
# RUN ALL SCRAPERS
# -----------------------------
@defer.inlineCallbacks
def run_all(runner: CrawlerRunner, scrapers: list[tuple[str, str]]):
    """Run each spider in turn, never letting one failure stop the rest."""
    successful: list[str] = []
    failed: list[tuple[str, str]] = []

    for outlet, spider_name in scrapers:

        print(f"🔄 Scraping {outlet}...")

        try:
            yield run_spider(runner, spider_name)

        except Exception as exc:
            # A dead outlet must not take the nightly run down with it.
            message = f"{type(exc).__name__}: {exc}"
            print(f"❌ {outlet} failed: {message}")
            failed.append((outlet, message))
            continue

        print(f"✅ {outlet} success")
        successful.append(outlet)

    return successful, failed


# Hard ceiling for the whole run, in seconds. The workflow also sets
# `timeout-minutes` as a second line of defence.
overall_timeout = int(os.getenv("SCRAPER_TIMEOUT", 90 * 60))


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Send Scrapy's own logs to stdout so everything is interleaved in one
    # chronological stream in the CI log.
    configure_logging()
    logging.getLogger("scrapy").setLevel(logging.INFO)

    # Accept a subset from the CLI: `run_daily.py fana`
    scrapers = SCRAPERS
    if len(sys.argv) > 1:
        requested = set(sys.argv[1:])
        scrapers = [s for s in SCRAPERS if s[1]
                    in requested or s[0] in requested]

    if not scrapers:
        print("No scrapers configured.")
        return 1

    print("=" * 40)
    print("Daily News Scraper")
    print("=" * 40)
    print()

    settings = build_settings()
    runner = CrawlerRunner(settings)

    # Scrapy drives the reactor, so hand it a deferred chain and let it run
    # the event loop. Each crawl is awaited before the next one starts.
    deferred = run_all(runner, scrapers)
    deferred.addErrback(
        lambda failure: print(f"❌ Daily run aborted: {failure.value}")
    )

    def print_summary(results):
        successful, failed = results

        print()
        print("=" * 40)
        print("Daily scrape completed")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")

        for outlet, message in failed:
            print(f"  - {outlet}: {message}")

        print("=" * 40)

        # Hand the results onward, then stop the loop. reactor.stop() takes
        # effect immediately, so anything returned after this is discarded.
        reactor.callLater(0, reactor.stop)

        return results

    deferred.addCallback(print_summary)

    # Safety net. Without this a stalled download would hang the process
    # forever and the GitHub Actions job would sit until its own timeout.
    reactor.callLater(overall_timeout, _watchdog_timeout, deferred)

    reactor.run()

    # After a watchdog abort the deferred has no usable result, so report
    # that rather than pretending the run succeeded.
    if not deferred.called:
        print("\n❌ Run aborted before any scraper reported back.")
        return 1

    if isinstance(deferred.result, Failure):
        print("\n❌ Daily run failed.")
        return 1

    successful, failed = deferred.result

    # Partial success is a successful run. A total wipeout is not.
    if not successful:
        print("\nAll scrapers failed.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
