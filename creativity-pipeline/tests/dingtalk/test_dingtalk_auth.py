import pytest
from unittest.mock import Mock, patch
import os

os.environ.setdefault("DINGTALK_CLIENT_ID", "test_client_id")
os.environ.setdefault("DINGTALK_CLIENT_SECRET", "test_client_secret")


class TestDingtalkAuth:
    def test_get_auth_returns_singleton(self):
        from src.dingtalk.dingtalk_auth import get_auth, _reset_auth
        _reset_auth()
        auth1 = get_auth()
        auth2 = get_auth()
        assert auth1 is auth2

    def test_auth_uses_env_variables(self):
        from src.dingtalk.dingtalk_auth import DingtalkAuth, _reset_auth
        _reset_auth()
        auth = DingtalkAuth()
        assert auth._client_id == "test_client_id"
        assert auth._client_secret == "test_client_secret"

    def test_is_app_token_valid_returns_false_when_no_token(self):
        from src.dingtalk.dingtalk_auth import DingtalkAuth, _reset_auth
        _reset_auth()
        auth = DingtalkAuth()
        assert auth._is_app_token_valid() is False
