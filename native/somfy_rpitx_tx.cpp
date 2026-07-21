/*
 * Minimal librpitx FSK burst backend for somfy-rpitx.
 *
 * stdin format: one "<state> <duration-us>" record per line.
 * State -1 disables the RF clock; 0/1 are logical RTS levels mapped to
 * SPACE/MARK here so inversion remains explicit.
 */

#include "fskburst.h"

#include <algorithm>
#include <chrono>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <thread>
#include <vector>

namespace {

struct Options {
    uint64_t mark_hz = 0;
    uint64_t space_hz = 0;
    uint32_t tick_us = 4;
    bool invert_mark_space = false;
};

void usage(const char *program) {
    std::cerr
        << "Usage: " << program
        << " --mark-hz HZ --space-hz HZ [--tick-us US]"
           " [--invert-mark-space]\n"
        << "Reads '<state> <duration-us>' records; state is -1, 0, or 1.\n";
}

bool parse_uint64(const char *text, uint64_t &value) {
    char *end = nullptr;
    errno = 0;
    const unsigned long long parsed = std::strtoull(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return false;
    }
    value = static_cast<uint64_t>(parsed);
    return true;
}

bool parse_options(int argc, char **argv, Options &options) {
    for (int index = 1; index < argc; ++index) {
        const std::string argument(argv[index]);
        if (argument == "--invert-mark-space") {
            options.invert_mark_space = true;
        } else if (argument == "--mark-hz" || argument == "--space-hz" ||
                   argument == "--tick-us") {
            if (++index >= argc) {
                return false;
            }
            uint64_t value = 0;
            if (!parse_uint64(argv[index], value)) {
                return false;
            }
            if (argument == "--mark-hz") {
                options.mark_hz = value;
            } else if (argument == "--space-hz") {
                options.space_hz = value;
            } else {
                if (value == 0 ||
                    value > std::numeric_limits<uint32_t>::max()) {
                    return false;
                }
                options.tick_us = static_cast<uint32_t>(value);
            }
        } else if (argument == "--help") {
            usage(argv[0]);
            std::exit(0);
        } else {
            return false;
        }
    }
    return options.mark_hz >= 50'000 &&
           options.mark_hz <= 1'500'000'000ULL &&
           options.space_hz >= 50'000 &&
           options.space_hz <= 1'500'000'000ULL &&
           options.mark_hz != options.space_hz;
}

} // namespace

int main(int argc, char **argv) {
    Options options;
    if (!parse_options(argc, argv, options)) {
        usage(argv[0]);
        return 2;
    }

    const uint64_t base_hz = std::min(options.mark_hz, options.space_hz);
    const uint64_t separation_hz =
        std::max(options.mark_hz, options.space_hz) - base_hz;
    const float symbol_rate = 1'000'000.0f / options.tick_us;

    std::vector<signed char> states;
    states.reserve(150'000);
    uint64_t requested_duration_us = 0;
    uint64_t quantized_duration_us = 0;

    int state = 0;
    uint64_t duration_us = 0;
    while (std::cin >> state >> duration_us) {
        if ((state < -1 || state > 1) || duration_us == 0 ||
            duration_us > 10'000'000ULL) {
            std::cerr << "Invalid pulse record\n";
            return 2;
        }
        signed char output_state = -1;
        if (state >= 0) {
            const bool mark_level = !options.invert_mark_space;
            const uint64_t tone_hz =
                (static_cast<bool>(state) == mark_level)
                    ? options.mark_hz
                    : options.space_hz;
            output_state = tone_hz == base_hz ? 0 : 1;
        }
        const uint64_t ticks = std::max<uint64_t>(
            1, static_cast<uint64_t>(std::llround(
                   static_cast<double>(duration_us) / options.tick_us)));
        if (states.size() + ticks > 10'000'000ULL) {
            std::cerr << "Transmission exceeds 10,000,000 DMA symbols\n";
            return 2;
        }
        states.insert(states.end(), static_cast<size_t>(ticks), output_state);
        requested_duration_us += duration_us;
        quantized_duration_us += ticks * options.tick_us;
    }
    if (!std::cin.eof()) {
        std::cerr << "Malformed pulse input\n";
        return 2;
    }
    if (states.empty()) {
        std::cerr << "No pulses supplied\n";
        return 2;
    }

    size_t active_bursts = 0;
    size_t silent_intervals = 0;
    size_t maximum_burst_symbols = 0;
    for (size_t offset = 0; offset < states.size();) {
        const bool silent = states[offset] < 0;
        size_t end = offset + 1;
        while (end < states.size() && (states[end] < 0) == silent) {
            ++end;
        }
        if (silent) {
            ++silent_intervals;
        } else {
            ++active_bursts;
            maximum_burst_symbols =
                std::max(maximum_burst_symbols, end - offset);
        }
        offset = end;
    }
    if (maximum_burst_symbols == 0) {
        std::cerr << "Pulse plan contains no RF burst\n";
        return 2;
    }

    std::cerr << "librpitx FSK burst: base=" << base_hz
              << "Hz separation=" << separation_hz
              << "Hz tick=" << options.tick_us
              << "us symbols=" << states.size()
              << " bursts=" << active_bursts
              << " silences=" << silent_intervals
              << " requested=" << requested_duration_us
              << "us quantized=" << quantized_duration_us << "us\n";

    // fskburst disables GPIO 4 at the end of every SetSymbols call.  Reusing
    // one DMA object lets us insert true carrier-off RTS gaps between bursts.
    // Gap duration is not protocol-critical; the active pulses remain DMA
    // timed. DMA channel 14 follows rpitx's own FSK examples.
    fskburst transmitter(base_hz, symbol_rate,
                         static_cast<float>(separation_hz), 14,
                         static_cast<uint32_t>(maximum_burst_symbols), 1, 0.0f);
    std::vector<unsigned char> burst;
    burst.reserve(maximum_burst_symbols);
    for (size_t offset = 0; offset < states.size();) {
        const bool silent = states[offset] < 0;
        size_t end = offset + 1;
        while (end < states.size() && (states[end] < 0) == silent) {
            ++end;
        }
        if (silent) {
            const uint64_t silence_us =
                static_cast<uint64_t>(end - offset) * options.tick_us;
            std::this_thread::sleep_for(
                std::chrono::microseconds(silence_us));
        } else {
            burst.assign(states.begin() + static_cast<std::ptrdiff_t>(offset),
                         states.begin() + static_cast<std::ptrdiff_t>(end));
            transmitter.SetSymbols(
                burst.data(), static_cast<uint32_t>(burst.size()));
        }
        offset = end;
    }
    transmitter.stop();
    return 0;
}
