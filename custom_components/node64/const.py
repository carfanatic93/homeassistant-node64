from datetime import timedelta

DOMAIN = "node64"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_API_KEY = "api_key"

DEFAULT_PORT = 8080
SCAN_INTERVAL = timedelta(seconds=60)

PROBLEM_STATES = frozenset({"down", "degraded"})
