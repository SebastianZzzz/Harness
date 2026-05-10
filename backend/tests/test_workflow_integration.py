import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aegis_harness import AegisHarnessMockBackend, TaskStatus


class WorkflowIntegrationTest(unittest.TestCase):
    def test_full_five_phase_flow_finishes_after_bounded_repair(self) -> None:
        backend = AegisHarnessMockBackend()
        task = backend.start(
            "Audit a TypeScript wallet integration for unsafe transaction signing, add tests, "
            "and return a maintainer-ready patch summary."
        )

        self.assertEqual(task.status, TaskStatus.PENDING_APPROVAL)
        self.assertIn("Negative Constraints From AI Preflight", task.prompt)
        self.assertEqual(len(task.references), 3)
        self.assertEqual(len(task.risks), 4)

        finished = backend.approve(task.id)

        self.assertEqual(finished.status, TaskStatus.FINISHED)
        self.assertLessEqual(finished.repair_attempts, finished.max_iterations)
        self.assertEqual(finished.repair_attempts, 1)
        self.assertEqual(finished.review.status, "passed")
        self.assertIsNotNone(finished.route)
        self.assertGreaterEqual(finished.route.difficulty, 4)
        self.assertEqual(finished.route.model, "GPT OSS 120B")
        self.assertIsNotNone(finished.code)

        event_types = [event.type for event in finished.events]
        self.assertIn("hitl.approval.requested", event_types)
        self.assertIn("compute.route.selected", event_types)
        self.assertIn("sandbox.review.completed", event_types)
        self.assertIn("workflow.finished", event_types)
        self.assertNotIn("settlement.completed", event_types)


if __name__ == "__main__":
    unittest.main()
