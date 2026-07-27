"""
Quick manual check that the Google Maps API key works.
Run: python test_travel_time.py
"""

from travel_time import get_travel_time_minutes

if __name__ == "__main__":
    minutes = get_travel_time_minutes("DA2 7HG", "ME3 7BD")
    print(f"Travel time DA2 7HG -> ME3 7BD: {minutes} minutes")