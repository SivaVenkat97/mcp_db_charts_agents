"""
Google Search Console MCP Server

This module provides a Model Context Protocol (MCP) server that exposes Google Search Console
functionality through various tools. It allows clients to interact with Google Search Console
data including site information, sitemaps, URL inspection, and search analytics.

The server provides tools for:
- Listing and managing verified sites
- Retrieving site information and metadata
- Managing and inspecting sitemaps
- URL inspection for individual pages
- Search analytics data with comprehensive filtering
- Performance metrics and top queries/pages

Authentication is handled via service account credentials stored in a JSON file.
"""

import logging
import sys
from typing import Any, Dict, List, Optional

from domain import (
    GSCSearchAnalytics,
    GSCSiteData,
    GSCSitemapData,
    GSCURLInspection,
)
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

logger = logging.getLogger("gsc_mcp_server")
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

SERVICE_ACCOUNT_FILE = "service_account.json"  # adjust path if needed
PROPERTY_URL = "https://episyche.com/"
# PROPERTY_URL = "sc-domain:jsonstudio.io"


# Create the server
mcp = FastMCP("Google Search Console MCP Server", host="0.0.0.0")


@mcp.resource(name="Valid Country Codes", uri="gsc://country_codes")
def country_codes() -> list[str]:
    """
    List all valid ISO 3166-1 alpha-3 country codes.
    """
    # fmt: off
    return [ 
        "IND", "USA", "GBR", "CAN", "AUS", "DEU", "FRA", "JPN", "KOR", "PRK",
        "RUS", "CHN", "BRA", "MEX", "ESP", "ITA", "NLD", "SGP", "ARE", "VNM"
    ] 
    # fmt: on


