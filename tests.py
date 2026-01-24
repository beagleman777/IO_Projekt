import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import logic

class TestSecurityLogic(unittest.TestCase):

    def setUp(self):
        self.dummy_img = MagicMock()
        self.dummy_img.read.return_value = b'fake_bytes'

    @patch('logic.database.get_user_by_qr')
    @patch('logic.database.log_access_attempt')
    def test_unknown_qr(self, mock_log, mock_db):
        mock_db.return_value = None
        success, msg, _ = logic.verify_access("QR_GHOST", self.dummy_img)
        self.assertFalse(success)
        self.assertEqual(msg, "Odmowa: Nieznany kod QR.")
        mock_log.assert_called_with("QR_GHOST", "USER_NOT_FOUND", unittest.mock.ANY)

    @patch('logic.database.get_user_by_qr')
    @patch('logic.database.log_access_attempt')
    def test_revoked_user(self, mock_log, mock_db):
        mock_db.return_value = (b'blob', "Janusz", 0)
        
        success, msg, _ = logic.verify_access("QR_JANUSZ", self.dummy_img)
        
        self.assertFalse(success)
        self.assertIn("zablokowany", msg)

    @patch('logic.BIOMETRICS_AVAILABLE', True)
    @patch('logic.face_recognition')           
    @patch('logic.database.get_user_by_qr')
    @patch('logic.database.log_access_attempt')
    def test_biometric_success(self, mock_log, mock_db, mock_fr):
        mock_db.return_value = (np.zeros(128).tobytes(), "CEO", 1)
        mock_fr.face_encodings.return_value = [np.zeros(128)]
        mock_fr.compare_faces.return_value = [True]
        success, msg, name = logic.verify_access("QR_CEO", self.dummy_img)
        self.assertTrue(success)
        self.assertEqual(name, "CEO")
        mock_fr.compare_faces.assert_called_once()
        args, kwargs = mock_fr.compare_faces.call_args
        self.assertEqual(kwargs['tolerance'], 0.5)


if __name__ == '__main__':
    unittest.main()
