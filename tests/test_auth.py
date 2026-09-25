import os
import unittest

from app.auth import AuthProviderConfig, AuthenticationRegistry
from app.integrations import SecretProvider


class StaticSecretProvider(SecretProvider):
    def __init__(self, values):
        self.values = values

    def get(self, name):
        return self.values.get(name)


class AuthenticationRegistryTests(unittest.TestCase):
    def test_disabled_provider_is_not_ready(self):
        registry = AuthenticationRegistry(StaticSecretProvider({"AUTH_CLIENT_SECRET": "x"}))
        registry.register(AuthProviderConfig("oidc", enabled=False, secret_names=("AUTH_CLIENT_SECRET",)))
        self.assertEqual(registry.ready("oidc"), (False, "authentication provider is disabled"))

    def test_missing_secret_does_not_expose_secret_value(self):
        registry = AuthenticationRegistry(StaticSecretProvider({}))
        registry.register(AuthProviderConfig("oidc", enabled=True, secret_names=("AUTH_CLIENT_SECRET",)))
        ok, message = registry.ready("oidc", approved=True)
        self.assertFalse(ok)
        self.assertEqual(message, "missing runtime secret(s): AUTH_CLIENT_SECRET")

    def test_external_provider_requires_approval(self):
        registry = AuthenticationRegistry(StaticSecretProvider({"AUTH_CLIENT_SECRET": "x"}))
        registry.register(AuthProviderConfig("oidc", enabled=True, secret_names=("AUTH_CLIENT_SECRET",)))
        self.assertEqual(registry.ready("oidc"), (False, "human approval required"))
        self.assertEqual(registry.ready("oidc", approved=True), (True, "authentication provider is configured"))

    def test_snapshot_contains_metadata_not_secret_values(self):
        registry = AuthenticationRegistry(StaticSecretProvider({"AUTH_CLIENT_SECRET": "super-secret"}))
        registry.register(AuthProviderConfig("oidc", enabled=True, secret_names=("AUTH_CLIENT_SECRET",), capabilities=("login", "logout")))
        snapshot = registry.snapshot()
        self.assertEqual(snapshot["oidc"]["secret_names"], ["AUTH_CLIENT_SECRET"])
        self.assertNotIn("super-secret", str(snapshot))


if __name__ == "__main__":
    unittest.main()
