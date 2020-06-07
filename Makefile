.PHONY: all
all: test install

.venv:
	virtualenv --python=python3 .venv

.PHONY: deps
deps: .venv
	.venv/bin/pip install -U -r requirements.txt

.PHONY: tdeps
tdeps: .venv
	.venv/bin/pip install -U -r test-requirements.txt

.PHONY: test
test: tdeps
	.venv/bin/tox -e pep8

.PHONY: install
install: deps
	.venv/bin/pip install .

.PHONY: clean
clean:
	.venv/bin/python3 setup.py clean

.PHONY: purge-movies
purge-movies:
	curl -XDELETE http://localhost:9200/movies

.PHONY: purge-music
purge-music:
	curl -XDELETE http://localhost:9200/music
