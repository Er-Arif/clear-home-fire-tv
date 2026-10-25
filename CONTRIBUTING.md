# Contributing

Report the device model, Fire OS version, Android API if known, what you tried and what happened. State whether Home on Fire is configured and whether direct Clear Home launch works. Remove network addresses and identifiers from diagnostics; never attach local backup or signing files.

For changes, run the Python installer tests, Java ordering tests and Android build. Add regression coverage for changed recovery/permission logic. Keep accessibility services unrelated to Clear Home intact and do not introduce blanket package removal or firmware-update blocking.

Compatibility reports are welcome. A successful install on one firmware build is not evidence for every device running the same Fire OS major version. Please identify physical-device testing versus simulation/emulator testing.