@mcp.tool()
def list_sites() -> list[str]:
    """
    List all verified sites in Google Search Console.

    Returns:
        list[str]: A list of site URLs that are verified in the Search Console account.

    Note:
        Uses the service account credentials to authenticate and retrieve the list
        of all sites the account has access to.
    """
    try:
        logger.info("Executing list_sites tool")
        s = GSCSiteData(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        raw = s.list_of_sites()
        sites = [entry["siteUrl"] for entry in raw.get("siteEntry", [])]
        logger.info("Found %d sites", len(sites))
        return sites
    except Exception as e:
        logger.error("Error in list_sites: %s", e)
        return []


@mcp.tool()
def site_info() -> dict:
    """
    Get detailed information about the default site property.

    Returns:
        dict: Site information including verification status, permissions,
              and other metadata for the authenticated site.

    Note:
        Uses the site URL configured in the SDK's site_url property.
        Returns raw JSON response from the Google Search Console API.
    """
    try:
        s = GSCSiteData(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing site_info tool for %s", s.site_url)
        result = s.site_info()
        logger.info("Retrieved site info for %s", s.site_url)
        return result
    except Exception as e:
        logger.error("Error in site_info: %s", e)
        return {"error": str(e)}


@mcp.tool()
def list_sitemaps() -> dict:
    """
    List all sitemaps and their metadata for the default site property.

    Returns:
        dict: Raw JSON response containing sitemap information including
              submission dates, last download times, warnings, and errors.

    Note:
        Returns the complete raw JSON response from the Google Search Console API
        for all sitemaps associated with the authenticated site.
    """
    try:
        sm = GSCSitemapData(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing list_sitemaps tool for %s", sm.site_url)

        raw = sm.list_of_sitemaps()
        logger.info("Retrieved sitemap list for %s", sm.site_url)

        # Return the raw JSON response (dict)
        return raw
    except Exception as e:
        logger.error("Error in list_sitemaps: %s", e)
        return {"error": str(e)}


@mcp.tool()
def sitemap_info(feed_path: str) -> dict:
    """
    Get detailed information about a specific sitemap.

    Args:
        feed_path (str): The sitemap URL or path. Can be:
            - A full URL (e.g., https://example.com/sitemap.xml)
            - A relative path (e.g., /sitemap.xml) which will be combined with the site URL

    Returns:
        dict: Raw JSON response containing detailed sitemap information including
              submission status, download times, warnings, errors, and URL counts.

    Note:
        If a relative path is provided, it will be combined with the authenticated site URL.
        Returns the complete raw JSON response from the Google Search Console API.
    """
    try:
        sm = GSCSitemapData(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)

        logger.info(
            "Executing sitemap_info tool for feed_path=%s (site=%s)",
            feed_path,
            sm.site_url,
        )

        # If a full URL is provided, use as-is
        if isinstance(feed_path, str) and feed_path.startswith("http"):
            full_sitemap_url = feed_path
        else:
            base = sm.site_url.rstrip("/")
            if not isinstance(feed_path, str):
                return {"error": "feed_path must be a string"}
            if not feed_path.startswith("/"):
                feed_path = "/" + feed_path
            full_sitemap_url = base + feed_path

        logger.info("Using full sitemap URL: %s", full_sitemap_url)
        result = sm.sitemap_info(feed_path=full_sitemap_url)
        logger.info("Retrieved sitemap info for %s", full_sitemap_url)

        # Return the raw JSON response
        return result
    except Exception as e:
        logger.error("Error in sitemap_info: %s", e)
        return {"error": str(e)}


@mcp.tool()
def inspect_url(url: str) -> dict:
    """
    Run URL inspection for a specific page to get detailed indexing information.

    Args:
        url (str): The full URL of the page to inspect (must be within the authenticated site)

    Returns:
        dict: URL inspection results including indexing status, mobile usability,
              rich results, and other Google Search Console data for the page.

    Note:
        The URL must be within the scope of the authenticated site property.
        Returns raw JSON response from the Google Search Console URL Inspection API.
    """
    try:
        ui = GSCURLInspection(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing inspect_url tool for %s (site=%s)", url, ui.site_url)
        result = ui.inspect(url) or {}
        logger.info("Retrieved URL inspection for %s", url)
        return result
    except Exception as e:
        logger.error("Error in inspect_url: %s", e)
        return {"error": str(e)}


@mcp.tool()
def search_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    dimension_filter_groups: Optional[List[Dict]] = None,
    row_limit: int = 1000,
    start_row: int = 0,
    aggregation_type: str = "auto",
    data_state: str = "all",
    search_type: str = "web",
) -> List[Dict[str, Any]]:
    """
    Fetch search analytics data with comprehensive filtering and dimension options.

    Args:
        start_date (Optional[str]): Start date for the data range (YYYY-MM-DD format)
        end_date (Optional[str]): End date for the data range (YYYY-MM-DD format)
        dimensions (Optional[List[str]]): Dimensions to group data by (e.g., ['query', 'page'])
        dimension_filter_groups (Optional[List[Dict]]): Filter groups to apply to the data
        row_limit (int): Maximum number of rows to return (default: 1000)
        start_row (int): Starting row for pagination (default: 0)
        aggregation_type (str): Data aggregation type - 'auto', 'byPage', 'byProperty' (default: 'auto')
        data_state (str): Data state filter - 'all', 'final' (default: 'all')
        search_type (str): Search type filter - 'web', 'image', 'video' (default: 'web')

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing search analytics data
                             with metrics like clicks, impressions, CTR, and position.

    Note:
        Uses the authenticated site property. Returns up to 1000 rows by default.
        Use start_row and row_limit for pagination through large datasets.
    """
    try:
        sa = GSCSearchAnalytics(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing search_analytics for %s", sa.site_url)

        result = sa.query(
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

        logger.info("Retrieved %d rows of search analytics for %s", len(result), sa.site_url)
        return result

    except Exception as e:
        logger.error("Error in search_analytics: %s", e)
        return [{"error": str(e)}]


@mcp.tool()
def get_total_metrics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    dimension_filter_groups: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Get aggregated total performance metrics for the site.

    Args:
        start_date (Optional[str]): Start date for the data range (YYYY-MM-DD format)
        end_date (Optional[str]): End date for the data range (YYYY-MM-DD format)
        dimension_filter_groups (Optional[List[Dict]]): Filter groups to apply to the data

    Returns:
        Dict[str, Any]: Dictionary containing total aggregated metrics including
                       total clicks, impressions, CTR, and average position.

    Note:
        Provides site-wide performance summary without dimensional breakdown.
        Useful for getting overall site performance metrics.
    """
    try:
        sa = GSCSearchAnalytics(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing get_total_metrics for %s", sa.site_url)

        result = sa.get_total_metrics(
            start_date=start_date,
            end_date=end_date,
            dimension_filter_groups=dimension_filter_groups,
        )

        logger.info("Retrieved total metrics for %s", sa.site_url)
        return result

    except Exception as e:
        logger.error("Error in get_total_metrics: %s", e)
        return {"error": str(e)}


@mcp.tool()
def get_top_queries(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    dimension_filter_groups: Optional[List[Dict]] = None,
) -> List[Dict[str, Any]]:
    """
    Get top performing search queries for the site.

    Args:
        start_date (Optional[str]): Start date for the data range (YYYY-MM-DD format)
        end_date (Optional[str]): End date for the data range (YYYY-MM-DD format)
        limit (int): Maximum number of top queries to return (default: 10)
        dimension_filter_groups (Optional[List[Dict]]): Filter groups to apply to the data

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing top queries with their
                             performance metrics (clicks, impressions, CTR, position).

    Note:
        Returns queries sorted by performance (typically by clicks or impressions).
        Useful for identifying the most valuable search terms driving traffic.
    """
    try:
        sa = GSCSearchAnalytics(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing get_top_queries for %s", sa.site_url)

        result = sa.get_top_queries(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            dimension_filter_groups=dimension_filter_groups,
        )

        logger.info("Retrieved %d top queries for %s", len(result), sa.site_url)
        return result

    except Exception as e:
        logger.error("Error in get_top_queries: %s", e)
        return [{"error": str(e)}]


@mcp.tool()
def get_top_pages(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    dimension_filter_groups: Optional[List[Dict]] = None,
) -> List[Dict[str, Any]]:
    """
    Get top performing pages for the site.

    Args:
        start_date (Optional[str]): Start date for the data range (YYYY-MM-DD format)
        end_date (Optional[str]): End date for the data range (YYYY-MM-DD format)
        limit (int): Maximum number of top pages to return (default: 10)
        dimension_filter_groups (Optional[List[Dict]]): Filter groups to apply to the data

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing top pages with their
                             performance metrics (clicks, impressions, CTR, position).

    Note:
        Returns pages sorted by performance (typically by clicks or impressions).
        Useful for identifying the most valuable pages driving organic search traffic.
    """
    try:
        sa = GSCSearchAnalytics(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Executing get_top_pages for %s", sa.site_url)

        result = sa.get_top_pages(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            dimension_filter_groups=dimension_filter_groups,
        )

        logger.info("Retrieved %d top pages for %s", len(result), sa.site_url)
        return result

    except Exception as e:
        logger.error("Error in get_top_pages: %s", e)
        return [{"error": str(e)}]


# TODO: this tool was not used anywhere
@mcp.tool()
def create_filter(dimension: str, operator: str, expression: str) -> Dict[str, str]:
    """
    Create a dimension filter for use in search analytics queries.

    Args:
        dimension (str): The dimension to filter on (e.g., 'query', 'page', 'country')
        operator (str): The filter operator (e.g., 'equals', 'contains', 'notEquals')
        expression (str): The value to filter by

    Returns:
        Dict[str, str]: A filter dictionary that can be used in dimension_filter_groups
                       parameter of search analytics functions.

    Note:
        This helper function creates properly formatted filter dictionaries for use
        with the search analytics API. Common operators include 'equals', 'contains',
        'notEquals', 'notContains', 'includingRegex', 'excludingRegex'.
    """
    try:
        sa = GSCSearchAnalytics(service_account_file=SERVICE_ACCOUNT_FILE, property_url=PROPERTY_URL)
        logger.info("Creating filter: %s %s %s", dimension, operator, expression)
        filter_dict = sa.create_filter(dimension, operator, expression)
        logger.info("Created filter: %s", filter_dict)
        return filter_dict
    except Exception as e:
        logger.error("Error in create_filter: %s", e)
        return {"error": str(e)}


def main():
    """
    Main entry point for the Google Search Console MCP server.

    Starts the FastMCP server and handles graceful shutdown on keyboard interrupt.
    The server runs asynchronously and exposes all the Google Search Console tools
    through the Model Context Protocol.

    Raises:
        SystemExit: Exits with code 1 if an error occurs during server startup or operation.
    """
    try:
        logger.info("Starting GSC MCP Server…")
        mcp.run(transport="streamable-http")
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
