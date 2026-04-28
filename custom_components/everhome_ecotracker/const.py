"""Constants for the everHome EcoTracker cloud integration."""

DOMAIN = "everhome_ecotracker"

API_BASE_URL = "https://everhome.cloud"
AUTHORIZE_URL = "https://everhome.cloud/oauth2/authorize"
TOKEN_URL = "https://everhome.cloud/oauth2/token"

CONF_AUTH_CODE = "authorization_code"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_LOCAL_URL = "local_url"
CONF_REDIRECT_URI = "redirect_uri"
CONF_SOURCE = "source"
CONF_TOKEN = "token"

DEFAULT_REDIRECT_URI = "http://localhost:12345"
DEFAULT_SCAN_INTERVAL_SECONDS = 5
MIN_SCAN_INTERVAL_SECONDS = 5
MAX_SCAN_INTERVAL_SECONDS = 3600

SOURCE_CLOUD = "cloud"
SOURCE_LOCAL = "local"
