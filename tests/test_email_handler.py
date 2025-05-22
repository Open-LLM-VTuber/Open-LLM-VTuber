import unittest
from unittest.mock import patch, mock_open, MagicMock
import smtplib
import yaml # Should be PyYAML if that's what the main code uses

# Assuming utils.email_handler is the path to your module
from utils.email_handler import send_email, load_smtp_config, CONFIG_FILE_PATH

# Default config for testing
DEFAULT_SMTP_CONFIG = {
    "SMTP": {
        "HOST": "smtp.test.com",
        "PORT": 587,
        "USE_TLS": True,
        "USE_SSL": False,
        "USERNAME": "testuser@example.com",
        "PASSWORD": "testpassword",
        "SENDER_EMAIL": "sender@example.com"
    }
}

class TestEmailHandler(unittest.TestCase):

    def _mock_config_load(self, mock_yaml_load, smtp_config_data):
        mock_yaml_load.return_value = smtp_config_data

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP')
    def test_send_email_successful_tls(self, mock_smtp_class, mock_yaml_load, mock_file_open):
        self._mock_config_load(mock_yaml_load, DEFAULT_SMTP_CONFIG)
        
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value = mock_smtp_instance

        result = send_email("recipient@example.com", "Test Subject TLS", "Test Body TLS")

        self.assertTrue(result)
        mock_smtp_class.assert_called_once_with(DEFAULT_SMTP_CONFIG["SMTP"]["HOST"], DEFAULT_SMTP_CONFIG["SMTP"]["PORT"])
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with(DEFAULT_SMTP_CONFIG["SMTP"]["USERNAME"], DEFAULT_SMTP_CONFIG["SMTP"]["PASSWORD"])
        mock_smtp_instance.sendmail.assert_called_once()
        self.assertEqual(mock_smtp_instance.sendmail.call_args[0][0], DEFAULT_SMTP_CONFIG["SMTP"]["SENDER_EMAIL"])
        self.assertEqual(mock_smtp_instance.sendmail.call_args[0][1], "recipient@example.com")
        mock_smtp_instance.quit.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP_SSL') # Mock SMTP_SSL for this test
    def test_send_email_successful_ssl(self, mock_smtp_ssl_class, mock_yaml_load, mock_file_open):
        ssl_config = {
            "SMTP": {
                **DEFAULT_SMTP_CONFIG["SMTP"],
                "USE_TLS": False,
                "USE_SSL": True,
                "PORT": 465 # Typical SSL port
            }
        }
        self._mock_config_load(mock_yaml_load, ssl_config)

        mock_smtp_instance = MagicMock()
        mock_smtp_ssl_class.return_value = mock_smtp_instance

        result = send_email("recipient@example.com", "Test Subject SSL", "Test Body SSL")

        self.assertTrue(result)
        mock_smtp_ssl_class.assert_called_once_with(ssl_config["SMTP"]["HOST"], ssl_config["SMTP"]["PORT"])
        mock_smtp_instance.starttls.assert_not_called() # TLS should not be called for SSL
        mock_smtp_instance.login.assert_called_once_with(ssl_config["SMTP"]["USERNAME"], ssl_config["SMTP"]["PASSWORD"])
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP')
    def test_send_email_no_auth(self, mock_smtp_class, mock_yaml_load, mock_file_open):
        no_auth_config = {
            "SMTP": {
                "HOST": "localhost",
                "PORT": 25, # Typical local relay port
                "USE_TLS": False,
                "USE_SSL": False,
                "USERNAME": None, # No username
                "PASSWORD": None, # No password
                "SENDER_EMAIL": "sender@example.com"
            }
        }
        self._mock_config_load(mock_yaml_load, no_auth_config)
        
        mock_smtp_instance = MagicMock()
        mock_smtp_class.return_value = mock_smtp_instance

        result = send_email("recipient@example.com", "Test Subject No Auth", "Test Body No Auth")

        self.assertTrue(result)
        mock_smtp_class.assert_called_once_with(no_auth_config["SMTP"]["HOST"], no_auth_config["SMTP"]["PORT"])
        mock_smtp_instance.login.assert_not_called() # Login should not be called
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP', side_effect=smtplib.SMTPConnectError("Connection refused"))
    def test_send_email_connection_error(self, mock_smtp_class, mock_yaml_load, mock_file_open):
        self._mock_config_load(mock_yaml_load, DEFAULT_SMTP_CONFIG)
        result = send_email("recipient@example.com", "Test Subject", "Test Body")
        self.assertFalse(result)
        mock_smtp_class.assert_called_once() # Check that SMTP was attempted

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP')
    def test_send_email_authentication_error(self, mock_smtp_class, mock_yaml_load, mock_file_open):
        self._mock_config_load(mock_yaml_load, DEFAULT_SMTP_CONFIG)
        
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication credentials invalid")
        mock_smtp_class.return_value = mock_smtp_instance

        result = send_email("recipient@example.com", "Test Subject", "Test Body")
        self.assertFalse(result)
        mock_smtp_instance.login.assert_called_once()
        mock_smtp_instance.quit.assert_called_once() # Quit should still be called

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP')
    def test_send_email_sendmail_error(self, mock_smtp_class, mock_yaml_load, mock_file_open):
        self._mock_config_load(mock_yaml_load, DEFAULT_SMTP_CONFIG)
        
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.sendmail.side_effect = smtplib.SMTPSenderRefused(550, "Sender refused", "sender@example.com")
        mock_smtp_class.return_value = mock_smtp_instance

        result = send_email("recipient@example.com", "Test Subject", "Test Body")
        self.assertFalse(result)
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    def test_load_smtp_config_success(self, mock_yaml_load, mock_file_open):
        self._mock_config_load(mock_yaml_load, DEFAULT_SMTP_CONFIG)
        config = load_smtp_config()
        self.assertEqual(config, DEFAULT_SMTP_CONFIG["SMTP"])
        mock_file_open.assert_called_once_with(CONFIG_FILE_PATH, 'r')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_smtp_config_file_not_found(self, mock_file_open):
        config = load_smtp_config()
        self.assertIsNone(config)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load', side_effect=yaml.YAMLError("YAML parsing error"))
    def test_load_smtp_config_yaml_error(self, mock_yaml_load, mock_file_open):
        config = load_smtp_config()
        self.assertIsNone(config)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load', return_value={"OTHER_CONFIG": "value"}) # No SMTP key
    def test_load_smtp_config_no_smtp_key(self, mock_yaml_load, mock_file_open):
        config = load_smtp_config()
        self.assertIsNone(config)
        
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('smtplib.SMTP')
    def test_send_email_missing_host_in_config(self, mock_smtp_class, mock_yaml_load, mock_file_open):
        bad_config = {
            "SMTP": {
                # "HOST": "smtp.test.com", # HOST is missing
                "PORT": 587,
                "USE_TLS": True,
                "USERNAME": "testuser@example.com",
                "PASSWORD": "testpassword",
                "SENDER_EMAIL": "sender@example.com"
            }
        }
        self._mock_config_load(mock_yaml_load, bad_config)
        result = send_email("recipient@example.com", "Test Subject", "Test Body")
        self.assertFalse(result)
        mock_smtp_class.assert_not_called() # Should not even attempt to connect

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
