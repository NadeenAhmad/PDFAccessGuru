from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.exceptions.llm_exceptions.open_router_connection_failed_exception import OpenRouterConnectionFailedException
from pdfaccessguru.model.LLM.image import Image


def test_send_message_with_image() :
    test_image_path = Path(__file__).resolve().parents[2] / 'resources' / 'image_dummies' / 'llm_prompt_with_image_test_image_beach.png'
    
    provider = OpenRouterBaseProvider()
    image = Image.from_image_path(str(test_image_path))

    response = provider.send_message_with_image("You Task is to describe the image.", "", image)
    print(response)
    assert len(response) > 0


def test_send_message_single() :
    provider = OpenRouterBaseProvider()
    response = provider.send_message("Echo hello re", "echo hello r")
    print(response)
    assert len(response) > 0


@patch("pdfaccessguru.LLM.providers.openrouter_provider.requests.post")
def test_send_message_request_exception_service_unavailable(mock_post):
    mock_request = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 503

    exc = requests.exceptions.HTTPError(
        "503 Server Error: Service Unavailable",
        response=mock_response,
        request=mock_request,
    )
    mock_post.side_effect = exc

    provider = OpenRouterBaseProvider()

    with pytest.raises(OpenRouterConnectionFailedException) as raised:
        provider.send_message("Alea iacta est.", "Veni, vidi, vici.")

    assert raised.value.message == "503 Server Error: Service Unavailable"
    mock_post.assert_called_once()

@patch("pdfaccessguru.LLM.providers.openrouter_provider.requests.post")
def test_send_message_request_exception_too_many_requests(mock_post):
    mock_request = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 429

    exc = requests.exceptions.HTTPError(
        "429 Client Error: Too Many Requests for url: https://openrouter.ai/api/v1/chat/completions",
        response=mock_response,
        request=mock_request,
    )
    mock_post.side_effect = exc

    provider = OpenRouterBaseProvider()

    with pytest.raises(OpenRouterConnectionFailedException) as raised:
        provider.send_message("Alea iacta est.", "Veni, vidi, vici.")

    assert raised.value.message == "429 Client Error: Too Many Requests for url: https://openrouter.ai/api/v1/chat/completions"
    mock_post.assert_called_once()