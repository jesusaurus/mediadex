.PHONY: all
all: test install

.venv:
	virtualenv --python=python3 .venv

.PHONY: deps
deps: .venv
	.venv/bin/pip install -r requirements.txt

.PHONY: tdeps
tdeps: .venv
	.venv/bin/pip install -r test-requirements.txt

.PHONY: test
test: tdeps
	.venv/bin/tox -e pep8

.PHONY: install
install: deps
	.venv/bin/pip install .
