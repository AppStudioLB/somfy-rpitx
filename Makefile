PYTHON ?= python3
CXX ?= c++
AR ?= ar
NPM ?= npm
PREFIX ?= /usr/local
DESTDIR ?=
VENV_DIR ?= /opt/somfy-rpitx
CPPFLAGS ?=
CXXFLAGS ?= -std=c++14 -O2 -Wall -Wextra
LDLIBS ?= -lm -lrt -lpthread

LIBRPITX_SRC_DIR := third_party/librpitx/src
LIBRPITX_BUILD_DIR := build/librpitx
LIBRPITX_SOURCES := \
	$(LIBRPITX_SRC_DIR)/fskburst.cpp \
	$(LIBRPITX_SRC_DIR)/dma.cpp \
	$(LIBRPITX_SRC_DIR)/gpio.cpp \
	$(LIBRPITX_SRC_DIR)/util.cpp \
	$(LIBRPITX_SRC_DIR)/mailbox.c \
	$(LIBRPITX_SRC_DIR)/raspberry_pi_revision.c \
	$(LIBRPITX_SRC_DIR)/rpi.c
LIBRPITX_HEADERS := $(wildcard $(LIBRPITX_SRC_DIR)/*.h)
LIBRPITX_OBJECTS := \
	$(patsubst $(LIBRPITX_SRC_DIR)/%.cpp,$(LIBRPITX_BUILD_DIR)/%.cpp.o,$(filter %.cpp,$(LIBRPITX_SOURCES))) \
	$(patsubst $(LIBRPITX_SRC_DIR)/%.c,$(LIBRPITX_BUILD_DIR)/%.c.o,$(filter %.c,$(LIBRPITX_SOURCES)))
LIBRPITX_LIBRARY := $(LIBRPITX_BUILD_DIR)/librpitx-somfy.a

.PHONY: all native test test-python test-homebridge install install-sudoers clean

all: native

native: build/somfy-rpitx-tx

build/somfy-rpitx-tx: native/somfy_rpitx_tx.cpp $(LIBRPITX_LIBRARY)
	mkdir -p build
	$(CXX) $(CPPFLAGS) -I$(LIBRPITX_SRC_DIR) $(CXXFLAGS) -o $@ $< $(LIBRPITX_LIBRARY) $(LDLIBS)

$(LIBRPITX_LIBRARY): $(LIBRPITX_OBJECTS)
	$(AR) rcs $@ $^

$(LIBRPITX_BUILD_DIR)/%.cpp.o: $(LIBRPITX_SRC_DIR)/%.cpp $(LIBRPITX_HEADERS)
	mkdir -p $(LIBRPITX_BUILD_DIR)
	$(CXX) $(CPPFLAGS) -I$(LIBRPITX_SRC_DIR) $(CXXFLAGS) -fPIC -c -o $@ $<

# Upstream compiles these historical .c files as C++; rpi.c uses <cstdio>.
$(LIBRPITX_BUILD_DIR)/%.c.o: $(LIBRPITX_SRC_DIR)/%.c $(LIBRPITX_HEADERS)
	mkdir -p $(LIBRPITX_BUILD_DIR)
	$(CXX) $(CPPFLAGS) -I$(LIBRPITX_SRC_DIR) $(CXXFLAGS) -fPIC -c -o $@ $<

test: test-python test-homebridge

test-python:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

test-homebridge:
	$(NPM) test
	$(NPM) run test:syntax

install: native
	$(PYTHON) -m venv --system-site-packages "$(DESTDIR)$(VENV_DIR)"
	"$(DESTDIR)$(VENV_DIR)/bin/python" -m pip install --no-deps --no-build-isolation .
	install -d "$(DESTDIR)$(PREFIX)/bin"
	ln -sfn "$(VENV_DIR)/bin/somfy-rpitx" "$(DESTDIR)$(PREFIX)/bin/somfy-rpitx"
	ln -sfn "$(VENV_DIR)/bin/somfy-rpitx-homebridge" \
		"$(DESTDIR)$(PREFIX)/bin/somfy-rpitx-homebridge"
	install -m 0755 build/somfy-rpitx-tx "$(DESTDIR)$(PREFIX)/bin/somfy-rpitx-tx"
	install -d -m 0750 "$(DESTDIR)/etc/somfy-rpitx"
	@if [ ! -e "$(DESTDIR)/etc/somfy-rpitx/config.json" ]; then \
		install -m 0640 config.example.json "$(DESTDIR)/etc/somfy-rpitx/config.json"; \
	fi
	install -d -m 0750 "$(DESTDIR)/var/lib/somfy-rpitx"
	$(MAKE) install-sudoers DESTDIR="$(DESTDIR)"

install-sudoers:
	@if [ -z "$(DESTDIR)" ]; then /usr/sbin/visudo -cf packaging/homebridge-somfy-rpitx.sudoers; fi
	install -d "$(DESTDIR)/etc/sudoers.d"
	install -m 0440 packaging/homebridge-somfy-rpitx.sudoers \
		"$(DESTDIR)/etc/sudoers.d/homebridge-somfy-rpitx"

clean:
	rm -rf build
