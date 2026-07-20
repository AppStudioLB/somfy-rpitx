PYTHON ?= python3
CXX ?= c++
NPM ?= npm
PREFIX ?= /usr/local
DESTDIR ?=
CXXFLAGS ?= -std=c++14 -O2 -Wall -Wextra
LDLIBS ?= -lrpitx -lm -lrt -lpthread

.PHONY: all native test test-python test-homebridge install clean

all: native

native: build/somfy-rpitx-tx

build/somfy-rpitx-tx: native/somfy_rpitx_tx.cpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDLIBS)

test: test-python test-homebridge

test-python:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

test-homebridge:
	$(NPM) test
	$(NPM) run test:syntax

install: native
	$(PYTHON) -m pip install . --prefix="$(DESTDIR)$(PREFIX)"
	install -d "$(DESTDIR)$(PREFIX)/bin"
	install -m 0755 build/somfy-rpitx-tx "$(DESTDIR)$(PREFIX)/bin/somfy-rpitx-tx"
	install -d -m 0750 "$(DESTDIR)/etc/somfy-rpitx"
	@if [ ! -e "$(DESTDIR)/etc/somfy-rpitx/config.json" ]; then \
		install -m 0640 config.example.json "$(DESTDIR)/etc/somfy-rpitx/config.json"; \
	fi
	install -d -m 0750 "$(DESTDIR)/var/lib/somfy-rpitx"

clean:
	rm -rf build
