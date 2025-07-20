from django.test import TestCase
from django.apps import apps
from users.apps import UsersConfig

class UsersConfigTests(TestCase):
    def test_users_config_name(self):
        """Test that the UsersConfig name is correct"""
        config = apps.get_app_config('users')
        self.assertEqual(config.name, 'users')
        self.assertIsInstance(config, UsersConfig)

    def test_users_config_default_auto_field(self):
        """Test that the default_auto_field is set correctly"""
        config = apps.get_app_config('users')
        self.assertEqual(config.default_auto_field, 'django.db.models.BigAutoField')



    def test_users_config_ready_method(self):
        """Test that ready method imports signals correctly"""
        # Use the actual app config from the apps registry
        config = apps.get_app_config('users')
        try:
            config.ready()
            # If we reach here without ImportError, signals were imported successfully
            self.assertTrue(True)
        except ImportError:
            self.fail("UsersConfig.ready() failed to import signals")

   

  
    def test_users_config_module(self):
        """Test that the app config is properly registered"""
        self.assertTrue(apps.is_installed('users'))
        config = apps.get_app_config('users')
        self.assertEqual(config.__class__.__module__, 'users.apps')