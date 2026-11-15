"""
Tests for the Weather action module.
These tests use real network calls to wttr.in.
Run with: pytest tests/test_weather.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from actions.weather import WeatherAction


class TestWeatherAction:

    def setup_method(self):
        self.weather = WeatherAction()

    def test_format_weather_returns_string(self):
        """get_weather should return a non-empty string on success."""
        mock_data = {
            "current_condition": [{
                "weatherDesc": [{"value": "Sunny"}],
                "temp_C": "22", "temp_F": "72",
                "FeelsLikeC": "21", "FeelsLikeF": "70",
                "humidity": "45", "windspeedMiles": "8",
                "winddir16Point": "NW", "visibility": "16", "uvIndex": "5",
            }],
            "weather": [{
                "maxtempC": "25", "mintempC": "15",
                "maxtempF": "77", "mintempF": "59",
                "astronomy": [{"sunrise": "6:00 AM", "sunset": "8:00 PM"}],
                "hourly": [
                    {}, {}, {}, {},
                    {"weatherDesc": [{"value": "Partly Cloudy"}]},
                ],
            }],
        }
        result = self.weather._format_weather(mock_data, "New York")
        assert isinstance(result, str)
        assert "New York" in result
        assert "72" in result  # temp F
        assert "Sunny" in result

    def test_get_weather_offline_returns_empty(self):
        """If network is down, should return empty string gracefully."""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            result = self.weather.get_weather("London")
        assert result == ""

    def test_get_weather_timeout_returns_empty(self):
        """If request times out, should return empty string."""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.Timeout):
            result = self.weather.get_weather("Tokyo")
        assert result == ""

    def test_default_location_used_when_none(self):
        """Should fall back to config.DEFAULT_LOCATION when no location given."""
        import config
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("skip")
            self.weather.get_weather(None)
            call_url = mock_get.call_args[0][0]
            assert config.DEFAULT_LOCATION.replace(" ", "+") in call_url
