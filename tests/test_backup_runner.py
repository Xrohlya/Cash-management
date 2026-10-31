from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from services.backup_runner import backup_is_due


class BackupRunnerTests(unittest.TestCase):
    def test_daily_backup_is_due_only_when_no_recent_completed_copy_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "backups").mkdir()
            with patch("services.backup_runner.ROOT", root):
                self.assertTrue(backup_is_due(now=100000))
                (root / "backups" / ".pending-backup-test").touch()
                self.assertTrue(backup_is_due(now=100000))
                backup = root / "backups" / "postgres_backup_test.json"
                backup.touch()
                os.utime(backup, (100000, 100000))
                self.assertFalse(backup_is_due(now=100001))
                self.assertTrue(backup_is_due(now=186400))
