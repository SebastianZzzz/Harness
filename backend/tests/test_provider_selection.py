import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_harness.config import Settings
from aegis_harness.live_state_machine import AegisHarnessLiveBackend


class ProviderSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.previous = {
            key: os.environ.get(key)
            for key in [
                "GEMINI_API_KEY",
                "GEMINI_MODEL",
                "CLOD_API_KEY",
                "CLOD_MODEL",
            ]
        }

    def tearDown(self) -> None:
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_gemini_wins_when_both_keys_exist(self) -> None:
        os.environ["GEMINI_API_KEY"] = "test-gemini"
        os.environ["GEMINI_MODEL"] = "gemini-test-model"
        os.environ["CLOD_API_KEY"] = "test-clod"
        os.environ["CLOD_MODEL"] = "GPT OSS 120B"

        backend = AegisHarnessLiveBackend(Settings.from_env(Path("/tmp/no-such-aegis-env")))

        self.assertEqual(backend.ai.provider_label, "Gemini API primary route")
        self.assertEqual(backend.ai.model_name, "gemini-test-model")

    def test_clod_is_fallback_when_gemini_missing(self) -> None:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["CLOD_API_KEY"] = "test-clod"
        os.environ["CLOD_MODEL"] = "GPT OSS 120B"

        backend = AegisHarnessLiveBackend(Settings.from_env(Path("/tmp/no-such-aegis-env")))

        self.assertEqual(backend.ai.provider_label, "Clod.io fallback route")
        self.assertEqual(backend.ai.model_name, "GPT OSS 120B")


if __name__ == "__main__":
    unittest.main()

