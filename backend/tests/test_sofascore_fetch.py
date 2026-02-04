import httpx
import unittest
from unittest.mock import patch

from services.sofascore_service import SofaScoreService


class FakeResponse:
    def __init__(self, status_code, json_data=None, url="https://example.com"):
        self.status_code = status_code
        self._json = json_data or {}
        self.request = httpx.Request("GET", url)
        self.url = url

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=self.request, response=self)


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, path):
        if not self._responses:
            raise RuntimeError("No more fake responses")
        resp = self._responses.pop(0)
        resp.request = httpx.Request("GET", path)
        return resp


class SofaScoreFetchTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.svc = SofaScoreService()
        # Force predictable base URL order for tests
        self.svc.base_urls = ["https://bad", "https://good"]

    async def test_last_finished_events_fallback_on_403(self):
        good_payload = {"events": [{"id": 1, "status": {"type": "finished"}}]}

        def client_factory(base_url):
            if "bad" in base_url:
                return FakeClient([FakeResponse(403)])
            return FakeClient([FakeResponse(200, good_payload)])

        with patch.object(self.svc, "_client", side_effect=client_factory):
            events = await self.svc.get_last_finished_events(team_id=10, limit=5, max_pages=1)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], 1)

    async def test_upcoming_events_filters_status(self):
        payload = {
            "events": [
                {"id": 11, "status": {"type": "inprogress"}},
                {"id": 12, "status": {"type": "finished"}},
                {"id": 13, "status": {"type": "notstarted"}},
            ]
        }

        def client_factory(base_url):
            return FakeClient([FakeResponse(200, payload)])

        with patch.object(self.svc, "_client", side_effect=client_factory):
            events = await self.svc.get_upcoming_events(team_id=10, limit=5, max_pages=1)

        ids = [e["id"] for e in events]
        self.assertEqual(ids, [11, 13])

    async def test_event_statistics_handles_404(self):
        def client_factory(base_url):
            return FakeClient([FakeResponse(404)])

        with patch.object(self.svc, "_client", side_effect=client_factory):
            data = await self.svc.get_event_statistics(event_id=999)

        self.assertEqual(data, {})


if __name__ == "__main__":
    unittest.main()
