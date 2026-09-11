"""Offline contracts for the simulated reader-review helper."""
import contextlib
import copy
import hashlib
from html.parser import HTMLParser
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reader_review as rr


def journal(manifest, reader="R1", count=1, stop=False, mode="sequential"):
    return {
        "source_sha256": manifest["source_sha256"], "review_id": manifest["review_id"], "reader": reader,
        "context_mode": mode,
        "entries": [
            {"note_id": f"{reader}-{p['id']}", "passage_id": p["id"],
             "attention": "steady", "reaction": "The claim is clear.",
             "needed": "An example.", "keep_reading": not (stop and i == count - 1)}
            for i, p in enumerate(manifest["passages"][:count])
        ],
    }


def skim_review(manifest):
    return {"source_sha256": manifest["source_sha256"], "review_id": manifest["review_id"],
            "context_mode": "sequential", "reaction": "The opening looks useful.",
            "would_open": True}


class ReaderReview(unittest.TestCase):
    def setUp(self):
        self.source = "# Clear title\r\n\r\nOpening claim.\r\n\r\nSECRET FUTURE paragraph.\r\n"
        self.manifest = rr.prepare(self.source, "Busy engineering managers")

    def test_exact_source_hash_and_stable_passages(self):
        self.assertEqual(self.manifest["source"], self.source)
        self.assertEqual(self.manifest["source_sha256"], hashlib.sha256(self.source.encode()).hexdigest())
        self.assertEqual([p["id"] for p in self.manifest["passages"]], ["p1", "p2", "p3"])
        self.assertEqual(rr.prepare(self.source, "Busy engineering managers"), self.manifest)
        for p in self.manifest["passages"]:
            self.assertEqual(self.source[p["start"]:p["end"]], p["text"])

    def test_fence_blank_lines_remain_in_one_passage(self):
        source = "Before.\n\n```python\nx = 1\n\ny = 2\n```\n\nAfter."
        m = rr.prepare(source, "Developers")
        self.assertEqual(len(m["passages"]), 3)
        self.assertIn("x = 1\n\ny = 2", m["passages"][1]["text"])

    def test_longer_fences_and_adjacent_headings_do_not_split_code(self):
        source = "# Title\nOpening.\n\n````\n```\n\n# Not a heading\n````\nTail."
        m = rr.prepare(source, "Developers")
        self.assertEqual(len(m["passages"]), 4)
        self.assertIn("# Not a heading", m["passages"][2]["text"])
        self.assertNotIn("Not a heading", json.dumps(rr.skim(m)))

    def test_next_only_reveals_next_and_prior_notes(self):
        payload = rr.next_passage(self.manifest, "R1")
        encoded = json.dumps(payload)
        self.assertEqual(payload["passage"]["id"], "p1")
        self.assertNotIn("Opening claim", encoded)
        self.assertNotIn("SECRET FUTURE", encoded)
        payload = rr.next_passage(self.manifest, "R1", journal(self.manifest))
        self.assertEqual(payload["passage"]["id"], "p2")
        self.assertEqual(len(payload["prior_notes"]), 1)
        self.assertNotIn("SECRET FUTURE", json.dumps(payload))

    def test_stop_is_terminal_and_hides_unread_text(self):
        notes = journal(self.manifest, stop=True)
        payload = rr.next_passage(self.manifest, "R1", notes)
        self.assertTrue(payload["done"])
        self.assertEqual(payload["reason"], "stopped")
        self.assertNotIn("passage", payload)
        self.assertNotIn("SECRET FUTURE", json.dumps(payload))
        notes["entries"].extend(journal(self.manifest, count=2)["entries"][1:])
        with self.assertRaises(rr.ContractError):
            rr.next_passage(self.manifest, "R1", notes)

    def test_complete_hides_source(self):
        payload = rr.next_passage(self.manifest, "R2", journal(self.manifest, "R2", 3))
        self.assertTrue(payload["done"])
        self.assertEqual(payload["reason"], "finished")
        self.assertNotIn("SECRET FUTURE", json.dumps(payload))

    def test_journal_binding_and_types(self):
        for mutation in (
            lambda n: n.update(source_sha256="wrong"),
            lambda n: n.update(review_id="wrong"),
            lambda n: n.update(reader="R2"),
            lambda n: n.update(context_mode="blind"),
            lambda n: n["entries"][0].update(passage_id="p2"),
            lambda n: n["entries"][0].update(note_id="R1-p2"),
            lambda n: n["entries"][0].update(attention="maybe"),
            lambda n: n["entries"][0].update(keep_reading=1),
            lambda n: n["entries"][0].update(reaction=[]),
        ):
            notes = journal(self.manifest)
            mutation(notes)
            with self.subTest(notes=notes), self.assertRaises(rr.ContractError):
                rr.next_passage(self.manifest, "R1", notes)

    def test_same_source_different_audience_rejects_old_journals_and_skim(self):
        other = rr.prepare(self.source, "New readers with different needs")
        old = journal(self.manifest, stop=True)
        self.assertEqual(other["source_sha256"], self.manifest["source_sha256"])
        self.assertNotEqual(other["review_id"], self.manifest["review_id"])
        for operation in (
            lambda: rr.next_passage(other, "R1", old),
            lambda: rr.recall(other, "R1", old),
            lambda: rr.report(other, [old, journal(other, "R2", stop=True)], skim_review(other)),
            lambda: rr.report(other, [journal(other, r, stop=True) for r in ("R1", "R2")], skim_review(self.manifest)),
        ):
            with self.subTest(operation=operation), self.assertRaises(rr.ContractError):
                operation()

    def test_manifest_tampering_rejected(self):
        for field, value in (("source", "Changed"), ("source_sha256", "wrong"), ("passages", [])):
            m = copy.deepcopy(self.manifest)
            m[field] = value
            with self.subTest(field=field), self.assertRaises(rr.ContractError):
                rr.next_passage(m, "R1")
        m = copy.deepcopy(self.manifest)
        m["passages"][0]["start"] = 0.0
        with self.assertRaises(rr.ContractError):
            rr.next_passage(m, "R1")

    def test_recall_is_notes_only_and_citation_bound(self):
        notes = journal(self.manifest, stop=True)
        payload = rr.recall(self.manifest, "R1", notes)
        self.assertNotIn("source", payload)
        self.assertNotIn("# Clear title", json.dumps(payload))
        self.assertNotIn("SECRET FUTURE", json.dumps(payload))
        self.assertEqual(payload["allowed_note_ids"], ["R1-p1"])
        notes["recall"] = {"takeaway": "A clear claim.", "questions": [], "note_ids": ["R1-p3"]}
        with self.assertRaises(rr.ContractError):
            rr.recall(self.manifest, "R1", notes)

    def test_skim_has_only_preview_and_unseen_body(self):
        preview = rr.skim(self.manifest)
        self.assertIn("Opening claim", json.dumps(preview))
        self.assertNotIn("SECRET FUTURE", json.dumps(preview))
        self.assertEqual(preview["skipped_body"], "unseen")

    def test_preview_is_bounded_and_includes_title(self):
        source = "# Title\n\n" + "Opening " * 1000 + "HIDDEN END\n\n" + "\n\n".join(f"## Heading {i}" for i in range(30))
        preview = rr.skim(rr.prepare(source, "Readers"))
        self.assertEqual(preview["title"], "# Title")
        self.assertLessEqual(len(preview["headings"]), 12)
        self.assertNotIn("HIDDEN END", json.dumps(preview))
        self.assertNotIn("Heading 29", json.dumps(preview))

    def test_report_escapes_every_untrusted_field_and_marks_unread(self):
        m = rr.prepare("<script>alert(1)</script>\n\nUnread words.", '<img src=x onerror="x">')
        reviews = [journal(m, "R1", stop=True), journal(m, "R2", stop=True, mode="retrospective")]
        reviews[0]["entries"][0]["reaction"] = "<img src=x onerror='bad'>"
        report = rr.report(m, reviews, skim_review(m))
        self.assertNotIn("<script>", report)
        self.assertNotIn("<img ", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("Content-Security-Policy", report)
        self.assertIn("default-src 'none'", report)
        self.assertIn("not read", report)
        self.assertIn("retrospective", report)
        self.assertIn("simulated hypotheses", report)
        self.assertIn("cannot attest", report)

    def test_report_requires_both_readers_and_completed_journals(self):
        with self.assertRaises(rr.ContractError):
            rr.report(self.manifest, [journal(self.manifest)], skim_review(self.manifest))
        with self.assertRaises(rr.ContractError):
            rr.report(self.manifest, [journal(self.manifest, "R1"), journal(self.manifest, "R2")], skim_review(self.manifest))

    def test_report_pairs_both_readers_with_each_exact_source_passage(self):
        reviews = [journal(self.manifest, reader, 3) for reader in ("R1", "R2")]
        output = rr.report(self.manifest, reviews, skim_review(self.manifest))
        self.assertIn("Simulated reactions generated by your AI assistant", output)
        for i in range(1, 4):
            marker = f'data-passage-row="p{i}"'
            self.assertIn(marker, output)
            row = output.split(marker, 1)[1].split('data-passage-row=', 1)[0]
            self.assertIn(f'R1-p{i}</a>', row)
            self.assertIn(f'R2-p{i}</a>', row)
            if i < 3:
                self.assertNotIn(f'R1-p{i+1}</a>', row)

        class DraftParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.reading = False
                self.text = []

            def handle_starttag(self, tag, attrs):
                if tag == "pre" and dict(attrs).get("class") == "draft":
                    self.reading = True

            def handle_endtag(self, tag):
                if tag == "pre":
                    self.reading = False

            def handle_data(self, text):
                if self.reading:
                    self.text.append(text)

        parser = DraftParser()
        parser.feed(output)
        self.assertEqual("".join(parser.text), self.source)

    def test_word_strips_cover_whole_draft_after_bailout(self):
        reviews = [journal(self.manifest, reader, stop=True) for reader in ("R1", "R2")]
        data = rr.report_data(self.manifest, reviews, skim_review(self.manifest))
        self.assertEqual([p["attention"] for p in data["attention"]["R1"]], ["steady", "not read", "not read"])
        self.assertEqual(sum(p["words"] for p in data["attention"]["R1"]), len(self.source.split()))

    def test_recall_requires_terminal_and_followups_require_seen_citations(self):
        with self.assertRaises(rr.ContractError):
            rr.recall(self.manifest, "R1", journal(self.manifest))
        notes = journal(self.manifest, stop=True)
        notes["followups"] = [{"question": "What is missing?", "answer": "An example.", "note_ids": ["R1-p1"]}]
        rr.recall(self.manifest, "R1", notes)
        notes["followups"][0]["note_ids"] = ["R2-p1"]
        with self.assertRaises(rr.ContractError):
            rr.recall(self.manifest, "R1", notes)

    def test_malformed_types_and_unknown_fields_have_contract_errors(self):
        malformed = [None, [], {}, {"source": "x"}]
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(rr.ContractError):
                rr.next_passage(value, "R1")
        for value in [None, [], {}, {**journal(self.manifest), "source": "injected future text"}]:
            with self.subTest(value=value), self.assertRaises(rr.ContractError):
                rr.validate_journal(self.manifest, "R1", value)
        with self.assertRaises(rr.ContractError):
            rr.prepare("   ", "People")
        with self.assertRaises(rr.ContractError):
            rr.prepare("Text", "")

    def test_previous_checks_audience_lenses_and_uses_revision_warning(self):
        reviews = [journal(self.manifest, reader, stop=True) for reader in ("R1", "R2")]
        old = rr.report_data(self.manifest, reviews, skim_review(self.manifest))
        revised = rr.prepare("An improved opening.\n\nAn example.", self.manifest["audience"])
        revised_reviews = [journal(revised, reader, stop=True) for reader in ("R1", "R2")]
        output = rr.report(revised, revised_reviews, skim_review(revised), old)
        self.assertIn("not aligned", output)
        old["manifest"]["audience"] = "Different readers"
        with self.assertRaises(rr.ContractError):
            rr.report(revised, revised_reviews, skim_review(revised), old)

    def test_previous_rejects_changed_lenses_and_tampered_attention(self):
        reviews = [journal(self.manifest, r, stop=True) for r in ("R1", "R2")]
        old = rr.report_data(self.manifest, reviews, skim_review(self.manifest))
        for mutate in (lambda p: p["manifest"]["lenses"].update(R1="Different lens"),
                       lambda p: p["attention"]["R1"][0].update(attention="engaged")):
            previous = copy.deepcopy(old)
            mutate(previous)
            with self.subTest(previous=previous), self.assertRaises(rr.ContractError):
                rr.report(self.manifest, reviews, skim_review(self.manifest), previous)

    def test_cli_preserves_crlf_and_prints_errors_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            draft = Path(folder) / "draft.md"
            draft.write_bytes(self.source.encode())
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(rr.main(["prepare", str(draft), "--audience", "Engineers"]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["source"], self.source)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(rr.main(["next", str(draft), "--reader", "R1"]), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_cli_roundtrip_all_commands_and_previous(self):
        def run(args):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = rr.main(args)
            self.assertEqual(status, 0, err.getvalue())
            return out.getvalue()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest, notes, reviews, skim, previous = [root / n for n in ("manifest.json", "notes.json", "reviews.json", "skim.json", "previous.json")]
            manifest.write_text(json.dumps(self.manifest))
            notes.write_text(json.dumps(journal(self.manifest, stop=True)))
            reviews.write_text(json.dumps([journal(self.manifest, r, stop=True) for r in ("R1", "R2")]))
            skim.write_text(json.dumps(skim_review(self.manifest)))
            first = json.loads(run(["next", str(manifest), "--reader", "R1", "--context-mode", "sequential"]))
            self.assertEqual(first["context_mode"], "sequential")
            self.assertTrue(json.loads(run(["next", str(manifest), "--reader", "R1", "--notes", str(notes)]))["done"])
            self.assertIn("allowed_note_ids", json.loads(run(["recall", str(manifest), "--reader", "R1", "--notes", str(notes)])))
            self.assertEqual(json.loads(run(["skim", str(manifest)]))["skipped_body"], "unseen")
            report_args = ["report", str(manifest), "--reviews", str(reviews), "--skim", str(skim)]
            previous.write_text(run(report_args + ["--json"]))
            self.assertTrue(run(report_args + ["--previous", str(previous)]).startswith("<!doctype html>"))

    def test_cli_duplicate_json_and_limits_are_clear_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid = Path(folder) / "invalid.json"
            invalid.write_text('{"schema":1,"schema":2}')
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(rr.main(["skim", str(invalid)]), 2)
            self.assertIn("duplicate JSON field", err.getvalue())
            with self.assertRaises(rr.ContractError):
                rr._read(invalid, 2)

    @unittest.skipUnless(hasattr(sys, "get_int_max_str_digits") and sys.get_int_max_str_digits() > 0,
                         "Python has no active integer-string parser limit")
    def test_cli_oversized_json_integer_is_clear_error(self):
        with tempfile.TemporaryDirectory() as folder:
            invalid = Path(folder) / "integer.json"
            invalid.write_text('{"schema":' + "1" * (sys.get_int_max_str_digits() + 1) + '}')
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                self.assertEqual(rr.main(["skim", str(invalid)]), 2)
            self.assertIn("error:", err.getvalue())
            self.assertNotIn("Traceback", err.getvalue())


if __name__ == "__main__":
    unittest.main()
