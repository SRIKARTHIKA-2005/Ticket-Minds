import sys
import os
import unittest
from werkzeug.security import generate_password_hash, check_password_hash

# Set Python Path to include current directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.config.config import Config
from backend.database import db_mgr
from backend.translations import translator
from backend.ai import ollama_service

class TestTicketMindsPipeline(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Override Database Path for testing to not corrupt production
        Config.DATABASE_PATH = os.path.join(Config.BASE_DIR, 'database', 'ticketminds_test.db')
        
        # Ensure database directory exists
        db_dir = os.path.dirname(Config.DATABASE_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        # Clean any old test database
        if os.path.exists(Config.DATABASE_PATH):
            try:
                os.remove(Config.DATABASE_PATH)
            except Exception:
                pass
                
        db_mgr.init_db()

    @classmethod
    def tearDownClass(cls):
        # Clean test database
        if os.path.exists(Config.DATABASE_PATH):
            try:
                os.remove(Config.DATABASE_PATH)
            except Exception:
                pass

    def test_database_initialization(self):
        """Verifies database tables are created and schema is accessible."""
        conn = db_mgr.get_db_connection()
        cursor = conn.cursor()
        
        # Check users table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        self.assertIsNotNone(cursor.fetchone(), "Users table should exist")
        
        # Check tickets table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tickets';")
        self.assertIsNotNone(cursor.fetchone(), "Tickets table should exist")
        
        # Check messages table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages';")
        self.assertIsNotNone(cursor.fetchone(), "Messages table should exist")
        
        conn.close()

    def test_user_creation_and_hashing(self):
        """Verifies user data insertions and password hash comparisons."""
        conn = db_mgr.get_db_connection()
        cursor = conn.cursor()
        
        email = "test_user@ticketminds.com"
        name = "Test User"
        raw_pw = "pass123"
        role = "user"
        
        hashed = generate_password_hash(raw_pw)
        self.assertTrue(check_password_hash(hashed, raw_pw))
        
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed, role)
        )
        conn.commit()
        
        # Retrieve and verify
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        self.assertIsNotNone(user)
        self.assertEqual(user['name'], name)
        self.assertEqual(user['role'], role)
        self.assertTrue(check_password_hash(user['password'], raw_pw))
        
        conn.close()

    def test_glossary_protection_logic(self):
        """Verifies that glossary terms are replaced with placeholders and restored correctly."""
        mock_glossary = {
            "VPN": "VPN",
            "API": "API",
            "Firewall": "Firewall"
        }
        
        test_text = "Check the Firewall settings and reset my VPN connection."
        
        # Protect text
        protected, placeholders = translator.protect_text(test_text, mock_glossary)
        
        # Verify placeholders exist in protected text
        self.assertIn("__GL_0__", protected)
        self.assertIn("__GL_1__", protected)
        self.assertNotIn("Firewall", protected)
        self.assertNotIn("VPN", protected)
        
        # Restore text
        restored = translator.restore_text(protected, placeholders)
        self.assertEqual(restored, test_text, "Restored text should match the original precisely")

    def test_translation_engine(self):
        """Verifies that translations process Spanish text to English while preserving glossary words."""
        # Force add terms in glossary file if not already present
        glossary = translator.load_glossary()
        self.assertIn("VPN", glossary, "Glossary JSON must contain VPN for testing")
        
        spanish_query = "Necesito cambiar mi contrasenia de la VPN por favor."
        
        # Translate to English
        translated = translator.translate_text(spanish_query, 'en', 'es')
        
        # Verify VPN is preserved exactly (case preserved)
        self.assertIn("VPN", translated)
        self.assertNotIn("__GL_", translated, "All placeholders must be cleaned up")
        
        # Verify general meaning is translated
        self.assertTrue(any(word in translated.lower() for word in ["password", "change", "please", "need"]))

    def test_ollama_fallback_handler(self):
        """Verifies that the Ollama service returns mock fallback values when offline."""
        # Ensure it doesn't fail even if Ollama is not active
        val = ollama_service.validate_translation("Hola", "Hello", "es")
        self.assertIsInstance(val, dict)
        self.assertIn("valid", val)
        
        sugg = ollama_service.get_context_suggestions(
            {"status": "Open", "original_language": "es"},
            [{"sender_type": "user", "translated_text": "Reset my VPN server please."}]
        )
        self.assertIn("summary", sugg)
        self.assertIn("suggested_reply", sugg)
        self.assertIn("VPN", sugg["suggested_reply"], "Fallback suggester should detect 'vpn' and include it")

if __name__ == '__main__':
    print("=" * 60)
    print("           TICKETMINDS SYSTEM INTEGRATION TESTING")
    print("=" * 60)
    unittest.main()
