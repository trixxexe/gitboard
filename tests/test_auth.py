
from gitboard.auth import clear_pat, get_pat, is_authenticated, store_pat


def test_store_and_retrieve_via_keyring(mocker):
    mocker.patch("keyring.get_password", return_value="ghp_test_token")
    token = get_pat()
    assert token == "ghp_test_token"


def test_store_pat_uses_keyring(mocker):
    mock_set = mocker.patch("keyring.set_password")
    store_pat("ghp_store_test")
    mock_set.assert_called_once_with("gitboard", "github_pat", "ghp_store_test")


def test_clear_pat_uses_keyring(mocker):
    mock_delete = mocker.patch("keyring.delete_password")
    clear_pat()
    mock_delete.assert_called_once_with("gitboard", "github_pat")


def test_fallback_to_file_when_keyring_fails(mocker, tmp_path, monkeypatch):
    mocker.patch("keyring.get_password", side_effect=RuntimeError("no backend"))
    monkeypatch.setattr("gitboard.auth.CONFIG_DIR", tmp_path)

    token_file = tmp_path / "token"
    token_file.write_text("ghp_file_token")

    token = get_pat()
    assert token == "ghp_file_token"


def test_store_fallback_to_file(mocker, tmp_path, monkeypatch):
    mocker.patch("keyring.set_password", side_effect=RuntimeError("no backend"))
    monkeypatch.setattr("gitboard.auth.CONFIG_DIR", tmp_path)

    store_pat("ghp_file_store")

    token_file = tmp_path / "token"
    assert token_file.exists()
    assert token_file.read_text().strip() == "ghp_file_store"
    assert oct(token_file.stat().st_mode)[-3:] in ("600", "600")


def test_fallback_retrieve_no_keyring_file_exists(mocker, tmp_path, monkeypatch):
    mocker.patch("keyring.get_password", side_effect=RuntimeError("no backend"))
    monkeypatch.setattr("gitboard.auth.CONFIG_DIR", tmp_path)

    token_file = tmp_path / "token"
    token_file.write_text("ghp_file_token")

    token = get_pat()
    assert token == "ghp_file_token"


def test_is_authenticated_true(mocker):
    mocker.patch("keyring.get_password", return_value="ghp_valid")
    assert is_authenticated() is True


def test_is_authenticated_false(mocker):
    mocker.patch("keyring.get_password", return_value=None)
    assert is_authenticated() is False
