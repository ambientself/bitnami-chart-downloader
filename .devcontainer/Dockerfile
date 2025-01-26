FROM mcr.microsoft.com/devcontainers/python:1-3.12

# Install Helm
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash

# Install Helm cm-push plugin
RUN helm plugin install https://github.com/chartmuseum/helm-push
