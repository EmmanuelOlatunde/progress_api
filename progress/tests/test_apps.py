from django.test import SimpleTestCase
from django.apps import apps
from progress.apps import ProgressConfig

class ProgressAppConfigTests(SimpleTestCase):
    def test_app_config_name(self):
        """ProgressConfig name should match the app label"""
        self.assertEqual(ProgressConfig.name, "progress")
    
    def test_ready_method_imports_signals(self):
        """Calling ready() should import signals without error"""
        config = apps.get_app_config("progress")
        try:
            config.ready()  # Should import signals
        except Exception as e:
            self.fail(f"ProgressConfig.ready() raised an exception: {e}")
