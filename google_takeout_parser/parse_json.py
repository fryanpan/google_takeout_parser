"""
Lots of functions to transform the JSON from the Takeout to useful information
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator, Any, Dict, Iterable, Optional, List, Union

from .http_allowlist import convert_to_https_opt
from .time_utils import parse_datetime_millis
from .log import logger
from .models import (
    ActivitySegment,
    ActivitySegmentActivity,
    SimplifiedRawPath,
    Subtitles,
    LocationInfo,
    Activity,
    LikedYoutubeVideo,
    ChromeHistory,
    PlayStoreAppInstall,
    Location,
    PlaceVisit,
    CandidateLocation,
    WaypointPath,
)
from .common import Res
from .time_utils import parse_json_utc_date


# "YouTube and YouTube Music/history/search-history.json"
# "YouTube and YouTube Music/history/watch-history.json"
# This is also the 'My Activity' JSON format
def _parse_json_activity(p: Path) -> Iterator[Res[Activity]]:
    json_data = json.loads(p.read_text())
    if not isinstance(json_data, list):
        yield RuntimeError(f"Activity: Top level item in '{p}' isn't a list")
    for blob in json_data:
        try:
            subtitles: List[Subtitles] = []
            for s in blob.get("subtitles", []):
                if not isinstance(s, dict):
                    continue
                # sometimes it's just empty ("My Activity/Assistant" data circa 2018)
                if "name" not in s:
                    continue
                subtitles.append(Subtitles(name=s["name"], url=s.get("url")))

            # till at least 2017
            old_format = "snippet" in blob
            if old_format:
                blob = blob["snippet"]
                header = "YouTube"  # didn't have header
                time_str = blob["publishedAt"]
            else:
                header = blob["header"]
                time_str = blob["time"]

            yield Activity(
                header=header,
                title=blob["title"],
                titleUrl=convert_to_https_opt(blob.get("titleUrl")),
                description=blob.get("description"),
                time=parse_json_utc_date(time_str),
                subtitles=subtitles,
                details=[
                    d["name"]
                    for d in blob.get("details", [])
                    if isinstance(d, dict) and "name" in d
                ],
                locationInfos=[
                    LocationInfo(
                        name=locinfo.get("name"),
                        url=convert_to_https_opt(locinfo.get("url")),
                        source=locinfo.get("source"),
                        sourceUrl=convert_to_https_opt(locinfo.get("sourceUrl")),
                    )
                    for locinfo in blob.get("locationInfos", [])
                ],
                products=blob.get("products", []),
            )
        except Exception as e:
            yield e


def _parse_likes(p: Path) -> Iterator[Res[LikedYoutubeVideo]]:
    json_data = json.loads(p.read_text())
    if not isinstance(json_data, list):
        yield RuntimeError(f"Likes: Top level item in '{p}' isn't a list")
    for jlike in json_data:
        try:
            yield LikedYoutubeVideo(
                title=jlike["snippet"]["title"],
                desc=jlike["snippet"]["description"],
                link="https://youtube.com/watch?v={}".format(
                    jlike["contentDetails"]["videoId"]
                ),
                dt=parse_json_utc_date(jlike["snippet"]["publishedAt"]),
            )
        except Exception as e:
            yield e


def _parse_app_installs(p: Path) -> Iterator[Res[PlayStoreAppInstall]]:
    json_data = json.loads(p.read_text())
    if not isinstance(json_data, list):
        yield RuntimeError(f"App installs: Top level item in '{p}' isn't a list")
    for japp in json_data:
        try:
            yield PlayStoreAppInstall(
                title=japp["install"]["doc"]["title"],
                device_name=japp["install"]["deviceAttribute"].get("deviceDisplayName"),
                dt=parse_json_utc_date(japp["install"]["firstInstallationTime"]),
            )
        except Exception as e:
            yield e


def _parse_timestamp_key(d: Dict[str, Any], key: str) -> datetime:
    if f"{key}Ms" in d:
        return parse_datetime_millis(d[f"{key}Ms"])
    else:
        # else should be the isoformat
        return parse_json_utc_date(d[key])


def _parse_location_history(p: Path) -> Iterator[Res[Location]]:
    ### HMMM, seems that all the locations are right after one another. broken? May just be all the location history that google has on me
    ### see numpy.diff(list(map(lambda yy: y.at, filter(lambda y: isinstance(Location), events()))))
    json_data = json.loads(p.read_text())
    if "locations" not in json_data:
        yield RuntimeError(f"Locations: no 'locations' key in '{p}'")
    for loc in json_data.get("locations", []):
        accuracy = loc.get("accuracy")
        try:
            yield Location(
                lng=float(loc["longitudeE7"]) / 1e7,
                lat=float(loc["latitudeE7"]) / 1e7,
                dt=_parse_timestamp_key(loc, "timestamp"),
                accuracy=None if accuracy is None else float(accuracy),
            )
        except Exception as e:
            yield e


_sem_required_keys = ["location", "duration"]
_sem_required_location_keys = [
    "placeId",  # some fairly recent (as of 2023) places might miss it
    "latitudeE7",
    "longitudeE7",
]


def _check_required_keys(
    d: Dict[str, Any], required_keys: Iterable[str]
) -> Optional[str]:
    for k in required_keys:
        if k not in d:
            return k
    return None


def _parse_semantic_location_history(
    p: Path,
) -> Iterator[Res[Union[PlaceVisit, ActivitySegment]]]:
    json_data = json.loads(p.read_text())
    if not isinstance(json_data, dict):
        yield RuntimeError(f"Locations: Top level item in '{p}' isn't a dict")
    if "timelineObjects" not in json_data:
        yield RuntimeError(f"Locations: no 'timelineObjects' key in '{p}'")
    timelineObjects = json_data.get("timelineObjects", [])
    for timelineObject in timelineObjects:
        try:
            if "placeVisit" in timelineObject:
                result = _parse_place_visit(timelineObject["placeVisit"])
            elif "activitySegment" in timelineObject:
                result = _parse_activity_segment(timelineObject["activitySegment"])
            else:
                yield RuntimeError(
                    f"Unknown timeline object with keys {timelineObject.keys()} in path '{p}'"
                )
            if result is not None:
                yield result
        except Exception as e:
            yield e


def _parse_place_visit(placeVisit: Dict[str, Any]) -> Optional[PlaceVisit]:
    missing_key = _check_required_keys(placeVisit, _sem_required_keys)
    if missing_key is not None:
        raise RuntimeError(f"PlaceVisit: no '{missing_key}' key in '{placeVisit}'")
    try:
        location_json = placeVisit["location"]
        missing_location_key = _check_required_keys(
            location_json, _sem_required_location_keys
        )
        if missing_location_key is not None:
            # Handle these fully defensively, since nothing at all we can do if it's missing these properties
            # If this comes up, quit early and don't try to create a PlaceVisit object
            logger.debug(
                f"CandidateLocation: {placeVisit}, no key '{missing_location_key}' in {location_json}"
            )
            return None
        location = CandidateLocation.from_dict(location_json)
        duration = placeVisit["duration"]
        return PlaceVisit(
            name=location.name,
            address=location.address,
            # separators=(",", ":") removes whitespace from json.dumps
            otherCandidateLocations=[
                CandidateLocation.from_dict(pv)
                for pv in placeVisit.get("otherCandidateLocations", [])
            ],
            sourceInfoDeviceTag=location.sourceInfoDeviceTag,
            placeConfidence=placeVisit.get("placeConfidence"),
            placeVisitImportance=placeVisit.get("placeVisitImportance"),
            placeVisitType=placeVisit.get("placeVisitType"),
            visitConfidence=placeVisit.get("visitConfidence"),
            editConfirmationStatus=placeVisit.get("editConfirmationStatus"),
            placeId=location.placeId,
            lng=location.lng,
            lat=location.lat,
            centerLat=float(placeVisit["centerLatE7"]) / 1e7
            if "centerLatE7" in placeVisit
            else None,
            centerLng=float(placeVisit["centerLngE7"]) / 1e7
            if "centerLngE7" in placeVisit
            else None,
            startTime=_parse_timestamp_key(duration, "startTimestamp"),
            endTime=_parse_timestamp_key(duration, "endTimestamp"),
            locationConfidence=location.locationConfidence,
        )
    except Exception as e:
        if isinstance(e, KeyError):
            raise RuntimeError(
                f"PlaceVisit: {placeVisit}, no key '{e}' in {placeVisit}"
            )
        else:
            raise e


_sem_activity_segment_required_keys = ["duration", "activities"]


def _parse_activity_segment(
    activitySegment: Dict[str, Any]
) -> Optional[ActivitySegment]:
    missing_key = _check_required_keys(
        activitySegment, _sem_activity_segment_required_keys
    )
    if missing_key is not None:
        raise RuntimeError(
            f"ActivitySegment: no '{missing_key}' key in '{activitySegment}'"
        )
    try:
        if activitySegment["startLocation"]:
            start = CandidateLocation.from_dict(activitySegment["startLocation"])
            startLat: Union[float, None] = start.lat
            startLng: Union[float, None] = start.lng
        else:
            startLat = startLng = None

        if activitySegment["endLocation"]:
            end = CandidateLocation.from_dict(activitySegment["endLocation"])
            endLat: Union[float, None] = end.lat
            endLng: Union[float, None] = end.lng
        else:
            endLat = endLng = None

        return ActivitySegment(
            startLat=startLat,
            startLng=startLng,
            endLat=endLat,
            endLng=endLng,
            startTime=parse_json_utc_date(
                activitySegment["duration"]["startTimestamp"]
            ),
            endTime=parse_json_utc_date(activitySegment["duration"]["endTimestamp"]),
            distance=activitySegment.get("distance"),
            activityType=activitySegment.get("activityType"),
            confidence=activitySegment.get("confidence"),
            activities=[
                ActivitySegmentActivity.from_dict(a)
                for a in activitySegment.get("activities", [])
            ],
            waypointPath=WaypointPath.from_dict(activitySegment["waypointPath"])
            if "waypointPath" in activitySegment
            else None,
            simplifiedRawPath=SimplifiedRawPath.from_list(
                activitySegment.get("simplifiedRawPath", {}).get("points", [])
            ),
            editConfirmationStatus=activitySegment.get("editConfirmationStatus"),
        )
    except Exception as e:
        if isinstance(e, KeyError):
            raise RuntimeError(
                f"ActivitySegment: {activitySegment}, no key '{e}' in {activitySegment}"
            )
        else:
            raise e


def _parse_chrome_history(p: Path) -> Iterator[Res[ChromeHistory]]:
    json_data = json.loads(p.read_text())
    if "Browser History" not in json_data:
        yield RuntimeError(f"Chrome/BrowserHistory: no 'Browser History' key in '{p}'")
    for item in json_data.get("Browser History", []):
        try:
            time_naive = datetime.utcfromtimestamp(item["time_usec"] / 10**6)
            yield ChromeHistory(
                title=item["title"],
                # dont convert to https here, this is just the users history
                # and there's likely lots of items that aren't https
                url=item["url"],
                dt=time_naive.replace(tzinfo=timezone.utc),
            )
        except Exception as e:
            yield e
