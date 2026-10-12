import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import token_settings

class TokenSettingsTest(unittest.TestCase):
    def test_roundtrip_permissions_and_delete(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(token_settings,'CONFIG_DIR',Path(d)):
                with patch.object(token_settings,'TOKEN_FILE',Path(d)/'token'):
                    token_settings.save_token('secret-example')
                    self.assertEqual(token_settings.load_token(),'secret-example')
                    if os.name=='posix':
                        self.assertEqual((Path(d)/'token').stat().st_mode & 0o777,0o600)
                    (Path(d)/'token').unlink()
                    self.assertIsNone(token_settings.load_token())
    def test_reject_bad_token(self):
        with self.assertRaises(ValueError): token_settings.save_token('a\nb')

if __name__=='__main__': unittest.main()
