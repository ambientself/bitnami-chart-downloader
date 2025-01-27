"""
Helm Chart Downloader and ChartMuseum Uploader

This script downloads Helm charts from specified repositories and uploads them to
a ChartMuseum instance. It supports downloading specific versions or ranges of
versions and handles temporary storage of charts.

Usage:
    python chart-downloader.py -r repo1=url1 repo2=url2 \
        -c repo1/chart1:version repo2/chart2 -m chartmuseum_url
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)


def helm_check() -> None:
    """
    Verify that the Helm client is installed and accessible.

    Raises:
        subprocess.CalledProcessError: If Helm is not installed or not accessible
    """
    try:
        subprocess.run(["helm", "version", "--short"], check=True, capture_output=True, text=True)
        logging.info("Helm client verified.")
    except subprocess.CalledProcessError as e:
        logging.error("Helm client verification failed: %s", e.stderr)
        raise


def helm_repo_add(repo_name: str, repo_url: str) -> None:
    """
    Add a Helm repository to the local Helm configuration.

    Args:
        repo_name: Name to give to the repository
        repo_url: URL of the repository

    Raises:
        ValueError: If repo_name is 'chartmuseum' (reserved name)
        subprocess.CalledProcessError: If repository addition fails
    """
    if repo_name == "chartmuseum":
        raise ValueError("Reserved repository name: chartmuseum")

    try:
        subprocess.run(["helm", "repo", "add", repo_name, repo_url], check=True, capture_output=True, text=True)
        logging.info("Added Helm repository %s with URL %s.", repo_name, repo_url)
    except subprocess.CalledProcessError as e:
        logging.error("Failed to add Helm repository %s with URL %s: %s", repo_name, repo_url, e.stderr)
        raise


def helm_repo_update() -> None:
    """
    Update all Helm repositories to fetch their latest chart metadata.

    Raises:
        subprocess.CalledProcessError: If repository update fails
    """
    try:
        subprocess.run(["helm", "repo", "update"], check=True, capture_output=True, text=True)
        logging.info("Helm repositories updated.")
    except subprocess.CalledProcessError as e:
        logging.error("Failed to update Helm repositories: %s", e.stderr)
        raise


def get_latest_version(repo_name: str, chart_name: str) -> str:
    """
    Get the latest version of a specific chart from a repository.

    Args:
        repo_name: Name of the repository
        chart_name: Name of the chart

    Returns:
        str: Latest version of the chart

    Raises:
        ValueError: If version information cannot be found
        subprocess.CalledProcessError: If chart information cannot be retrieved
    """
    try:
        result = subprocess.run(
            ["helm", "show", "chart", f"{repo_name}/{chart_name}"], check=True, capture_output=True, text=True
        )
        for line in result.stdout.split("\n"):
            if line.startswith("version:"):
                _, version = line.split(":", 1)
                return version.strip()
        logging.error("Version not found in chart %s/%s", repo_name, chart_name)
        raise ValueError(f"Version not found in chart {repo_name}/{chart_name}")
    except subprocess.CalledProcessError as e:
        logging.error("Failed to get latest version for %s/%s: %s", repo_name, chart_name, e.stderr)
        raise


def helm_pull_chart(repo_name: str, chart_name: str, version: str | None = None, temp_dir: str | None = None) -> None:
    """
    Download a specific version of a Helm chart.

    Args:
        repo_name: Name of the repository
        chart_name: Name of the chart
        version: Optional specific version to download
        temp_dir: Optional directory to store the downloaded chart

    Raises:
        subprocess.CalledProcessError: If chart download fails
    """
    try:
        cmd = ["helm", "pull", f"{repo_name}/{chart_name}"]
        if version:
            cmd.extend(["--version", version])
        if temp_dir:
            cmd.extend(["--destination", temp_dir])
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info("Downloaded: %s/%s (version: %s)", repo_name, chart_name, version)
    except subprocess.CalledProcessError as e:
        logging.error("Failed to pull Helm chart %s from repository %s: %s", chart_name, repo_name, e.stderr)
        raise


def check_chart_museum(chartmuseum_url: str) -> None:
    """
    Verify that the ChartMuseum instance is accessible.

    Args:
        chartmuseum_url: URL of the ChartMuseum instance

    Raises:
        subprocess.CalledProcessError: If ChartMuseum is not accessible
    """
    try:
        subprocess.run(
            ["helm", "repo", "add", "chartmuseum", f"{chartmuseum_url}"], check=True, capture_output=True, text=True
        )
        logging.info("ChartMuseum repository verified.")
    except subprocess.CalledProcessError as e:
        logging.error("ChartMuseum repository verification failed: %s", e.stderr)
        raise


def upload_chart_to_chartmuseum(chart_name: str, chart_version: str, temp_dir: str | None = None) -> None:
    """
    Upload Helm chart to ChartMuseum

    Args:
        chart_name (str): Name of the Helm chart
        chart_version (str): Version of the Helm chart
        temp_dir (str): Temporary directory where the chart is stored

    Raises:
        FileNotFoundError: If the chart file is not found
        subprocess.CalledProcessError: If the upload fails
    """
    chart_file = f"{chart_name}-{chart_version}.tgz"
    chart_path = os.path.join(temp_dir, chart_file) if temp_dir else chart_file

    if not os.path.exists(chart_path):
        logging.error("Chart file %s not found", chart_path)
        raise FileNotFoundError(f"Chart file {chart_path} not found")

    try:
        subprocess.run(["helm", "cm-push", chart_path, "chartmuseum"], check=True, capture_output=True, text=True)
        logging.info("Uploaded: %s to ChartMuseum", chart_file)
    except subprocess.CalledProcessError as e:
        logging.error("Failed to upload Helm chart %s to ChartMuseum: %s", chart_name, e.stderr)
        raise


def get_all_versions(repo_name: str, chart_name: str) -> list[str]:
    """
    Get all available versions of a chart from a repository.

    Args:
        repo_name: Name of the repository
        chart_name: Name of the chart

    Returns:
        list[str]: Sorted list of all available versions

    Raises:
        subprocess.CalledProcessError: If versions cannot be retrieved
    """
    try:
        result = subprocess.run(
            ["helm", "search", "repo", f"{repo_name}/{chart_name}", "--versions"],
            check=True,
            capture_output=True,
            text=True,
        )
        versions = []
        for line in result.stdout.split("\n")[1:]:  # Skip header
            if line.strip():
                parts = line.split()
                versions.append(parts[1])
        return sorted(versions, key=lambda x: [int(i) for i in x.split(".")])
    except subprocess.CalledProcessError as e:
        logging.error("Failed to get versions for %s/%s: %s", repo_name, chart_name, e.stderr)
        raise


def check_chartmuseum_version(chart_name: str, version: str) -> bool:
    """
    Check if a specific version of a chart exists in ChartMuseum.

    Args:
        chart_name: Name of the chart
        version: Version to check

    Returns:
        bool: True if version exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["helm", "search", "repo", "chartmuseum/" + chart_name, "--version", version],
            check=True,
            capture_output=True,
            text=True,
        )
        # Helm output uses space-padded columns
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # Split by whitespace and get name and version columns
            parts = [p for p in line.split() if p.strip()]
            if len(parts) >= 2 and parts[1] == version:
                return True
        return False
    except (subprocess.CalledProcessError, IndexError) as e:
        logging.debug("Error checking version in ChartMuseum: %s", str(e))
        return False


