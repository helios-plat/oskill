"""Tests for oskill.validate_password_strength."""

from __future__ import annotations

from oskill._validate_password_strength import validate_password_strength


class TestValidatePasswordStrength:
    def test_strong_password_passes(self):
        assert validate_password_strength("Abcd123!") is True

    def test_too_short_fails(self):
        assert validate_password_strength("Ab1!") is False

    def test_missing_uppercase_fails(self):
        assert validate_password_strength("abcd123!") is False

    def test_missing_lowercase_fails(self):
        assert validate_password_strength("ABCD123!") is False

    def test_missing_digit_fails(self):
        assert validate_password_strength("Abcdefg!") is False

    def test_missing_special_char_fails(self):
        assert validate_password_strength("Abcd1234") is False

    def test_empty_string_fails(self):
        assert validate_password_strength("") is False
