"""
JARVIS Weather Action
=====================
Fetches weather using wttr.in — completely FREE, no API key needed.

wttr.in is a weather service that supports JSON output.
URL format: https://wttr.in/{location}?format=j1

Usage:
    weather = WeatherAction()
    data = weather.get_weather("London")
    summary = weather.get_short_summary("NYC")
"""

import requests
from utils.logger import get_logger
import config

log = get_logger("weather")


class WeatherAction:
    """Free weather data via wttr.in."""

    BASE_URL = "https://wttr.in/{location}?format=j1"

    def get_weather(self, location: str = None) -> str:
        """
        Get weather data as a formatted string for LLM context injection.
        Returns empty string on failure.
        """
        loc = location or config.DEFAULT_LOCATION
        loc_clean = loc.strip().replace(" ", "+")

        try:
            url = self.BASE_URL.format(location=loc_clean)
            resp = requests.get(url, timeout=config.WEATHER_TIMEOUT, headers={
                "User-Agent": "JARVIS-Assistant/1.0"
            })
            resp.raise_for_status()
            data = resp.json()

            return self._format_weather(data, loc)

        except requests.exceptions.ConnectionError:
            log.warning("No internet connection for weather")
            return ""
        except requests.exceptions.Timeout:
            log.warning("Weather request timed out")
            return ""
        except Exception as e:
            log.error(f"Weather error: {e}")
            return ""

    def _format_weather(self, data: dict, location: str) -> str:
        """Parse wttr.in JSON and format as a readable string."""
        try:
            current = data["current_condition"][0]
            weather_desc = current["weatherDesc"][0]["value"]
            temp_c = current["temp_C"]
            temp_f = current["temp_F"]
            feels_c = current["FeelsLikeC"]
            feels_f = current["FeelsLikeF"]
            humidity = current["humidity"]
            wind_mph = current["windspeedMiles"]
            wind_dir = current["winddir16Point"]
            visibility = current["visibility"]
            uv = current.get("uvIndex", "N/A")

            # Today's forecast
            today = data["weather"][0]
            max_c = today["maxtempC"]
            min_c = today["mintempC"]
            max_f = today["maxtempF"]
            min_f = today["mintempF"]

            # Astronomy
            sunrise = today.get("astronomy", [{}])[0].get("sunrise", "N/A")
            sunset = today.get("astronomy", [{}])[0].get("sunset", "N/A")

            summary = (
                f"Location: {location}\n"
                f"Condition: {weather_desc}\n"
                f"Temperature: {temp_f}°F ({temp_c}°C)\n"
                f"Feels Like: {feels_f}°F ({feels_c}°C)\n"
                f"Today's Range: {min_f}°F to {max_f}°F ({min_c}°C to {max_c}°C)\n"
                f"Humidity: {humidity}%\n"
                f"Wind: {wind_mph} mph {wind_dir}\n"
                f"Visibility: {visibility} km\n"
                f"UV Index: {uv}\n"
                f"Sunrise: {sunrise} | Sunset: {sunset}"
            )

            # Add 3-day forecast
            forecast_lines = []
            for i, day in enumerate(data.get("weather", [])[:3]):
                day_desc = day["hourly"][4]["weatherDesc"][0]["value"]
                forecast_lines.append(
                    f"  Day {i+1}: {day_desc}, "
                    f"{day['mintempF']}°F–{day['maxtempF']}°F"
                )

            if forecast_lines:
                summary += "\n\n3-Day Forecast:\n" + "\n".join(forecast_lines)

            return summary

        except (KeyError, IndexError) as e:
            log.warning(f"Weather parse error: {e}")
            # Return raw data truncated
            import json
            return json.dumps(data, indent=2)[:1000]

    def get_short_summary(self, location: str = None) -> str:
        """Returns a one-line weather summary."""
        loc = location or config.DEFAULT_LOCATION
        try:
            url = f"https://wttr.in/{loc.replace(' ', '+')}?format=3"
            resp = requests.get(url, timeout=config.WEATHER_TIMEOUT, headers={
                "User-Agent": "JARVIS-Assistant/1.0"
            })
            return resp.text.strip()
        except Exception:
            return ""
