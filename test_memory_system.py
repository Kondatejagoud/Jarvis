import os
import unittest
from memory_manager import MemoryManager
import tools.memory_tools as memory_tools

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "test_memory_temp.db"
        self.manager = MemoryManager(self.test_db_path)
        
        # Inject manager into the memory tools global context
        memory_tools.memory_manager = self.manager

    def tearDown(self):
        # Ensure database is closed and removed
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except:
                pass

    def test_short_term_memory(self):
        # Defaults
        self.assertEqual(self.manager.get_short_term("active_project"), "None")
        
        # Setter
        self.manager.set_short_term("active_project", "Project Jarvis")
        self.assertEqual(self.manager.get_short_term("active_project"), "Project Jarvis")
        
        # Invalid key should ignore
        self.manager.set_short_term("invalid_key", "ignore_me")
        self.assertEqual(self.manager.get_short_term("invalid_key"), "None")

    def test_semantic_memory_store_and_retrieve(self):
        # Store
        self.manager.store_semantic_memory("user_name", "Teja Goud", "identity", "high")
        
        # Retrieve all
        m_all = self.manager.retrieve_semantic_memories()
        self.assertEqual(len(m_all), 1)
        self.assertEqual(m_all[0]["key"], "user_name")
        self.assertEqual(m_all[0]["value"], "Teja Goud")
        self.assertEqual(m_all[0]["category"], "identity")
        
        # Retrieve specific category
        m_filtered = self.manager.retrieve_semantic_memories("identity")
        self.assertEqual(len(m_filtered), 1)
        
        m_empty = self.manager.retrieve_semantic_memories("preference")
        self.assertEqual(len(m_empty), 0)

    def test_semantic_memory_deletion(self):
        self.manager.store_semantic_memory("coding_model", "Qwen2.5-Coder", "preference")
        self.assertTrue(self.manager.delete_semantic_memory("coding_model"))
        self.assertFalse(self.manager.delete_semantic_memory("coding_model")) # Already deleted

    def test_context_string_formatting(self):
        self.manager.set_short_term("active_task", "Refactoring loop")
        self.manager.store_semantic_memory("user_name", "Master", "identity")
        
        context_str = self.manager.get_memory_context_string()
        self.assertIn("Active Task: Refactoring loop", context_str)
        self.assertIn("- [identity] user_name: Master", context_str)

    def test_memory_tools_wrappers(self):
        # Test store_memory tool
        res_store = memory_tools.store_memory("editor", "VS Code", "preference")
        self.assertIn("Successfully stored", res_store)
        
        # Test retrieve_memories tool
        res_retrieve = memory_tools.retrieve_memories("preference")
        self.assertIn("editor: VS Code", res_retrieve)
        
        # Test set_context tool
        res_context = memory_tools.set_context(project="Jarvis Core", goal="Implement Memory")
        self.assertIn("Successfully updated", res_context)
        self.assertEqual(self.manager.get_short_term("active_project"), "Jarvis Core")
        self.assertEqual(self.manager.get_short_term("active_goal"), "Implement Memory")
        
        # Test delete_memory tool
        res_delete = memory_tools.delete_memory("editor")
        self.assertIn("Successfully deleted", res_delete)

    def test_context_restoration_persistence(self):
        # Set context in current manager
        self.manager.set_short_term("active_project", "WebScraper")
        self.manager.set_short_term("active_task", "Testing Scraping")
        
        # Instantiate a new MemoryManager pointing to same database
        new_manager = MemoryManager(self.test_db_path)
        
        # Verify it restored successfully
        self.assertEqual(new_manager.get_short_term("active_project"), "WebScraper")
        self.assertEqual(new_manager.get_short_term("active_task"), "Testing Scraping")
        
        # Verify greeting generation
        new_manager.store_semantic_memory("user_name", "Spiderman", "identity")
        greeting = new_manager.get_restored_greeting()
        self.assertEqual(greeting, "Welcome back, Spiderman! Resuming work on Project WebScraper, task: Testing Scraping.")

if __name__ == "__main__":
    unittest.main()
