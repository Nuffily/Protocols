import pytest
import os
from ssl_smtp_client import MySMTP


# Фикстура для создания временных файлов для тестов
class TestMySMPT:
    @pytest.fixture
    def temp_message_file(self, tmp_path):
        def _creator(content, filename="test_message.txt"):
            file_path = tmp_path / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return str(file_path)
        return _creator
    
    @pytest.fixture
    def smtp(self):
        return MySMTP("login.txt")

    
    def test_get_message_simple_text(self, smtp, temp_message_file):
        content = "Hello, world!\nThis is a test message."
        file_path = temp_message_file(content)
        expected_output = content
        assert smtp.get_message(file_path) == expected_output
    
    def test_get_message_with_dot_line(self, smtp, temp_message_file):
        content = "Line 1\n.\nLine 3"
        expected_output = "Line 1\n..\nLine 3"
        file_path = temp_message_file(content)
        assert smtp.get_message(file_path) == expected_output
    
    def test_get_message_with_dot_line_crlf(self, smtp, temp_message_file):
        content = "First line.\n.\nLast line."
        expected_output = "First line.\n..\nLast line."
        file_path = temp_message_file(content)
        assert smtp.get_message(file_path) == expected_output
    
    def test_get_message_with_multiple_dot_lines(self, smtp, temp_message_file):
        content = "Start\n.\nMiddle\n.\nEnd"
        expected_output = "Start\n..\nMiddle\n..\nEnd"
        file_path = temp_message_file(content)
        assert smtp.get_message(file_path) == expected_output
    
    def test_get_message_dot_not_alone(self, smtp, temp_message_file):
        content = "Line with . inside\n.not_alone\nJust a dot."
        expected_output = "Line with . inside\n.not_alone\nJust a dot."
        file_path = temp_message_file(content)
        assert smtp.get_message(file_path) == expected_output
    
    def test_get_message_empty_file(self, smtp, temp_message_file):
        content = ""
        file_path = temp_message_file(content)
        expected_output = ""
        assert smtp.get_message(file_path) == expected_output
    
    def test_get_message_only_dot_line(self, smtp, temp_message_file):
        content = "."
        expected_output = ".."
        file_path = temp_message_file(content)
        assert smtp.get_message(file_path) == expected_output