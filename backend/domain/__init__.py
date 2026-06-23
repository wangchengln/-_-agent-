"""Domain models for the interactive weekend travel recommendation system."""

from domain.feed import RecommendationFeed, ScoreBreakdown, ScoredPOIItem
from domain.irf_state import (
    IRFSessionState,
    MAX_COMMAND_HISTORY,
    ParserInput,
    ParserOutput,
)
from domain.itinerary import (
    BuildItineraryRequest,
    BuildItineraryResponse,
    ItineraryLeg,
    ItineraryStop,
    WeekendItinerary,
)
from domain.poi import POIItem, parse_amap_poi, parse_amap_pois
from domain.preference import (
    NegativeHardConstraints,
    NegativeSoftPreferences,
    PositiveHardConstraints,
    PositiveSoftPreferences,
    PreferenceProfile,
)
from domain.types import GeoLocation, VenueType

__all__ = [
    "GeoLocation",
    "VenueType",
    "PositiveHardConstraints",
    "PositiveSoftPreferences",
    "NegativeHardConstraints",
    "NegativeSoftPreferences",
    "PreferenceProfile",
    "POIItem",
    "parse_amap_poi",
    "parse_amap_pois",
    "ScoreBreakdown",
    "ScoredPOIItem",
    "RecommendationFeed",
    "BuildItineraryRequest",
    "BuildItineraryResponse",
    "ItineraryLeg",
    "ItineraryStop",
    "WeekendItinerary",
    "IRFSessionState",
    "ParserInput",
    "ParserOutput",
    "MAX_COMMAND_HISTORY",
]
