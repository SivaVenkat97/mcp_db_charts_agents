import logging
from datetime import date
from typing import Any, Dict, List, Optional, Union

from core import GSCAuthenticator
from dateutil.relativedelta import relativedelta

# Set up logger
logger = logging.getLogger(__name__)


class GSCSearchAnalytics(GSCAuthenticator):
    """
    Enhanced Google Search Console Search Analytics API wrapper.

    Provides flexible search analytics data retrieval with comprehensive
    filtering, dimensions, and parameter support.
    """

    # Available dimensions mapping
    DIMENSIONS = {
        "date": "DATE",
        "query": "QUERY",
        "page": "PAGE",
        "country": "COUNTRY",
        "device": "DEVICE",
        "searchAppearance": "SEARCH_APPEARANCE",
    }

    # Available operators for filters
    OPERATORS = [
        "equals",
        "notEquals",
        "contains",
        "notContains",
        "includingRegex",
        "excludingRegex",
    ]

    # Restricted operators for specific dimensions
    RESTRICTED_OPERATORS = {
        "DEVICE": ["equals", "notEquals"],
        "SEARCH_APPEARANCE": ["equals", "notEquals"],
        "COUNTRY": ["equals", "notEquals"],
    }

    def __init__(self, service_account_file: str, property_url: str):
        """
        Initialize the Search Analytics client.

        Args:
            service_account_file (str): Path to the service account JSON file.
                                      Defaults to "service_account.json".

        Returns:
            None (constructor)

        Purpose:
            Initializes the GSCSearchAnalytics class by calling the parent
            GSCAuthenticator constructor with the service account file.
        """
        super().__init__(service_account_file, property_url)

    def query(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        dimensions: Optional[List[str]] = None,
        dimension_filter_groups: Optional[List[Dict]] = None,
        row_limit: int = 1000,
        start_row: int = 0,
        aggregation_type: str = "auto",
        data_state: str = "all",
        search_type: str = "web",
    ) -> List[Dict[str, Any]]:
        """
        Query Google Search Console Search Analytics API.

        Args:
            start_date (Optional[Union[str, date]]): Start date for query range.
                                                   Defaults to 3 months ago. Can be string
                                                   in YYYY-MM-DD format or date object.
            end_date (Optional[Union[str, date]]): End date for query range.
                                                 Defaults to today. Can be string in
                                                 YYYY-MM-DD format or date object.
            dimensions (Optional[List[str]]): List of dimensions to group by.
                                            Available: date, query, page, country,
                                            device, searchAppearance.
            dimension_filter_groups (Optional[List[Dict]]): Filter groups for dimensions.
                                                          Each group contains filters list.
            row_limit (int): Maximum number of rows to return. Default 1000, max 25000.
            start_row (int): Starting row for pagination. Default 0.
            aggregation_type (str): How to aggregate data. Options: "auto" or "byPage".
                                  Default "auto".
            data_state (str): Data state filter. Options: "all", "final", "fresh".
                            Default "all".
            search_type (str): Type of search. Options: "web", "image", "video", "news".
                             Default "web".

        Returns:
            List[Dict[str, Any]]: List of search analytics data rows containing metrics
                                like clicks, impressions, CTR, and position.

        Purpose:
            Main method to query Google Search Console Search Analytics API with flexible
            filtering and dimension options. Handles date formatting, request body building,
            API execution, and error handling.
        """
        # Set default dates (past 3 months)
        if not start_date:
            start_date = (date.today() - relativedelta(months=3)).strftime("%Y-%m-%d")
        elif isinstance(start_date, date):
            start_date = start_date.strftime("%Y-%m-%d")

        if not end_date:
            end_date = date.today().strftime("%Y-%m-%d")
        elif isinstance(end_date, date):
            end_date = end_date.strftime("%Y-%m-%d")

        # Build request body
        request_body = self._build_request_body(
            start_date=start_date,
            end_date=end_date,
            dimensions=dimensions,
            dimension_filter_groups=dimension_filter_groups,
            row_limit=row_limit,
            start_row=start_row,
            aggregation_type=aggregation_type,
            data_state=data_state,
            search_type=search_type,
        )

        # Execute API request
        try:
            service = self.service
            response = service.searchanalytics().query(siteUrl=self.site_url, body=request_body).execute()

            return response.get("rows", [])

        except Exception as e:
            raise Exception(f"Search Analytics API error: {str(e)}")

    def _build_request_body(
        self,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        dimension_filter_groups: Optional[List[Dict]] = None,
        row_limit: int = 1000,
        start_row: int = 0,
        aggregation_type: str = "auto",
        data_state: str = "all",
        search_type: str = "web",
    ) -> Dict[str, Any]:
        """
        Build the API request body.

        Args:
            start_date (str): Start date in YYYY-MM-DD format.
            end_date (str): End date in YYYY-MM-DD format.
            dimensions (Optional[List[str]]): List of dimensions to include.
            dimension_filter_groups (Optional[List[Dict]]): Filter groups for dimensions.
            row_limit (int): Maximum number of rows to return.
            start_row (int): Starting row for pagination.
            aggregation_type (str): Aggregation method ("auto" or "byPage").
            data_state (str): Data state filter ("all", "final", "fresh").
            search_type (str): Type of search ("web", "image", "video", "news").

        Returns:
            Dict[str, Any]: Dictionary containing the properly formatted API request body.

        Purpose:
            Private method that constructs the request body dictionary for the Google
            Search Console API call. Validates dimensions, applies filters, and sets
            optional parameters only when they differ from defaults.
        """

        body = {"startDate": start_date, "endDate": end_date}

        # Add dimensions if provided
        if dimensions:
            validated_dimensions = []
            for dim in dimensions:
                if dim in self.DIMENSIONS:
                    validated_dimensions.append(self.DIMENSIONS[dim])
                else:
                    raise ValueError(f"Invalid dimension: {dim}. Available: {list(self.DIMENSIONS.keys())}")
            body["dimensions"] = validated_dimensions

        # Add dimension filters if provided
        if dimension_filter_groups:
            body["dimensionFilterGroups"] = self._validate_filters(dimension_filter_groups)

        # Add optional parameters (only if not default values)
        if row_limit != 1000:
            body["rowLimit"] = min(row_limit, 25000)  # API max is 25000

        if start_row > 0:
            body["startRow"] = start_row

        if aggregation_type != "auto":
            body["aggregationType"] = aggregation_type

        if data_state != "all":
            body["dataState"] = data_state

        if search_type != "web":
            body["type"] = search_type

        return body

    def _validate_filters(self, dimension_filter_groups: List[Dict]) -> List[Dict]:
        """
        Validate dimension filter groups.

        Args:
            dimension_filter_groups (List[Dict]): List of filter group dictionaries.
                                                 Each must contain 'filters' key with
                                                 list of filter objects.

        Returns:
            List[Dict]: List of validated filter group dictionaries ready for API consumption.

        Purpose:
            Private method that validates filter group structure, ensures required fields
            are present (dimension, operator, expression), validates dimension names and
            operators against allowed values, and converts lowercase dimensions to uppercase
            format required by the API.
        """
        validated_groups = []

        for group in dimension_filter_groups:
            if "filters" not in group:
                raise ValueError("Each filter group must have a 'filters' key")

            validated_filters = []
            for filter_item in group["filters"]:
                # Validate required fields
                required_fields = ["dimension", "operator", "expression"]
                for field in required_fields:
                    if field not in filter_item:
                        raise ValueError(f"Filter missing required field: {field}")

                dimension = filter_item["dimension"]
                operator = filter_item["operator"]

                # Convert lowercase dimension to uppercase if needed
                if dimension.lower() in self.DIMENSIONS:
                    dimension = self.DIMENSIONS[dimension.lower()]
                    filter_item = filter_item.copy()  # Don't modify original
                    filter_item["dimension"] = dimension

                # Validate dimension (now check against uppercase values)
                if dimension not in self.DIMENSIONS.values():
                    raise ValueError(
                        f"Invalid filter dimension: {dimension}. Available: {list(self.DIMENSIONS.values())}"
                    )

                # Validate operator
                allowed_operators = self.RESTRICTED_OPERATORS.get(dimension, self.OPERATORS)
                if operator not in allowed_operators:
                    raise ValueError(
                        f"Invalid operator '{operator}' for dimension '{dimension}'. Allowed: {allowed_operators}"
                    )

                validated_filters.append(filter_item)

            validated_groups.append({"filters": validated_filters})

        return validated_groups

    def create_filter(self, dimension: str, operator: str, expression: str) -> Dict[str, str]:
        """
        Create a single dimension filter.

        Args:
            dimension (str): Dimension name. Available options: query, page, country,
                           device, searchAppearance.
            operator (str): Filter operator. Available: equals, notEquals, contains,
                          notContains, includingRegex, excludingRegex. Some dimensions
                          have restrictions.
            expression (str): Filter value/expression to match against.

        Returns:
            Dict[str, str]: Filter dictionary with dimension, operator, and expression keys.

        Purpose:
            Helper method to create a properly formatted single dimension filter.
            Validates dimension and operator combinations according to API restrictions.
        """
        if dimension not in self.DIMENSIONS:
            raise ValueError(f"Invalid dimension: {dimension}. Available: {list(self.DIMENSIONS.keys())}")

        gsc_dimension = self.DIMENSIONS[dimension]
        allowed_operators = self.RESTRICTED_OPERATORS.get(gsc_dimension, self.OPERATORS)

        if operator not in allowed_operators:
            raise ValueError(f"Invalid operator '{operator}' for {dimension}. Allowed: {allowed_operators}")

        return {
            "dimension": gsc_dimension,
            "operator": operator,
            "expression": expression,
        }

    def create_filter_group(self, filters: List[Dict[str, str]]) -> Dict[str, List]:
        """
        Create a filter group from multiple filters.

        Args:
            filters (List[Dict[str, str]]): List of filter dictionaries, typically
                                          created using create_filter method.

        Returns:
            Dict[str, List]: Filter group dictionary with 'filters' key containing
                           the list of filters.

        Purpose:
            Helper method to create a filter group structure required by the API.
            Multiple filters in a group are combined with AND logic.
        """
        return {"filters": filters}

    def get_total_metrics(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        dimension_filter_groups: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Get total metrics (no dimensions) for the specified period.

        Args:
            start_date (Optional[Union[str, date]]): Start date for metrics.
                                                   Defaults to 3 months ago.
            end_date (Optional[Union[str, date]]): End date for metrics.
                                                 Defaults to today.
            dimension_filter_groups (Optional[List[Dict]]): Optional filters to apply.

        Returns:
            Dict[str, Any]: Dictionary with total clicks, impressions, CTR, and position.
                          Keys: 'clicks' (int), 'impressions' (int), 'ctr' (float),
                          'position' (float).

        Purpose:
            Convenience method to get aggregated metrics without dimensional breakdown.
            Returns overall performance metrics for the site within the specified period.
        """
        rows = self.query(
            start_date=start_date,
            end_date=end_date,
            dimensions=None,
            dimension_filter_groups=dimension_filter_groups,
            row_limit=1,
        )

        if rows:
            return {
                "clicks": rows[0].get("clicks", 0),
                "impressions": rows[0].get("impressions", 0),
                "ctr": rows[0].get("ctr", 0.0),
                "position": rows[0].get("position", 0.0),
            }

        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}

    def get_top_queries(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        limit: int = 10,
        dimension_filter_groups: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing queries.

        Args:
            start_date (Optional[Union[str, date]]): Start date for query analysis.
                                                   Defaults to 3 months ago.
            end_date (Optional[Union[str, date]]): End date for query analysis.
                                                 Defaults to today.
            limit (int): Number of top queries to return. Default 10.
            dimension_filter_groups (Optional[List[Dict]]): Optional filters to apply.

        Returns:
            List[Dict[str, Any]]: List of query performance data. Each dict contains
                                'keys' (with query text) and metrics (clicks, impressions,
                                ctr, position).

        Purpose:
            Convenience method to get the best performing search queries for the site.
            Results are typically ordered by clicks or impressions.
        """
        return self.query(
            start_date=start_date,
            end_date=end_date,
            dimensions=["query"],
            dimension_filter_groups=dimension_filter_groups,
            row_limit=limit,
        )

    def get_top_pages(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        limit: int = 10,
        dimension_filter_groups: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing pages.

        Args:
            start_date (Optional[Union[str, date]]): Start date for page analysis.
                                                   Defaults to 3 months ago.
            end_date (Optional[Union[str, date]]): End date for page analysis.
                                                 Defaults to today.
            limit (int): Number of top pages to return. Default 10.
            dimension_filter_groups (Optional[List[Dict]]): Optional filters to apply.

        Returns:
            List[Dict[str, Any]]: List of page performance data. Each dict contains
                                'keys' (with page URL) and metrics (clicks, impressions,
                                ctr, position).

        Purpose:
            Convenience method to get the best performing pages/URLs for the site.
            Helps identify which content drives the most search traffic.
        """
        return self.query(
            start_date=start_date,
            end_date=end_date,
            dimensions=["page"],
            dimension_filter_groups=dimension_filter_groups,
            row_limit=limit,
        )

    def get_country_breakdown(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        limit: int = 10,
        dimension_filter_groups: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get performance breakdown by country.

        Args:
            start_date (Optional[Union[str, date]]): Start date for country analysis.
                                                   Defaults to 3 months ago.
            end_date (Optional[Union[str, date]]): End date for country analysis.
                                                 Defaults to today.
            limit (int): Number of countries to return. Default 10.
            dimension_filter_groups (Optional[List[Dict]]): Optional filters to apply.

        Returns:
            List[Dict[str, Any]]: List of country performance data. Each dict contains
                                'keys' (with country code) and metrics (clicks, impressions,
                                ctr, position).

        Purpose:
            Convenience method to analyze search performance by geographical location.
            Useful for understanding international SEO performance and market reach.
        """
        return self.query(
            start_date=start_date,
            end_date=end_date,
            dimensions=["country"],
            dimension_filter_groups=dimension_filter_groups,
            row_limit=limit,
        )

    def get_device_breakdown(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        dimension_filter_groups: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get performance breakdown by device.

        Args:
            start_date (Optional[Union[str, date]]): Start date for device analysis.
                                                   Defaults to 3 months ago.
            end_date (Optional[Union[str, date]]): End date for device analysis.
                                                 Defaults to today.
            dimension_filter_groups (Optional[List[Dict]]): Optional filters to apply.

        Returns:
            List[Dict[str, Any]]: List of device performance data. Each dict contains
                                'keys' (with device type: desktop, mobile, tablet) and
                                metrics (clicks, impressions, ctr, position).

        Purpose:
            Convenience method to analyze search performance across different device types.
            Limited to 10 results (typically 3: desktop, mobile, tablet).
        """
        return self.query(
            start_date=start_date,
            end_date=end_date,
            dimensions=["device"],
            dimension_filter_groups=dimension_filter_groups,
            row_limit=10,
        )

    def get_daily_performance(
        self,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        dimension_filter_groups: Optional[List[Dict]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get daily performance metrics.

        Args:
            start_date (Optional[Union[str, date]]): Start date for daily analysis.
                                                   Defaults to 3 months ago.
            end_date (Optional[Union[str, date]]): End date for daily analysis.
                                                 Defaults to today.
            dimension_filter_groups (Optional[List[Dict]]): Optional filters to apply.

        Returns:
            List[Dict[str, Any]]: List of daily performance data. Each dict contains
                                'keys' (with date) and metrics (clicks, impressions,
                                ctr, position) for that specific day.

        Purpose:
            Convenience method to get time-series performance data. Useful for trend
            analysis and identifying performance patterns over time.
        """
        return self.query(
            start_date=start_date,
            end_date=end_date,
            dimensions=["date"],
            dimension_filter_groups=dimension_filter_groups,
            row_limit=1000,
        )


class GSCSiteData(GSCAuthenticator):
    """
    Google Search Console Site Data API wrapper.

    Provides methods to retrieve information about sites registered
    in Google Search Console.
    """

    def list_of_sites(self) -> Dict[str, Any]:
        """
        List all sites in Search Console.

        Args:
            None

        Returns:
            dict: Dictionary containing site information for all sites accessible
                 to the authenticated account. Includes site URLs and verification status.

        Purpose:
            Retrieves a list of all websites/properties that are registered and
            accessible through the authenticated Google Search Console account.
        """
        logger.info("[DEBUG] calling sites().list()")
        return self.service.sites().list().execute()

    def site_info(self) -> Dict[str, Any]:
        """
        Get information about the current site.

        Args:
            None (uses self.site_url from parent class)

        Returns:
            Dict[str, Any]: Dictionary containing detailed information about the specific site,
                          including verification status, permissions, and site-specific settings.

        Purpose:
            Retrieves detailed information about a specific site/property registered
            in Google Search Console, including verification and permission details.
        """
        logger.info("[DEBUG] calling sites().get() for %s", self.site_url)
        return self.service.sites().get(siteUrl=self.site_url).execute()


class GSCSitemapData(GSCAuthenticator):
    """
    Google Search Console Sitemap Data API wrapper.

    Provides methods to retrieve sitemap information and status
    from Google Search Console.
    """

    def list_of_sitemaps(self) -> Dict[str, Any]:
        """
        List all sitemaps for the current site.

        Args:
            None (uses self.site_url from parent class)

        Returns:
            Dict[str, Any]: Dictionary containing information about all sitemaps
                          submitted for the site, including sitemap URLs, submission
                          dates, processing status, and error information.

        Purpose:
            Retrieves a list of all sitemaps that have been submitted to Google
            Search Console for the specified site, along with their processing status.
        """
        return self.service.sitemaps().list(siteUrl=self.site_url).execute()

    def sitemap_info(self, feed_path: str) -> Dict[str, Any]:
        """
        Get information about a specific sitemap.

        Args:
            feed_path (str): Path/URL of the sitemap to get information about.

        Returns:
            Dict[str, Any]: Dictionary containing detailed information about the specific
                          sitemap, including submission date, last download time,
                          processing status, number of URLs submitted/indexed, and any errors.

        Purpose:
            Retrieves detailed information about a specific sitemap, including processing
            status, indexing statistics, and any errors encountered during processing.
        """
        return self.service.sitemaps().get(siteUrl=self.site_url, feedpath=feed_path).execute()


class GSCURLInspection(GSCAuthenticator):
    """
    Google Search Console URL Inspection API wrapper.

    Provides methods to inspect individual URLs and get detailed
    information about their indexing status and issues.
    """

    def inspect(self, inspection_url: str) -> Dict[str, Any]:
        """
        Inspect a specific URL for indexing status and issues.

        Args:
            inspection_url (str): The complete URL to inspect. Must be a valid URL
                                within the verified site property.

        Returns:
            Dict[str, Any]: Dictionary containing comprehensive URL inspection results
                          including:
                          - Index coverage status (indexed, not indexed, etc.)
                          - Crawling information (last crawl time, crawl status)
                          - Mobile usability issues
                          - Rich results information
                          - AMP status (if applicable)
                          - Security issues
                          - Manual actions affecting the URL

        Purpose:
            Provides detailed technical information about how Google sees and processes
            a specific URL, including indexing status, crawl errors, mobile usability,
            and other factors that might affect search performance.
        """
        body = {"inspectionUrl": inspection_url, "siteUrl": self.site_url}
        return self.service.urlInspection().index().inspect(body=body).execute()
