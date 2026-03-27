import os
import shutil
import unittest
import uuid
from pathlib import Path

from syncdocs_mcp.config import get_config_file, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_load_and_save_config_with_temp_home(self):
        temp_dir = Path("tests/.tmp") / f"config_{uuid.uuid4().hex}"
        old_home = os.environ.get("SYNCDOCS_HOME")
        os.environ["SYNCDOCS_HOME"] = str(temp_dir)
        try:
            config = load_config()
            self.assertTrue(get_config_file().exists())
            config["ollama_chat_model"] = "gemma3:4b"
            saved = save_config(config)
            self.assertEqual(saved["ollama_chat_model"], "gemma3:4b")
            reloaded = load_config()
            self.assertEqual(reloaded["ollama_chat_model"], "gemma3:4b")
        finally:
            if old_home is None:
                os.environ.pop("SYNCDOCS_HOME", None)
            else:
                os.environ["SYNCDOCS_HOME"] = old_home
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
