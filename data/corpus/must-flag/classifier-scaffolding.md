# What the logging migration cost

The economics are simple. Storage is cheap and cardinality is not, so a
pipeline that indexes every label pays for the labels rather than the bytes.

We ingested 4TB a day across 240 services. The dangerous part is that the bill
arrived monthly while the cardinality grew hourly, so the first three alerts
looked like billing errors.

Sampling debug lines at 1% took ingest to 900GB a day. The gap between the two
figures has a simple cause: 78% of the volume came from one library's retry
logging, which nobody had read since the library shipped.

The score has limits worth stating. It counts what it can see, and the rest is
the reader's judgment.

One honest caveat before the numbers: this is a single fleet over one quarter,
and the shape of the saving depends on how your services log. Those are the
ones that matter when you plan your own migration.
