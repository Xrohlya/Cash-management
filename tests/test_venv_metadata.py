from pathlib import Path
import tempfile
import unittest

from tools.clean_venv_metadata import APPLEDOUBLE, clean_metadata


class MetadataTests(unittest.TestCase):
    def test_only_verified_sidecars_inside_the_environment_are_quarantined(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "venv"
            site = root / "lib" / "python3.13" / "site-packages"
            site.mkdir(parents=True)
            metadata = site / "._rapidfuzz-3.14.6.dist-info"
            metadata.write_bytes(APPLEDOUBLE + b"metadata")
            other = site / "._ordinary.dist-info"
            other.write_bytes(b"not AppleDouble")
            real = site / "rapidfuzz-3.14.6.dist-info"
            real.mkdir()
            outside = Path(folder) / "site-packages"
            outside.mkdir()
            external = outside / "._external.dist-info"
            external.write_bytes(APPLEDOUBLE)
            self.assertEqual(clean_metadata(root, [str(site), str(outside)]), 1)
            self.assertFalse(metadata.exists())
            self.assertTrue(other.exists())
            self.assertTrue(real.is_dir())
            self.assertTrue(external.exists())
            self.assertEqual(clean_metadata(root, [str(site)]), 0)