def check_helm_plugin_installed(plugin_name: str) -> None:
    """
    Verify that a specific Helm plugin is installed.

    Args:
        plugin_name: Name of the plugin to check

    Raises:
        RuntimeError: If plugin is not installed
        subprocess.CalledProcessError: If plugin check fails
    """
    try:
        subprocess.run(["helm", "plugin", "list"], check=True, capture_output=True, text=True).stdout.lower().index(
            plugin_name.lower()
        )
        logging.info("Found required Helm plugin '%s'", plugin_name)
    except ValueError as exc:
        logging.error("Required Helm plugin '%s' not installed", plugin_name)
        raise RuntimeError(f"Missing Helm plugin: {plugin_name}") from exc
    except subprocess.CalledProcessError as e:
        logging.error("Failed to check Helm plugins: %s", e.stderr)
        raise


def get_version_range(versions: list[str], start_version: str | None = None) -> list[str]:
    """
    Get a range of versions starting from a specific version.

    Args:
        versions: List of all available versions
        start_version: Optional version to start from

    Returns:
        list[str]: List of versions to process
    """
    if not start_version:
        return [versions[-1]]  # Latest only
    try:
        start_idx = versions.index(start_version)
        return versions[start_idx:]
    except ValueError:
        logging.error("Version %s not found. Available versions: %s", start_version, ", ".join(versions))
        return []


