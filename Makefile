# Ashwin's notes: everyday commands. Run `make` to see them.
PY ?= python3

.PHONY: help deps build check serve new clean

help:
	@echo "make deps    install the two Python packages the build needs (markdown, pygments)"
	@echo "make new T=\"Post title\" [K=deck] [TAGS=a,b] [S=\"Series name\" P=2]"
	@echo "             scaffold posts/<slug>/ (Markdown article by default, K=deck for slides)"
	@echo "make build   render everything into _site/"
	@echo "make check   build, then validate metadata, links and typography (what CI runs)"
	@echo "make serve   preview at http://localhost:8000$(shell $(PY) -c 'import json;print(json.load(open("site.json"))["base"])')/"
	@echo "make clean   remove _site/"

deps:
	$(PY) -m pip install --quiet markdown pygments

build:
	$(PY) scripts/build.py

check:
	$(PY) scripts/build.py --check

serve: build
	$(PY) scripts/serve.py

# usage: make new T="Why softmax?" TAGS=llm      or      make new T="Part 2: The MLP block" K=deck S="LLM internals" P=2
new:
	@test -n "$(T)" || (echo 'usage: make new T="Post title" [K=article|deck] [TAGS=a,b] [S="Series name" P=n]'; exit 1)
	$(PY) scripts/new-post.py "$(T)" --kind $(or $(K),article) $(if $(TAGS),--tags "$(TAGS)") $(if $(S),--series "$(S)" --part $(P))

clean:
	rm -rf _site
