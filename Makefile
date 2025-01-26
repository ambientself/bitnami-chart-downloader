SHELL := /bin/bash

test:
	@echo "testing against local chart museum"
	@python chart-downloader.py \
		--repos \
		bitnami=https://charts.bitnami.com/bitnami \
		argo=https://argoproj.github.io/argo-helm \
		--charts \
		bitnami/external-dns \
		argo/argo-cd:7.7.15 \
		--chartmuseum_url http://172.18.133.128:8080