def validate_chart_format(chart: str) -> None:
    """
    Validate the format of a chart specification.

    Args:
        chart: Chart specification in 'repo/chart[:version]' format

    Raises:
        ValueError: If chart format is invalid
    """
    if "/" not in chart:
        raise ValueError(f"Invalid chart format: {chart}. Must be in 'repo/chart[:version]' format")
    if chart.count(":") > 1:
        raise ValueError(f"Invalid version specifier in chart: {chart}. Must be in 'repo/chart[:version]' format")


def main() -> None:
    """
    Main function that orchestrates the chart download and upload process.

    Processes command line arguments, sets up repositories, downloads charts,
    and uploads them to ChartMuseum while managing temporary storage.

    Raises:
        Various exceptions from called functions
    """
    parser = argparse.ArgumentParser(
        description="Helm chart downloader", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "-r", "--repos", nargs="+", required=True, help="List of Helm repository names in 'name=url' format"
    )

    parser.add_argument(
        "-c", "--charts", nargs="+", required=True, help="List of Helm chart names in 'repo/chart:version' format"
    )

    parser.add_argument("-m", "--chartmuseum_url", required=True, help="URL of ChartMuseum repository")

    args = parser.parse_args()

    # Check if Helm client is installed
    helm_check()

    # Check if ChartMuseum repository is accessible
    check_chart_museum(args.chartmuseum_url)

    # Validate chart format
    for chart in args.charts:
        validate_chart_format(chart)

    # Check for required plugins early
    check_helm_plugin_installed("cm-push")

    repos = {}
    for repo in args.repos:
        name, url = repo.split("=", 1)
        repos[name] = url
        helm_repo_add(name, url)

    helm_repo_update()

    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info("Using temporary directory: %s", temp_dir)
        try:
            for chart in args.charts:
                repo, chart_name = chart.split("/", 1)
                start_version = None
                if ":" in chart_name:
                    chart_name, start_version = chart_name.split(":", 1)

                # Get all available versions
                all_versions = get_all_versions(repo, chart_name)
                versions_to_process = get_version_range(all_versions, start_version)

                if not versions_to_process:
                    continue

                for version in versions_to_process:
                    if not check_chartmuseum_version(chart_name, version):
                        logging.info(
                            "Version %s of %s/%s not found in ChartMuseum - downloading", version, repo, chart_name
                        )
                        helm_pull_chart(repo, chart_name, version, temp_dir)
                        upload_chart_to_chartmuseum(chart_name, version, temp_dir)
                        logging.info("Uploaded %s/%s version %s to ChartMuseum", repo, chart_name, version)
                    else:
                        logging.info(
                            "Version %s of %s/%s already exists in ChartMuseum - skipping", version, repo, chart_name
                        )
        finally:
            logging.info("Cleaning up temporary files")


if __name__ == "__main__":
    main()
