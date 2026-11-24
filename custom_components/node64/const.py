from datetime import timedelta

DOMAIN = "node64"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_API_KEY = "api_key"

DEFAULT_PORT = 8080
SCAN_INTERVAL = timedelta(seconds=60)
STATS_INTERVAL = timedelta(minutes=10)
STATS_RANGES = ("24h", "30d", "1y")

PROBLEM_STATES = frozenset({"down", "degraded"})

SUB_HEALTHCHECKS = "healthchecks"
SUB_MONITOR64 = "monitor64"
SUB_PROXY64 = "proxy64"
SUB_HONEYPOT = "honeypot"
