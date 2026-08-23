# Blind quality-rating protocol

Judge the writing in each item. Do not guess whether a person or model wrote it, and
do not use a detector or inspect any method mapping. Read only the blind packet.

Assign one label and severity:

- `clean`, severity 1 or 2: no material AI-register or writing-quality defect needs
  correction. Severity 2 permits a minor weakness that does not justify rewriting.
- `borderline`, severity 3: a real weakness is present, but the case is ambiguous or
  too slight to call sloppy.
- `sloppy`, severity 4 or 5: the text materially needs editing for one or more allowed
  signals. Severity 5 is pervasive.

Allowed signals are `hollow_substance`, `semantic_redundancy`, `vague_reference`,
`canned_framing`, `genre_mismatch`, `local_repetition`, `unsupported_attribution`,
`reader_process_leak`, `rhythm`, and `formatting`. Clean items must have no signals;
sloppy items must have at least one. Judge each item independently. Do not reward
brevity by itself, invent missing context, or penalize a legitimate formal register.

Return the exact JSON schema supplied in the rating task. Do not include prose outside
the JSON file.
