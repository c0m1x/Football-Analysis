import os
import unittest

import httpx

from services.sofascore_service import SofaScoreService


class SofaScoreLiveTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_last_events(self):
        if os.getenv("RUN_LIVE_SOFASCORE_TESTS") != "1":
            self.skipTest("Set RUN_LIVE_SOFASCORE_TESTS=1 to enable live SofaScore tests")

        team_id = int(os.getenv("GIL_VICENTE_TEAM_ID", "9764"))
        svc = SofaScoreService()

        try:
            events = await svc.get_last_finished_events(team_id, limit=1, max_pages=1)
        except httpx.HTTPStatusError as e:
            status = getattr(e.response, "status_code", None)
            if status == 403:
                self.fail(
                    "SofaScore denied this environment (403). "
                    "This live test requires an environment with permitted access."
                )
            raise

        self.assertIsInstance(events, list)
        self.assertGreaterEqual(len(events), 0)


if __name__ == "__main__":
    unittest.main()
