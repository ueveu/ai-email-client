import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import unittest
from src.services.credential_service import CredentialService

class TestCredentialService(unittest.TestCase):
    def setUp(self):
        self.credential_service = CredentialService()
        self.test_email = "test@example.com"
        self.test_password = "securepassword123"

    def test_store_and_get_password(self):
        # Store the password
        self.assertTrue(self.credential_service.store_password(self.test_email, self.test_password))

        # Retrieve the password
        retrieved_password = self.credential_service.get_password(self.test_email)
        self.assertEqual(retrieved_password, self.test_password)

if __name__ == "__main__":
    unittest.main() 