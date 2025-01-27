import subprocess
import logging
import sys
import argparse
import tempfile
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def helm_check() -> None:
    try:
        subprocess.run(
            ["helm", "version", "--short"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info("Helm client verified.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Helm client verification failed: {e.stderr}")
        raise

def helm_repo_add(repo_name:str, repo_url:str) -> None:
    if repo_name == "chartmuseum":
        raise ValueError("Reserved repository name: chartmuseum")
    
    try:
        subprocess.run(
            ["helm", "repo", "add", repo_name, repo_url],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Added Helm repository {repo_name} with URL {repo_url}.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to add Helm repository {repo_name} with URL {repo_url}: {e.stderr}")
        raise

def helm_repo_update() -> None:
    try:
        subprocess.run(
            ["helm", "repo", "update"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info("Helm repositories updated.")
    except subprocess.CalledProcessError as e:
        logging.error(f'Failed to update Helm repositories: {e.stderr}')
        raise


def get_latest_version(repo_name:str, chart_name:str) -> str:
    try:
        result = subprocess.run(
            ["helm", "show", "chart", f"{repo_name}/{chart_name}"],
            check=True,
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if line.startswith('version:'):
                _, version = line.split(':', 1)
                return version.strip()
        logging.error(f"Version not found in chart {repo_name}/{chart_name}")
        raise ValueError(f"Version not found in chart {repo_name}/{chart_name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get latest version for {repo_name}/{chart_name}: {e.stderr}")
        raise

def helm_pull_chart(repo_name:str, chart_name:str, version=None, temp_dir=None) -> None:
    try:
        cmd = ["helm", "pull", f"{repo_name}/{chart_name}"]
        if version:
            cmd.extend(["--version", version])
        if temp_dir:
            cmd.extend(["--destination", temp_dir])
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Downloaded: {repo_name}/{chart_name} (version: {version})")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to pull Helm chart {chart_name} from repository {repo_name}: {e.stderr}")
        raise

def check_chart_museum(chartmuseum_url:str) -> None:
    try:
        subprocess.run(
            ["helm", "repo", "add", "chartmuseum", f"{chartmuseum_url}"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info("ChartMuseum repository verified.")
    except subprocess.CalledProcessError as e:
        logging.error(f"ChartMuseum repository verification failed: {e.stderr}")
        raise

def upload_chart_to_chartmuseum(chart_name:str, chart_version:str, temp_dir:str | None = None) -> None:
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
        logging.error(f"Chart file {chart_path} not found")
        raise FileNotFoundError(f"Chart file {chart_path} not found")

    try:
        subprocess.run(
            ["helm", "cm-push", chart_path, "chartmuseum"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Uploaded: {chart_file} to ChartMuseum")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to upload Helm chart {chart_name} to ChartMuseum: {e.stderr}")
        raise

def get_all_versions(repo_name:str, chart_name:str) -> list[str]:
    try:
        result = subprocess.run(
            ["helm", "search", "repo", f"{repo_name}/{chart_name}", "--versions"],
            check=True,
            capture_output=True,
            text=True
        )
        versions = []
        for line in result.stdout.split('\n')[1:]:  # Skip header
            if line.strip():
                parts = line.split()
                versions.append(parts[1])
        return sorted(versions, key=lambda x: [int(i) for i in x.split('.')])
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get versions for {repo_name}/{chart_name}: {e.stderr}")
        raise

def check_chartmuseum_version(chart_name:str, version:str) -> bool:
    try:
        result = subprocess.run(
            ["helm", "search", "repo", "chartmuseum/"+chart_name, "--version", version],
            check=True,
            capture_output=True,
            text=True
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
        logging.debug(f"Error checking version in ChartMuseum: {str(e)}")
        return False

def check_helm_plugin_installed(plugin_name:str) -> None:
    try:
        subprocess.run(
            ["helm", "plugin", "list"],
            check=True,
            capture_output=True,
            text=True
        ).stdout.lower().index(plugin_name.lower())
        logging.info(f"Found required Helm plugin '{plugin_name}'")
    except ValueError:
        logging.error(f"Required Helm plugin '{plugin_name}' not installed")
        raise RuntimeError(f"Missing Helm plugin: {plugin_name}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to check Helm plugins: {e.stderr}")
        raise

def get_version_range(versions: list[str], start_version=None) -> list[str]:
    if not start_version:
        return [versions[-1]]  # Latest only
    try:
        start_idx = versions.index(start_version)
        return versions[start_idx:]
    except ValueError:
        logging.error(f"Version {start_version} not found. Available versions: {', '.join(versions)}")
        return []

def validate_chart_format(chart:str) -> None:
    if "/" not in chart:
        raise ValueError(f"Invalid chart format: {chart}. Must be in 'repo/chart[:version]' format")
    if chart.count(":") > 1:
        raise ValueError(f"Invalid version specifier in chart: {chart}. Must be in 'repo/chart[:version]' format")

def main():
    parser = argparse.ArgumentParser(
        description="Helm chart downloader",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
    
    parser.add_argument(
        "-r", "--repos",
        nargs="+",
        required=True,
        help="List of Helm repository names in 'name=url' format"
    )

    parser.add_argument(
        "-c", "--charts",
        nargs="+",
        required=True,
        help="List of Helm chart names in 'repo/chart:version' format"
    )

    parser.add_argument(
        "-m", "--chartmuseum_url",
        required=True,
        help="URL of ChartMuseum repository"
    )

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
        logging.info(f"Using temporary directory: {temp_dir}")
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
                        logging.info(f"Version {version} of {repo}/{chart_name} not found in ChartMuseum - downloading")
                        helm_pull_chart(repo, chart_name, version, temp_dir)
                        upload_chart_to_chartmuseum(chart_name, version, temp_dir)
                        logging.info(f"Uploaded {repo}/{chart_name} version {version} to ChartMuseum")
                    else:
                        logging.info(f"Version {version} of {repo}/{chart_name} already exists in ChartMuseum - skipping")
        finally:
            logging.info("Cleaning up temporary files")

if __name__ == "__main__":
    main()
