import unittest
from unittest.mock import patch, mock_open
import os
import shutil
import tempfile
from loguru import logger # To check for log messages

# Assuming prompts.prompt_loader is the path to your module
# Need to adjust sys.path if tests are run from a different directory
# or if the project structure requires it. For now, direct import.
from prompts import prompt_loader

# Disable logger for tests to keep output clean, or configure for test-specific output
logger.remove() 
logger.add(lambda _: None) # No-op sink

class TestPromptLoader(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for prompts
        self.test_dir = tempfile.mkdtemp()
        self.persona_dir = os.path.join(self.test_dir, "persona")
        self.util_dir = os.path.join(self.test_dir, "utils")
        os.makedirs(self.persona_dir)
        os.makedirs(self.util_dir)

        # Patch the directory constants in prompt_loader to use our temp directory
        self.persona_dir_patch = patch.object(prompt_loader, 'PERSONA_PROMPT_DIR', self.persona_dir)
        self.util_dir_patch = patch.object(prompt_loader, 'UTIL_PROMPT_DIR', self.util_dir)
        
        self.persona_dir_patch.start()
        self.util_dir_patch.start()

    def tearDown(self):
        # Stop the patches
        self.persona_dir_patch.stop()
        self.util_dir_patch.stop()
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)

    def test_load_persona_successful_md(self):
        persona_name = "test_persona.md"
        persona_content = "# Test Persona MD\nThis is a test."
        with open(os.path.join(self.persona_dir, persona_name), "w", encoding="utf-8") as f:
            f.write(persona_content)

        loaded_content = prompt_loader.load_persona(persona_name)
        self.assertEqual(loaded_content, persona_content)

    def test_load_persona_successful_txt(self):
        # Test if it can still load .txt files if specified
        persona_name = "legacy_persona.txt"
        persona_content = "Legacy Persona TXT\nThis is a legacy test."
        with open(os.path.join(self.persona_dir, persona_name), "w", encoding="utf-8") as f:
            f.write(persona_content)

        loaded_content = prompt_loader.load_persona(persona_name)
        self.assertEqual(loaded_content, persona_content)

    def test_load_persona_path_construction(self):
        # This test indirectly verifies path construction by checking if the correct file is loaded.
        persona_name = "specific_path.md"
        expected_path = os.path.join(self.persona_dir, persona_name)
        persona_content = "Content for path construction test."
        
        with open(expected_path, "w", encoding="utf-8") as f:
            f.write(persona_content)

        # We mock _load_file_content to assert the path it's called with
        with patch.object(prompt_loader, '_load_file_content', return_value=persona_content) as mock_load_file:
            prompt_loader.load_persona(persona_name)
            mock_load_file.assert_called_once_with(expected_path)


    @patch.object(logger, 'error') # Mock logger.error
    @patch.object(logger, 'warning') # Mock logger.warning
    def test_load_persona_file_not_found_fallback(self, mock_logger_warning, mock_logger_error):
        persona_name = "non_existent_persona.md"
        
        # The fallback content as defined in prompt_loader.py
        expected_fallback_content = """# Fallback Persona

You are a generic AI assistant. The configured persona file was not found."""

        loaded_content = prompt_loader.load_persona(persona_name)
        
        self.assertEqual(loaded_content, expected_fallback_content)
        mock_logger_error.assert_called_once()
        self.assertIn(f"Persona file not found: {os.path.join(self.persona_dir, persona_name)}", mock_logger_error.call_args[0][0])
        mock_logger_warning.assert_called_once_with("Falling back to default persona content.")

    def test_load_util_successful(self):
        util_name = "test_util.txt" # Assuming utils are still .txt based on original structure
        util_content = "Utility prompt content."
        with open(os.path.join(self.util_dir, util_name), "w", encoding="utf-8") as f:
            f.write(util_content)
        
        loaded_content = prompt_loader.load_util(util_name)
        self.assertEqual(loaded_content, util_content)

    @patch.object(logger, 'error') # Mock logger.error
    def test_load_util_file_not_found(self, mock_logger_error):
        util_name = "non_existent_util.txt"
        
        with self.assertRaises(FileNotFoundError): # Expecting it to re-raise
            prompt_loader.load_util(util_name)
        
        mock_logger_error.assert_called_once()
        self.assertIn(f"Error loading util {util_name}", mock_logger_error.call_args[0][0])


    # Test _load_file_content directly for encoding issues if necessary
    @patch('builtins.open', new_callable=mock_open, read_data="你好世界".encode('gbk'))
    @patch.object(prompt_loader.chardet, 'detect', return_value={'encoding': 'gbk', 'confidence': 1.0})
    def test_load_file_content_gbk_encoding(self, mock_chardet_detect, mock_file_open):
        # This test is more for the _load_file_content helper, but it's crucial for load_persona
        # We need to ensure that the file path passed to open is correct
        dummy_filepath = os.path.join(self.persona_dir, "dummy_gbk.txt")
        
        # We're mocking 'open' at the builtins level.
        # prompt_loader._load_file_content will call open(dummy_filepath, ...)
        # The mock_open we defined will intercept this call.
        
        content = prompt_loader._load_file_content(dummy_filepath)
        self.assertEqual(content, "你好世界")
        # Ensure open was called with 'rb' when chardet is used after initial failures
        # This is tricky because open is called multiple times.
        # For simplicity, we assume if content is correct, encoding worked.
        # A more robust test would inspect mock_file_open.call_args_list


    @patch('builtins.open', new_callable=mock_open, read_data="Hello".encode('utf-8-sig'))
    @patch.object(prompt_loader.chardet, 'detect') # Keep chardet from being called if utf-8-sig works
    def test_load_file_content_utf8_sig_encoding(self, mock_chardet_detect, mock_file_open):
        dummy_filepath = os.path.join(self.persona_dir, "dummy_utf8sig.txt")
        content = prompt_loader._load_file_content(dummy_filepath)
        self.assertEqual(content, "Hello")
        mock_chardet_detect.assert_not_called() # UTF-8-SIG should be tried before chardet

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
