"""Cooperative cancellation shared by the routing layer and the scraper.

A request runs on a worker thread that can't be killed from outside, so stopping
it is COOPERATIVE: the API sets a threading.Event when the client disconnects, and
the long-running work polls it at safe checkpoints (each beam-search level, each
phase boundary, each navigation hop) and raises ScrapeCancelled to unwind.

This lives in its own module so both app/navigator.py (analysis) and
app/scraper.py (browser) can import it without a circular import — scraper imports
navigator, so the shared piece can't live in either.
"""


class ScrapeCancelled(Exception):
    """The caller signalled that the client disconnected (the user hit Stop).

    Propagating this unwinds the analysis/scrape so the offline beam search stops
    deliberating and the browser (if open) is closed in a `finally` — instead of
    finishing the whole query in the background and blocking the next request.
    """


def check_cancel(cancel):
    """Raise ScrapeCancelled if the caller asked to stop. `cancel` is a
    threading.Event (or None when cancellation isn't wired in, e.g. /ask)."""
    if cancel is not None and cancel.is_set():
        raise ScrapeCancelled()
