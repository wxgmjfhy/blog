HUGO ?= hugo

.PHONY: help prep build dev clean

help:
	@echo "make build   生成静态站点到 public/"
	@echo "make dev     本地预览 http://localhost:1313（含草稿）"
	@echo "make prep    只跑 src/ -> content/ 的预处理"
	@echo "make clean   清空 public/ 与生成的 content/"

prep:
	python3 scripts/mathprep.py

build: prep
	$(HUGO) --gc --minify

dev: prep
	$(HUGO) server -D --disableFastRender

clean:
	rm -rf public content resources
