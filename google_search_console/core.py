from typing import Any

from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource, build


class GSCAuthenticator:

    def __init__(self, service_account_file: str, property_url: str):
        """
        Args:
            service_account_file: str Example: "service_account.json"
            property_url: str Example: "https://episyche.com/"
        """
        self.service_account_file = service_account_file
        self.scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
        self.service: Resource | None = None
        self.credentials: Credentials | None = None
        self.site_url: str = property_url
        self.set_service()

    def authenticate(self) -> None:
        """Authenticate using a service account key JSON file."""
        self.credentials: Credentials = service_account.Credentials.from_service_account_file(
            self.service_account_file, scopes=self.scopes
        )

    def set_service(self) -> Resource:
        try:
            if not self.service:
                if not self.credentials:
                    self.authenticate()
                # Use standard Google API service
                self.service = build("searchconsole", "v1", credentials=self.credentials)
        except Exception as e:
            print(e)
            return None
        return self.service


class GSCDimensions:

    available_dimensions = {
        "query": "QUERY",
        "page": "PAGE",
        "country": "COUNTRY",
        "device": "DEVICE",
        "date": "DATE",
        "searchAppearance": "SEARCH_APPEARANCE",
    }
    allowed_operators = [
        "equals",
        "notEquals",
        "contains",
        "notContains",
        "includingRegex",
        "excludingRegex",
    ]
    restricted_operators = {
        "DEVICE": ["equals", "notEquals"],
        "SEARCH_APPEARANCE": ["equals", "notEquals"],
        "COUNTRY": ["equals", "notEquals"],
    }

    def create_filter(self, dimension: str, operator: str, expression: str) -> dict[str, str]:
        allowed = self.restricted_operators.get(dimension, self.allowed_operators)
        if operator not in allowed:
            raise ValueError(f"Invalid operator '{operator}' for {dimension}. Allowed: {allowed}")
        return {"dimension": dimension, "operator": operator, "expression": expression}

    def get_allowed_operators_for_dimension(self, dimension: str) -> list[str]:
        return self.restricted_operators.get(dimension, self.allowed_operators)


class GSCQueryExecutor(GSCAuthenticator):

    def get_search_analytics(self, request_body: dict[str, Any]) -> dict[str, Any]:
        return self.service.searchanalytics().query(siteUrl=self.site_url, body=request_body).execute()
