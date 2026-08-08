import os
import json
import unittest
from events import EventBus
from config_manager import ConfigManager

class TestCoreArchitecture(unittest.TestCase):
    def setUp(self):
        self.test_config_path = "test_config_temp.json"
        # Create a mock config file
        self.mock_config = {
            "WAKE_WORD_THRESHOLD": 0.35,
            "FEATURE_FLAGS": {
                "enable_voice": False
            }
        }
        with open(self.test_config_path, 'w') as f:
            json.dump(self.mock_config, f, indent=2)

    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)

    def test_event_bus_pub_sub(self):
        event_bus = EventBus()
        received_data = []

        def callback(event_type, data):
            received_data.append((event_type, data))

        # Subscribe
        event_bus.subscribe("TEST_EVENT", callback)
        
        # Publish
        event_bus.publish("TEST_EVENT", {"message": "Hello World"})
        self.assertEqual(len(received_data), 1)
        self.assertEqual(received_data[0][0], "TEST_EVENT")
        self.assertEqual(received_data[0][1]["message"], "Hello World")

        # Unsubscribe
        event_bus.unsubscribe("TEST_EVENT", callback)
        event_bus.publish("TEST_EVENT", {"message": "Should not see this"})
        self.assertEqual(len(received_data), 1)

    def test_config_manager_loading_and_fallbacks(self):
        manager = ConfigManager(self.test_config_path)
        
        # Test loading from config path
        self.assertEqual(manager.get("WAKE_WORD_THRESHOLD"), 0.35)
        
        # Test fallbacks from static config.py (e.g. DURATION is 4.0 or from config.py)
        # Assuming config.py has static settings like DURATION or SAMPLE_RATE
        import config as static_config
        if hasattr(static_config, "SAMPLE_RATE"):
            self.assertEqual(manager.get("SAMPLE_RATE"), static_config.SAMPLE_RATE)
            
        # Test dynamic updates and saving
        manager.set("TEST_DYNAMIC_KEY", 999)
        self.assertEqual(manager.get("TEST_DYNAMIC_KEY"), 999)
        
        # Verify it got saved to disk
        new_manager = ConfigManager(self.test_config_path)
        self.assertEqual(new_manager.get("TEST_DYNAMIC_KEY"), 999)

if __name__ == "__main__":
    unittest.main()
