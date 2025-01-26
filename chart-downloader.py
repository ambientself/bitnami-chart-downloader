import subprocess
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def helm_check():
    try:
        subprocess.run(
            ["helm", "version", "--short"],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info("Helm client verified.")
    except subprocess.CalledProcessError:
        print("Helm not found. Please install Helm.")
        raise

def helm_repo_add(repo_name, repo_url):
    try:
        subprocess.run(
            ["helm", "repo", "add", repo_name, repo_url],
            check=True,
            capture_output=True,
            text=True
        )
        logging.info(f"Added Helm repository {repo_name} with URL {repo_url}.")
    except subprocess.CalledProcessError:
        logging.error(f"Failed to add Helm repository {repo_name} with URL {repo_url}.")
        raise

def main():
    helm_check()

    repo_name = "bitnami"
    repo_url = "https://charts.bitnami.com/bitnami"
    helm_repo_add(repo_name, repo_url)


if __name__ == "__main__":
    main()