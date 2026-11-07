"""Source adapters. Each module exposes fetch(company_config, session) -> list[Job].

To support a new portal type, add a module here and register it in SOURCES,
and in URL_SOURCES if its config uses `url:` rather than `board:`.
"""

from . import ashby, bearingpoint, greenhouse, jibe, lever, oleeo, phenom, talemetry, workday, yello

SOURCES = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "workday": workday.fetch,
    "jibe": jibe.fetch,
    "yello": yello.fetch,
    "talemetry": talemetry.fetch,
    "oleeo": oleeo.fetch,
    "bearingpoint": bearingpoint.fetch,
    "phenom": phenom.fetch,
}

# Sources configured with a full `url:`; the rest use a `board:` slug.
URL_SOURCES = {"workday", "jibe", "yello", "talemetry", "oleeo", "bearingpoint", "phenom"}
