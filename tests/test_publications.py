"""Regression coverage for Scholar record merges and curated display metadata."""

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fetch_scholar", ROOT / "scripts/fetch_scholar.py")
scholar = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scholar)

TQC_ID = "Q7Ybs-gAAAAJ:3fE2CSJIrl8C"
TQC_OLD_ID = "Q7Ybs-gAAAAJ:eQOLeE2rZwMC"
SCI_ID = "Q7Ybs-gAAAAJ:kNdYIx-mwKoC"
SCI_OLD_ID = "Q7Ybs-gAAAAJ:LkGwnXOMwfcC"
EXPECTED_ORDER = ["p5", "p2", "p1", "p3", "p4"]


class PublicationSyncTests(unittest.TestCase):
    def setUp(self):
        self.overrides = json.loads((ROOT / "data/overrides.json").read_text())
        self.articles = json.loads((ROOT / "tests/sample_serpapi.json").read_text())["articles"]
        self.tqc = next(a for a in self.articles if a["citation_id"] == TQC_OLD_ID)

    def transform(self):
        return scholar.transform(self.articles, self.overrides, scholar.DEFAULT_AUTHOR_ID)

    def assert_tqc(self, pubs):
        paper = next(p for p in pubs if p.get("paper_id") == "p4")
        self.assertEqual(paper["year"], 2026)
        self.assertEqual(paper["image"], "assets/img/papers/p4.jpg")
        self.assertEqual(paper["venue_badge"], "ACM TQC")
        self.assertEqual(paper["authors"][-1], {"name": "Qiang Guan", "corresponding": True})
        self.assertIn("https://dl.acm.org/doi/abs/10.1145/3848024",
                      [link["url"] for link in paper["links"]])
        self.assertEqual([p["paper_id"] for p in pubs], EXPECTED_ORDER)
        return paper

    def test_current_scholar_record_keeps_curated_metadata(self):
        # The actual October 2026 record has a new ID, en dash, and 2025 year.
        self.tqc.update(citation_id=TQC_ID, year="2025",
                        publication="ACM Transactions on Quantum Computing",
                        title=self.tqc["title"].replace("Quantum-AI", "Quantum–AI"),
                        cited_by={"value": 4})
        pubs, _ = self.transform()
        paper = self.assert_tqc(pubs)
        self.assertEqual(paper["cited_by"], 4)
        self.assertTrue(paper["links"][-1]["url"].endswith(TQC_ID))

    def test_future_id_uses_unique_normalized_title_and_preserves_order(self):
        self.tqc.update(citation_id="Q7Ybs-gAAAAJ:future-id",
                        title=self.tqc["title"].replace("Quantum-AI", "Quantum–AI"))
        pubs, _ = self.transform()
        self.assert_tqc(pubs)

    def test_old_id_alias_survives_title_change(self):
        self.tqc["title"] = "A changed Scholar title"
        pubs, _ = self.transform()
        self.assert_tqc(pubs)

    def test_both_scholar_ids_produce_one_card_without_summing_citations(self):
        self.tqc["cited_by"] = {"value": 9}
        current = copy.deepcopy(self.tqc)
        current.update(citation_id=TQC_ID, cited_by={"value": 4})
        self.articles.append(current)
        pubs, _ = self.transform()
        paper = self.assert_tqc(pubs)
        self.assertEqual(paper["citation_id"], TQC_ID)
        self.assertEqual(paper["cited_by"], 9)
        self.assertTrue(paper["links"][-1]["url"].endswith(TQC_ID))

    def test_ambiguous_title_does_not_apply_an_arbitrary_override(self):
        publications = copy.deepcopy(self.overrides["publications"])
        publications["duplicate"] = copy.deepcopy(publications[TQC_ID])
        self.tqc["citation_id"] = "unknown-id"
        self.assertEqual(scholar.resolve_override(self.tqc, publications), (None, {}))

    def test_frontispiece_stays_attached_to_original_paper(self):
        pubs, _ = self.transform()
        paper = next(p for p in pubs if p.get("paper_id") == "p2")
        self.assertEqual(paper["year"], 2025)
        feature = paper["frontispiece"]
        configured = self.overrides["publications"][SCI_ID]["frontispiece"]
        self.assertEqual(feature, {key: value for key, value in configured.items()
                                   if key not in ("citation_id", "scholar_title")})
        self.assertEqual(feature["published"], "27 February 2026")
        self.assertTrue((ROOT / feature["image"]).is_file())

    def test_changed_science_id_preserves_frontispiece_and_curated_order(self):
        science = next(a for a in self.articles if a["citation_id"] == SCI_OLD_ID)
        science.update(citation_id="future-science-id",
                       title=science["title"].replace("-", "‐"),
                       cited_by={"value": 20})
        pubs, _ = self.transform()
        paper = next(p for p in pubs if p.get("paper_id") == "p2")
        self.assertEqual(paper["cited_by"], 20)
        self.assertIn("frontispiece", paper)
        self.assertEqual([p["paper_id"] for p in pubs], EXPECTED_ORDER)

    def test_frontispiece_scholar_record_is_not_an_extra_paper(self):
        feature = self.overrides["publications"][SCI_ID]["frontispiece"]
        record = {"citation_id": feature["citation_id"], "title": feature["scholar_title"],
                  "authors": "Y Zhang, Y Yang", "publication": "Advanced Science 13 (12)",
                  "year": "2026"}
        # Cover title matching also survives a future Scholar ID change.
        future = dict(record, citation_id="future-frontispiece-id",
                      title=record["title"].replace("-", "‐"))
        self.articles.extend([record, future])
        pubs, preprints = self.transform()
        self.assertEqual(len(pubs), 5)
        self.assertEqual(len(preprints), 1)
        self.assertEqual(sum(bool(p.get("frontispiece")) for p in pubs), 1)

    def test_manual_accepted_paper_replaces_unicode_preprint_title(self):
        manual = next(p for p in self.overrides["manual_publications"]
                      if p["paper_id"] == "p1")
        self.articles.append({
            "citation_id": "new-qsad-id",
            "title": manual["title"].replace("Utility-Scale", "Utility–Scale"),
            "authors": "Y Zhang, Q Guan",
            "publication": "arXiv preprint",
            "year": "2026",
        })
        pubs, preprints = self.transform()
        self.assertEqual(sum(p.get("paper_id") == "p1" for p in pubs), 1)
        self.assertEqual(len(preprints), 1)
        self.assertEqual(preprints[0]["paper_id"], "pre1")

    def test_in_press_pnas_paper_leads_with_full_author_list(self):
        pubs, _ = self.transform()
        paper = pubs[0]
        self.assertEqual(paper["paper_id"], "p5")
        self.assertEqual(paper["venue_badge"], "PNAS")
        self.assertEqual(paper["status"], "In Press")
        names = [a["name"] for a in paper["authors"]]
        self.assertEqual(len(names), 16)
        # "Sixu Chen" and "Siwei Chen" share a name key; both must survive.
        self.assertIn("Sixu Chen", names)
        self.assertIn("Siwei Chen", names)
        self.assertEqual([a["name"] for a in paper["authors"] if a.get("corresponding")],
                         ["Qiang Guan", "Ruth Nussinov", "Feixiong Cheng"])
        qsad = next(p for p in pubs if p.get("paper_id") == "p1")
        self.assertIn("Siwei Chen", [a["name"] for a in qsad["authors"]])

    def test_pnas_scholar_record_merges_and_keeps_first_place(self):
        manual = next(p for p in self.overrides["manual_publications"]
                      if p["paper_id"] == "p5")
        self.articles.append({
            "citation_id": "Q7Ybs-gAAAAJ:future-pnas",
            "title": manual["title"].replace("Drug-Binding", "Drug–Binding"),
            "authors": "Y Zhang, Y Qiu, W Martin, Y Yang, S Chen, ...",
            "publication": "Proceedings of the National Academy of Sciences",
            "year": "2026",
        })
        pubs, _ = self.transform()
        self.assertEqual(sum(p.get("paper_id") == "p5" for p in pubs), 1)
        self.assertEqual([p["paper_id"] for p in pubs], EXPECTED_ORDER)
        self.assertEqual(len(pubs[0]["authors"]), 16)

    def test_non_first_author_papers_remain_filtered(self):
        pubs, preprints = self.transform()
        self.assertEqual(len(pubs), 5)
        self.assertEqual(len(preprints), 1)
        self.assertFalse(any("REGRID" in p["title"] for p in pubs + preprints))


if __name__ == "__main__":
    unittest.main()
