PY_FILES = $(shell find mediadex/ -type f -name '*.py')

.PHONY: install
install: test .venv/bin/mediadex

.venv:
	virtualenv --python=python3 .venv
	$(MAKE) refresh

.PHONY: pip
pip: .venv
	.venv/bin/pip install --upgrade pip wheel

.PHONY: deps
deps: .venv requirements.txt
	.venv/bin/pip install --upgrade --upgrade-strategy eager -r requirements.txt

.PHONY: tdeps
tdeps: .venv test-requirements.txt
	.venv/bin/pip install --upgrade --upgrade-strategy eager -r test-requirements.txt

.PHONY: refresh
refresh: pip deps tdeps

.PHONY: test
test: .venv pyproject.toml setup.cfg setup.py $(PY_FILES)
	.venv/bin/tox -e pep8

.venv/bin/mediadex: .venv pyproject.toml setup.cfg setup.py $(PY_FILES)
	.venv/bin/pip install --no-deps .

.PHONY: all
all: refresh install

.PHONY: clean
clean:
	.venv/bin/python3 setup.py clean

.PHONY: deepclean
deepclean:
	rm -r .venv

# ElasticSearch purge for schema changes
.PHONY: purge
purge: purge-music purge-movies

.PHONY: purge-movies
purge-movies:
	curl -XDELETE http://localhost:9200/movies?pretty

.PHONY: purge-music
purge-music:
	curl -XDELETE http://localhost:9200/music?pretty
