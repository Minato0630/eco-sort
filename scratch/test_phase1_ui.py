import os
import re
import unittest

class TestPhase1UI(unittest.TestCase):
    def test_01_assets_exist(self):
        self.assertTrue(os.path.exists("frontend/css/ecosort.css"), "ecosort.css missing!")
        self.assertTrue(os.path.exists("frontend/js/theme.js"), "theme.js missing!")

    def test_02_index_html_elements(self):
        with open("frontend/index.html", "r", encoding="utf-8") as f:
            html = f.read()

        # Check CSS and JS linked
        self.assertIn('href="css/ecosort.css"', html)
        self.assertIn('src="js/theme.js"', html)

        # Check core student dashboard IDs
        for expected_id in ["authView", "appView", "statPoints", "statCO2", "statSorted", "statRank", "recyclingChart"]:
            self.assertIn(f'id="{expected_id}"', html, f"Missing id={expected_id} in index.html")

        # Check AI Scanner enhancements
        self.assertIn('id="dropzone"', html)
        self.assertIn('id="resDetails"', html)
        self.assertIn('id="resUncertaintyBox"', html, "Uncertainty alert box missing in index.html!")
        self.assertIn('id="resTopPredictionsBox"', html, "Top predictions box missing in index.html!")

        # Verify legacy simulated OTP block was completely removed
        self.assertNotIn('id="communicationSimulation"', html, "Legacy simulation mockup should be removed!")
        self.assertNotIn('(Copy-paste the OTP from above to verify)', html)

    def test_03_admin_html_elements(self):
        with open("frontend/admin.html", "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('href="css/ecosort.css"', html)
        self.assertIn('src="js/theme.js"', html)

        for expected_id in ["adminTotalUsers", "adminTotalScans", "adminTotalCO2", "adminCompletedPickups", "userRows", "retrainStatus", "terminalLog", "pickupsRows"]:
            self.assertIn(f'id="{expected_id}"', html, f"Missing id={expected_id} in admin.html")

        # Check dataset text corrected from legacy unverified count
        self.assertNotIn("27 campus sorted sample images", html)
        self.assertIn("verified campus sorted sample images", html)

    def test_04_collector_html_elements(self):
        with open("frontend/collector.html", "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('href="css/ecosort.css"', html)
        self.assertIn('src="js/theme.js"', html)

        for expected_id in ["statAvailable", "statActive", "statCompleted", "collectorPoints", "map", "activeClaimsRows", "allPickupsRows"]:
            self.assertIn(f'id="{expected_id}"', html, f"Missing id={expected_id} in collector.html")

        # Verify confirmation prompt in claim/complete
        self.assertIn("confirm(`Are you sure you want to", html)

if __name__ == "__main__":
    unittest.main()
