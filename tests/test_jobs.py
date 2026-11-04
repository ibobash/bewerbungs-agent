import unittest
from unittest.mock import patch, MagicMock

from bewerbungs_agent.__main__ import fetch_jobs, select_jobs


class JobTests(unittest.TestCase):
    def setUp(self):
        self.jobs = [dict(slug="one", title="Python Engineer", company_name="Example",
                          description="<p>Python &amp; SQL</p>", tags=[],
                          location="Berlin", remote=True, url="https://example.org/job")]

    def test_matching_and_filters(self):
        result = select_jobs(self.jobs, ["Python", "SQL", "Rust"], "berlin", True)
        self.assertEqual(result[0]["score"], 67)
        self.assertEqual(result[0]["description"], "Python & SQL")
        self.assertEqual(select_jobs(self.jobs, ["Rust"]), [])
        self.assertEqual(select_jobs(self.jobs, location="Hamburg"), [])
        self.assertEqual(select_jobs([dict(self.jobs[0], remote=False)], remote=True), [])

    @patch("bewerbungs_agent.__main__.urlopen")
    def test_pagination_deduplicates(self, open_url):
        response = MagicMock()
        response.read.return_value = '{"data": [], "links": {}}'
        open_url.return_value.__enter__.return_value = response
        with patch("bewerbungs_agent.__main__.json.load", side_effect=[
            {"data": self.jobs, "links": {"next": "page2"}},
            {"data": self.jobs, "links": {"next": None}},
        ]):
            self.assertEqual(len(fetch_jobs(3)), 1)
        self.assertEqual(open_url.call_count, 2)


if __name__ == "__main__":
    unittest.main()
