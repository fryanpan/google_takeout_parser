import json
import datetime
from pathlib import Path
from typing import Iterator, Any

import pytest
import google_takeout_parser.parse_json as prj
from google_takeout_parser import models


@pytest.fixture(scope="function")
def tmp_path_f(
    request: Any, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[Path]:
    """
    Create a new tempdir every time this runs
    """
    # request is a _pytest.fixture.SubRequest, function that called this
    assert isinstance(request.function.__name__, str), str(request)
    assert request.function.__name__.strip(), str(request)
    tmp_dir = tmp_path_factory.mktemp(request.function.__name__, numbered=True)
    yield tmp_dir


def test_parse_activity_json(tmp_path_f: Path) -> None:
    contents = '[{"header": "Discover", "title": "7 cards in your feed", "time": "2021-12-13T03:04:05.007Z", "products": ["Discover"], "locationInfos": [{"name": "At this general area", "url": "https://www.google.com/maps/@?api=1&map_action=map&center=lat,lon&zoom=12", "source": "From your Location History", "sourceUrl": "https://www.google.com/maps/timeline"}], "subtitles": [{"name": "Computer programming"}, {"name": "Computer Science"}, {"name": "PostgreSQL"}, {"name": "Technology"}]}]'
    fp = tmp_path_f / "file"
    fp.write_text(contents)
    res = list(prj._parse_json_activity(fp))
    assert res[0] == models.Activity(
        header="Discover",
        title="7 cards in your feed",
        time=datetime.datetime(
            2021, 12, 13, 3, 4, 5, 7000, tzinfo=datetime.timezone.utc
        ),
        description=None,
        titleUrl=None,
        subtitles=[
            models.Subtitles("Computer programming", None),
            models.Subtitles("Computer Science", None),
            models.Subtitles("PostgreSQL", None),
            models.Subtitles("Technology", None),
        ],
        locationInfos=[
            models.LocationInfo(
                "At this general area",
                "https://www.google.com/maps/@?api=1&map_action=map&center=lat,lon&zoom=12",
                "From your Location History",
                "https://www.google.com/maps/timeline",
            ),
        ],
        details=[],
        products=["Discover"],
    )


def test_parse_likes_json(tmp_path_f: Path) -> None:
    contents = """[{"contentDetails": {"videoId": "J1tF-DKKt7k", "videoPublishedAt": "2015-10-05T17:23:15.000Z"}, "etag": "GbLczUV2gsP6j0YQgTcYropUbdY", "id": "TExBNkR0bmJaMktKY2t5VFlmWE93UU5BLkoxdEYtREtLdDdr", "kind": "youtube#playlistItem", "snippet": {"channelId": "UCA6DtnbZ2KJckyTYfXOwQNA", "channelTitle": "Sean B", "description": "\\u30b7\\u30e5\\u30ac\\u30fc\\u30bd\\u30f3\\u30b0\\u3068\\u30d3\\u30bf\\u30fc\\u30b9\\u30c6\\u30c3\\u30d7 \\nSugar Song and Bitter Step\\n\\u7cd6\\u6b4c\\u548c\\u82e6\\u5473\\u6b65\\u9a5f\\nUNISON SQUARE GARDEN\\n\\u7530\\u6df5\\u667a\\u4e5f\\n\\u8840\\u754c\\u6226\\u7dda\\n\\u5e7b\\u754c\\u6230\\u7dda\\nBlood Blockade Battlefront ED\\nArranged by Maybe\\nScore:https://drive.google.com/open?id=0B9Jb1ks6rtrWSk1hX1U0MXlDSUE\\nThx~~", "playlistId": "LLA6DtnbZ2KJckyTYfXOwQNA", "position": 4, "publishedAt": "2020-07-05T18:27:32.000Z", "resourceId": {"kind": "youtube#video", "videoId": "J1tF-DKKt7k"}, "thumbnails": {"default": {"height": 90, "url": "https://i.ytimg.com/vi/J1tF-DKKt7k/default.jpg", "width": 120}, "high": {"height": 360, "url": "https://i.ytimg.com/vi/J1tF-DKKt7k/hqdefault.jpg", "width": 480}, "medium": {"height": 180, "url": "https://i.ytimg.com/vi/J1tF-DKKt7k/mqdefault.jpg", "width": 320}, "standard": {"height": 480, "url": "https://i.ytimg.com/vi/J1tF-DKKt7k/sddefault.jpg", "width": 640}}, "title": "[Maybe]Blood Blockade Battlefront ED \\u30b7\\u30e5\\u30ac\\u30fc\\u30bd\\u30f3\\u30b0\\u3068\\u30d3\\u30bf\\u30fc\\u30b9\\u30c6\\u30c3\\u30d7 Sugar Song and Bitter Step"}, "status": {"privacyStatus": "public"}}]"""
    fp = tmp_path_f / "file"
    fp.write_text(contents)
    res = list(prj._parse_likes(fp))
    assert res == [
        models.LikedYoutubeVideo(
            title="[Maybe]Blood Blockade Battlefront ED シュガーソングとビターステップ "
            "Sugar Song and Bitter Step",
            desc="シュガーソングとビターステップ \n"
            "Sugar Song and Bitter Step\n"
            "糖歌和苦味步驟\n"
            "UNISON SQUARE GARDEN\n"
            "田淵智也\n"
            "血界戦線\n"
            "幻界戰線\n"
            "Blood Blockade Battlefront ED\n"
            "Arranged by Maybe\n"
            "Score:https://drive.google.com/open?id=0B9Jb1ks6rtrWSk1hX1U0MXlDSUE\n"
            "Thx~~",
            link="https://youtube.com/watch?v=J1tF-DKKt7k",
            dt=datetime.datetime(2020, 7, 5, 18, 27, 32, tzinfo=datetime.timezone.utc),
        )
    ]


def test_parse_app_installs(tmp_path_f: Path) -> None:
    contents = """[{"install": {"doc": {"documentType": "Android Apps", "title": "Discord - Talk, Video Chat & Hang Out with Friends"}, "firstInstallationTime": "2020-05-25T03:11:53.055Z", "deviceAttribute": {"manufacturer": "motorola", "deviceDisplayName": "motorola moto g(7) play"}, "lastUpdateTime": "2020-08-27T02:55:33.259Z"}}]"""

    fp = tmp_path_f / "file"
    fp.write_text(contents)
    res = list(prj._parse_app_installs(fp))
    assert res == [
        models.PlayStoreAppInstall(
            title="Discord - Talk, Video Chat & Hang Out with Friends",
            dt=datetime.datetime(
                2020, 5, 25, 3, 11, 53, 55000, tzinfo=datetime.timezone.utc
            ),
            device_name="motorola moto g(7) play",
        )
    ]


def test_location_old(tmp_path_f: Path) -> None:
    contents = '{"locations": [{"timestampMs": "1512947698030", "latitudeE7": 351324213, "longitudeE7": -1122434441, "accuracy": 10}]}'
    fp = tmp_path_f / "file"
    fp.write_text(contents)
    res = list(prj._parse_location_history(fp))
    assert res == [
        models.Location(
            lng=-112.2434441,
            lat=35.1324213,
            dt=datetime.datetime(
                2017, 12, 10, 23, 14, 58, tzinfo=datetime.timezone.utc
            ),
            accuracy=10.0,
        ),
    ]


def test_location_new(tmp_path_f: Path) -> None:
    contents = '{"locations": [{"latitudeE7": 351324213, "longitudeE7": -1122434441, "accuracy": 10, "deviceTag": -80241446968629135069, "deviceDesignation": "PRIMARY", "timestamp": "2017-12-10T23:14:58.030Z"}]}'
    fp = tmp_path_f / "file"
    fp.write_text(contents)
    res = list(prj._parse_location_history(fp))
    assert res == [
        models.Location(
            lng=-112.2434441,
            lat=35.1324213,
            dt=datetime.datetime(
                2017, 12, 10, 23, 14, 58, 30000, tzinfo=datetime.timezone.utc
            ),
            accuracy=10.0,
        ),
    ]


def test_chrome_history(tmp_path_f: Path) -> None:
    contents = '{"Browser History": [{"page_transition": "LINK", "title": "sean", "url": "https://sean.fish", "client_id": "W1vSb98l403jhPeK==", "time_usec": 1617404690134513}]}'
    fp = tmp_path_f / "file"
    fp.write_text(contents)
    res = list(prj._parse_chrome_history(fp))
    assert res == [
        models.ChromeHistory(
            title="sean",
            url="https://sean.fish",
            dt=datetime.datetime(
                2021, 4, 2, 23, 4, 50, 134513, tzinfo=datetime.timezone.utc
            ),
        ),
    ]


_TEST_PLACE_VISIT = {
    "placeVisit": {
        "location": {
            "latitudeE7": 555555555,
            "longitudeE7": -1066666666,
            "placeId": "JK4E4P",
            "address": "address",
            "name": "name",
            "sourceInfo": {"deviceTag": 987654321},
            "locationConfidence": 60.45,
        },
        "duration": {
            "startTimestamp": "2017-12-10T23:29:25.026Z",
            "endTimestamp": "2017-12-11T01:20:06.106Z",
        },
        "placeConfidence": "MEDIUM_CONFIDENCE",
        "centerLatE7": 555555555,
        "centerLngE7": -1666666666,
        "visitConfidence": 65.45,
        "otherCandidateLocations": [
            {
                "latitudeE7": 423984239,
                "longitudeE7": -1565656565,
                "placeId": "XPRK4E4P",
                "address": "address2",
                "name": "name2",
                "locationConfidence": 24.475897,
            }
        ],
        "editConfirmationStatus": "NOT_CONFIRMED",
        "locationConfidence": 55,
        "placeVisitType": "SINGLE_PLACE",
        "placeVisitImportance": "MAIN",
    }
}

# Sample activity segment based on data from 2012 (missing most fields)
_TEST_ACTIVITY_SEGMENT_BASIC = {
    "activitySegment": {
        "startLocation": {},
        "endLocation": {},
        "duration": {
            "startTimestamp": "2012-12-06T04:09:31.087Z",
            "endTimestamp": "2012-12-06T04:19:21.052Z",
        },
        "distance": 735,
        "confidence": "LOW",
        "activities": [
            {"activityType": "WALKING", "probability": 0.0},
            {"activityType": "CYCLING", "probability": 0.0},
            {"activityType": "IN_VEHICLE", "probability": 0.0},
        ],
        "simplifiedRawPath": {
            "points": [
                {
                    "latE7": -450339851,
                    "lngE7": 1686552734,
                    "accuracyMeters": 5,
                    "timestamp": "2012-12-06T04:12:29.104Z",
                }
            ]
        },
        "editConfirmationStatus": "NOT_CONFIRMED",
    }
}

# Sample activity from 2016
_TEST_ACTIVITY_PARTIAL_WAYPOINT_PATH = {
    "activitySegment": {
        "startLocation": {"latitudeE7": 377624484, "longitudeE7": -1223967085},
        "endLocation": {"latitudeE7": 377944635, "longitudeE7": -1224026022},
        "duration": {
            "startTimestamp": "2016-12-24T00:11:20.573Z",
            "endTimestamp": "2016-12-24T00:32:23.034Z",
        },
        "distance": 4393,
        "activityType": "IN_PASSENGER_VEHICLE",
        "confidence": "LOW",
        "activities": [
            {"activityType": "IN_PASSENGER_VEHICLE", "probability": 42.59993179064075},
            {"activityType": "CYCLING", "probability": 31.740499796503187},
            {"activityType": "IN_BUS", "probability": 18.35780278904862},
        ],
        "waypointPath": {
            "waypoints": [
                {"latE7": 377624588, "lngE7": -1223965377},
                {"latE7": 377720146, "lngE7": -1223895111},
                {"latE7": 377943038, "lngE7": -1224025726},
            ],
            "source": "INFERRED",
        },
        "simplifiedRawPath": {
            "points": [
                {
                    "latE7": 377721165,
                    "lngE7": -1223895764,
                    "accuracyMeters": 10,
                    "timestamp": "2016-12-24T00:16:18.999Z",
                }
            ]
        },
        "editConfirmationStatus": "NOT_CONFIRMED",
    }
}

# Sample activity segment based on data from 2023 with more complete data
_TEST_ACTIVITY_SEGMENT_FULL = {
    "activitySegment": {
        "startLocation": {
            "latitudeE7": 377605210,
            "longitudeE7": -1224310834,
            "sourceInfo": {"deviceTag": -1935307820},
        },
        "endLocation": {
            "latitudeE7": 377605242,
            "longitudeE7": -1224310477,
            "sourceInfo": {"deviceTag": -1935307820},
        },
        "duration": {
            "startTimestamp": "2023-12-01T01:50:29Z",
            "endTimestamp": "2023-12-01T02:03:13.834Z",
        },
        "distance": 642,
        "activityType": "WALKING",
        "confidence": "HIGH",
        "activities": [
            {"activityType": "WALKING", "probability": 84.14630889892578},
            {"activityType": "STILL", "probability": 11.461445689201355},
            {"activityType": "CYCLING", "probability": 2.6100903749465942},
            {"activityType": "RUNNING", "probability": 0.8146878331899643},
            {"activityType": "IN_PASSENGER_VEHICLE", "probability": 0.791911780834198},
            {"activityType": "SKIING", "probability": 0.038399442564696074},
            {"activityType": "IN_BUS", "probability": 0.035894475877285004},
            {"activityType": "MOTORCYCLING", "probability": 0.03407726180739701},
            {"activityType": "IN_FERRY", "probability": 0.02370273577980697},
            {"activityType": "IN_SUBWAY", "probability": 0.01822529739001766},
            {"activityType": "IN_TRAIN", "probability": 0.015967445506248623},
            {"activityType": "SAILING", "probability": 0.004841846021008678},
            {"activityType": "IN_TRAM", "probability": 0.004207661550026387},
            {"activityType": "FLYING", "probability": 2.4401106202276424e-4},
            {"activityType": "IN_VEHICLE", "probability": 5.013597093039834e-7},
        ],
        "waypointPath": {
            "waypoints": [
                {"latE7": 377604026, "lngE7": -1224310760},
                {"latE7": 377607688, "lngE7": -1224304504},
                {"latE7": 377612037, "lngE7": -1224286727},
                {"latE7": 377604217, "lngE7": -1224307250},
            ],
            "source": "INFERRED",
            "roadSegment": [
                {"placeId": "ChIJTTaLQxp-j4ARGyHL8nP2V58", "duration": "50s"},
                {"placeId": "ChIJQU0YOxp-j4ARzltYMqf2ybc", "duration": "128s"},
                {"placeId": "ChIJxzaaiBl-j4ARmhZgp3OF8MM", "duration": "168s"},
                {"placeId": "ChIJxzaaiBl-j4ARmxZgp3OF8MM", "duration": "214s"},
                {"placeId": "ChIJQU0YOxp-j4ARzltYMqf2ybc", "duration": "184s"},
                {"placeId": "ChIJTTaLQxp-j4ARGyHL8nP2V58", "duration": "18s"},
            ],
            "distanceMeters": 593.2073502973352,
            "travelMode": "WALK",
            "confidence": 0.9991572432077641,
        },
        "simplifiedRawPath": {
            "points": [
                {
                    "latE7": 377612610,
                    "lngE7": -1224286804,
                    "accuracyMeters": 35,
                    "timestamp": "2023-12-01T01:56:56Z",
                }
            ]
        },
    }
}


def test_semantic_location_history(tmp_path_f: Path) -> None:
    data = {
        "timelineObjects": [
            _TEST_PLACE_VISIT,
            _TEST_ACTIVITY_SEGMENT_BASIC,
            _TEST_ACTIVITY_PARTIAL_WAYPOINT_PATH,
            _TEST_ACTIVITY_SEGMENT_FULL,
        ]
    }
    fp = tmp_path_f / "file"
    fp.write_text(json.dumps(data))
    res = list(prj._parse_semantic_location_history(fp))

    obj = res[0]
    assert not isinstance(obj, Exception)
    # remove JSON, compare manually below
    assert obj == models.PlaceVisit(
        lat=55.5555555,
        lng=-106.6666666,
        centerLat=55.5555555,
        centerLng=-166.6666666,
        name="name",
        address="address",
        locationConfidence=60.45,
        placeId="JK4E4P",
        startTime=datetime.datetime(
            2017, 12, 10, 23, 29, 25, 26000, tzinfo=datetime.timezone.utc
        ),
        endTime=datetime.datetime(
            2017, 12, 11, 1, 20, 6, 106000, tzinfo=datetime.timezone.utc
        ),
        sourceInfoDeviceTag=987654321,
        placeConfidence="MEDIUM_CONFIDENCE",
        placeVisitImportance="MAIN",
        placeVisitType="SINGLE_PLACE",
        visitConfidence=65.45,
        editConfirmationStatus="NOT_CONFIRMED",
        otherCandidateLocations=[
            models.CandidateLocation(
                lat=42.3984239,
                lng=-156.5656565,
                name="name2",
                address="address2",
                locationConfidence=24.475897,
                placeId="XPRK4E4P",
                sourceInfoDeviceTag=None,
            )
        ],
    )

    obj1 = res[1]
    assert obj1 == models.ActivitySegment(
        startTime=datetime.datetime(
            2012, 12, 6, 4, 9, 31, 87000, tzinfo=datetime.timezone.utc
        ),
        endTime=datetime.datetime(
            2012, 12, 6, 4, 19, 21, 52000, tzinfo=datetime.timezone.utc
        ),
        distance=735,
        confidence="LOW",
        activities=[
            models.ActivitySegmentActivity("WALKING", 0.0),
            models.ActivitySegmentActivity("CYCLING", 0.0),
            models.ActivitySegmentActivity("IN_VEHICLE", 0.0),
        ],
        simplifiedRawPath=models.SimplifiedRawPath(
            points=[
                models.RawPathPoint(
                    lat=-45.0339851,
                    lng=168.6552734,
                    accuracyMeters=5,
                    timestamp=datetime.datetime(
                        2012, 12, 6, 4, 12, 29, 104000, tzinfo=datetime.timezone.utc
                    ),
                )
            ]
        ),
        editConfirmationStatus="NOT_CONFIRMED",
    )

    obj2 = res[2]
    assert obj2 == models.ActivitySegment(
        startLat=37.7624484,
        startLng=-122.3967085,
        endLat=37.7944635,
        endLng=-122.4026022,
        startTime=datetime.datetime(
            2016, 12, 24, 0, 11, 20, 573000, tzinfo=datetime.timezone.utc
        ),
        endTime=datetime.datetime(
            2016, 12, 24, 0, 32, 23, 34000, tzinfo=datetime.timezone.utc
        ),
        distance=4393,
        activityType="IN_PASSENGER_VEHICLE",
        confidence="LOW",
        activities=[
            models.ActivitySegmentActivity("IN_PASSENGER_VEHICLE", 42.59993179064075),
            models.ActivitySegmentActivity("CYCLING", 31.740499796503187),
            models.ActivitySegmentActivity("IN_BUS", 18.35780278904862),
        ],
        waypointPath=models.WaypointPath(
            waypoints=[
                models.Waypoint(37.7624588, -122.3965377),
                models.Waypoint(37.7720146, -122.3895111),
                models.Waypoint(37.7943038, -122.4025726),
            ],
            source="INFERRED",
        ),
        simplifiedRawPath=models.SimplifiedRawPath(
            points=[
                models.RawPathPoint(
                    lat=37.7721165,
                    lng=-122.3895764,
                    accuracyMeters=10,
                    timestamp=datetime.datetime(
                        2016, 12, 24, 0, 16, 18, 999000, tzinfo=datetime.timezone.utc
                    ),
                )
            ]
        ),
        editConfirmationStatus="NOT_CONFIRMED",
    )

    obj3 = res[3]
    assert obj3 == models.ActivitySegment(
        startLat=37.7605210,
        startLng=-122.4310834,
        endLat=37.7605242,
        endLng=-122.4310477,
        startTime=datetime.datetime(
            2023, 12, 1, 1, 50, 29, 0, tzinfo=datetime.timezone.utc
        ),
        endTime=datetime.datetime(
            2023, 12, 1, 2, 3, 13, 834000, tzinfo=datetime.timezone.utc
        ),
        distance=642,
        activityType="WALKING",
        confidence="HIGH",
        activities=[
            models.ActivitySegmentActivity("WALKING", 84.14630889892578),
            models.ActivitySegmentActivity("STILL", 11.461445689201355),
            models.ActivitySegmentActivity("CYCLING", 2.6100903749465942),
            models.ActivitySegmentActivity("RUNNING", 0.8146878331899643),
            models.ActivitySegmentActivity("IN_PASSENGER_VEHICLE", 0.791911780834198),
            models.ActivitySegmentActivity("SKIING", 0.038399442564696074),
            models.ActivitySegmentActivity("IN_BUS", 0.035894475877285004),
            models.ActivitySegmentActivity("MOTORCYCLING", 0.03407726180739701),
            models.ActivitySegmentActivity("IN_FERRY", 0.02370273577980697),
            models.ActivitySegmentActivity("IN_SUBWAY", 0.01822529739001766),
            models.ActivitySegmentActivity("IN_TRAIN", 0.015967445506248623),
            models.ActivitySegmentActivity("SAILING", 0.004841846021008678),
            models.ActivitySegmentActivity("IN_TRAM", 0.004207661550026387),
            models.ActivitySegmentActivity("FLYING", 2.4401106202276424e-4),
            models.ActivitySegmentActivity("IN_VEHICLE", 5.013597093039834e-7),
        ],
        waypointPath=models.WaypointPath(
            waypoints=[
                models.Waypoint(37.7604026, -122.4310760),
                models.Waypoint(37.7607688, -122.4304504),
                models.Waypoint(37.7612037, -122.4286727),
                models.Waypoint(37.7604217, -122.4307250),
            ],
            source="INFERRED",
            roadSegment=[
                models.RoadSegment("ChIJTTaLQxp-j4ARGyHL8nP2V58", 50),
                models.RoadSegment("ChIJQU0YOxp-j4ARzltYMqf2ybc", 128),
                models.RoadSegment("ChIJxzaaiBl-j4ARmhZgp3OF8MM", 168),
                models.RoadSegment("ChIJxzaaiBl-j4ARmxZgp3OF8MM", 214),
                models.RoadSegment("ChIJQU0YOxp-j4ARzltYMqf2ybc", 184),
                models.RoadSegment("ChIJTTaLQxp-j4ARGyHL8nP2V58", 18),
            ],
            distanceMeters=593.2073502973352,
            travelMode="WALK",
            confidence=0.9991572432077641,
        ),
        simplifiedRawPath=models.SimplifiedRawPath(
            points=[
                models.RawPathPoint(
                    lat=37.7612610,
                    lng=-122.4286804,
                    accuracyMeters=35,
                    timestamp=datetime.datetime(
                        2023, 12, 1, 1, 56, 56, tzinfo=datetime.timezone.utc
                    ),
                )
            ]
        ),
    )
