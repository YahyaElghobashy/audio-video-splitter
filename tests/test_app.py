import unittest
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        app.config['TESTING'] = True
        
    def test_home_page(self):
        """Test that the home page loads correctly."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Split Audio/Video', response.data)
        
    def test_youtube_page(self):
        """Test that the YouTube page loads correctly."""
        response = self.app.get('/youtube')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'YouTube Video Processor', response.data)
        
    def test_history_page(self):
        """Test that the history page loads correctly."""
        response = self.app.get('/history')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Processing History', response.data)
        
if __name__ == '__main__':
    unittest.main() 