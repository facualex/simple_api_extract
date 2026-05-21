from unittest.mock import MagicMock, patch

import pytest
import requests

from src.extract import fetch_all_pages, fetch_page


def _mock_response(data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.headers = {}
    mock.raise_for_status = MagicMock()
    return mock


MOVIE_FIXTURE = {"id": 1, "title": "Test Movie", "overview": "A test."}


class TestFetchPage:
    def test_returns_parsed_json(self):
        payload = {"results": [MOVIE_FIXTURE], "page": 1, "total_pages": 1, "total_results": 1}
        with patch("src.extract.requests.get", return_value=_mock_response(payload)) as mock_get:
            result = fetch_page("movie/popular", page=1)
        assert result == payload
        mock_get.assert_called_once()

    def test_sends_bearer_token(self):
        payload = {"results": [], "page": 1, "total_pages": 1, "total_results": 0}
        with patch("src.extract.requests.get", return_value=_mock_response(payload)) as mock_get:
            with patch("src.extract.API_KEY", "test-token"):
                fetch_page("movie/popular", page=1)
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"

    def test_builds_correct_url(self):
        payload = {"results": [], "page": 1, "total_pages": 1, "total_results": 0}
        with patch("src.extract.requests.get", return_value=_mock_response(payload)) as mock_get:
            with patch("src.extract.BASE_URL", "https://api.themoviedb.org/3"):
                fetch_page("movie/top_rated", page=2)
        url = mock_get.call_args[0][0]
        assert url == "https://api.themoviedb.org/3/movie/top_rated"
        assert mock_get.call_args[1]["params"]["page"] == 2

    def test_retries_on_transient_error_then_succeeds(self):
        transient = _mock_response({}, status_code=503)
        transient.raise_for_status = MagicMock(side_effect=requests.HTTPError())
        success_payload = {"results": [MOVIE_FIXTURE], "page": 1, "total_pages": 1, "total_results": 1}
        success = _mock_response(success_payload)

        with patch("src.extract.requests.get", side_effect=[transient, success]):
            with patch("src.extract.time.sleep"):
                result = fetch_page("movie/popular", page=1, max_retries=2)

        assert result == success_payload

    def test_raises_after_max_retries(self):
        transient = _mock_response({}, status_code=503)
        transient.raise_for_status = MagicMock(side_effect=requests.HTTPError("503"))

        with patch("src.extract.requests.get", return_value=transient):
            with patch("src.extract.time.sleep"):
                with pytest.raises(requests.HTTPError):
                    fetch_page("movie/popular", page=1, max_retries=2)

    def test_retries_on_network_error(self):
        success_payload = {"results": [], "page": 1, "total_pages": 1, "total_results": 0}
        success = _mock_response(success_payload)

        with patch(
            "src.extract.requests.get",
            side_effect=[requests.exceptions.ConnectionError(), success],
        ):
            with patch("src.extract.time.sleep"):
                result = fetch_page("movie/popular", page=1, max_retries=2)

        assert result == success_payload


class TestFetchAllPages:
    def test_single_page(self):
        payload = {"results": [MOVIE_FIXTURE], "page": 1, "total_pages": 1, "total_results": 1}
        with patch("src.extract.fetch_page", return_value=payload):
            with patch("src.extract.time.sleep"):
                results = fetch_all_pages("movie/popular")
        assert results == [MOVIE_FIXTURE]

    def test_multiple_pages(self):
        movie_a = {"id": 1, "title": "A"}
        movie_b = {"id": 2, "title": "B"}
        pages = [
            {"results": [movie_a], "page": 1, "total_pages": 2, "total_results": 2},
            {"results": [movie_b], "page": 2, "total_pages": 2, "total_results": 2},
        ]
        with patch("src.extract.fetch_page", side_effect=pages):
            with patch("src.extract.time.sleep"):
                results = fetch_all_pages("movie/popular")
        assert results == [movie_a, movie_b]

    def test_empty_results(self):
        payload = {"results": [], "page": 1, "total_pages": 0, "total_results": 0}
        with patch("src.extract.fetch_page", return_value=payload):
            results = fetch_all_pages("movie/popular")
        assert results == []

    def test_stops_at_total_pages(self):
        payload = {"results": [MOVIE_FIXTURE], "page": 1, "total_pages": 1, "total_results": 1}
        with patch("src.extract.fetch_page", return_value=payload) as mock_fetch:
            with patch("src.extract.time.sleep"):
                fetch_all_pages("movie/popular")
        assert mock_fetch.call_count == 1
