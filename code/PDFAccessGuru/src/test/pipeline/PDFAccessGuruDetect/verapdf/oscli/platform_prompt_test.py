from unittest.mock import MagicMock, patch

from pytest import fail
import pytest

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt import PlatformPrompt


def test_normal_case_run_echo_command() :
    """
    Normal case that tests the execution of a simple echo command. 
    Use this to verify that the execution of cli commands works concretely on the current platform.
    """
    expected: str  = "This is a test message"
    platform_prompt = PlatformPrompt()
    actual = platform_prompt.execute(["echo", expected])
    if actual is None:
        fail()
    assert expected == actual.strip('"')


@patch("pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt.platform.system")
@patch("pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt.subprocess.Popen")
def test_edge_case_execute_on_darwin(mock_popen, mock_platform_system):
    """
    Mocks platform.system() to return "Darwin" and verifies that the command is
    started with shell=False and that its standard output is returned.
    """
    command = ["ls", "-la"]
    expected = "Darwin_output_data"
    mock_platform_system.return_value = "Darwin"
    mock_popen.return_value.communicate.return_value = (expected, "")

    actual = PlatformPrompt().execute(command)

    mock_platform_system.assert_called_once()
    assert mock_popen.call_args.args[0] == command
    assert mock_popen.call_args.kwargs["shell"] is False
    assert expected == actual

@patch("pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt.platform.system")
@patch("pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt.subprocess.Popen")
def test_edge_case_execute_on_windows(mock_popen, mock_platform_system):
    """
    Mocks platform.system() to return "Windows" and verifies that the command is
    started with shell=True and that its standard output is returned.
    """
    command = ["dir"]
    expected = "Windows_output_data"
    mock_platform_system.return_value = "Windows"
    mock_popen.return_value.communicate.return_value = (expected, "")

    actual = PlatformPrompt().execute(command)

    mock_platform_system.assert_called_once()
    assert mock_popen.call_args.args[0] == command
    assert mock_popen.call_args.kwargs["shell"] is True
    assert expected == actual


@patch("pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt.platform.system")
@patch("pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt.subprocess.run")
def test_error_case_unsupported_os(mock_subprocess_run, mock_platform_system):
    """
    Mocks the platform.system() to return "RANDOM_UNSUPPORTED_OS" and expects 
    an OSError to be raised when execute is called.
    """
    mock_platform_system.return_value = "RANDOM_UNSUPPORTED_OS"
    prompt_runner = PlatformPrompt()

    # 2. Act & Assert: Wrap the failing call in pytest.raises
    with pytest.raises(OSError) as exc_info:
        prompt_runner.execute(["ls", "-la"])

    assert "No Support for operating system 'RANDOM_UNSUPPORTED_OS' implemented." in str(exc_info.value)