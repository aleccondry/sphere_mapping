# Python Nominal Connect App + Microbit Firmware
This repo contains an embedded Rust firmware for Micro:bit v2 and a Python visualization pipeline that maps live accelerometer + magnetometer data to an oriented textured sphere, streaming yaw/pitch/roll to a Nominal Connect client.

## Microbit Firmware
- **Target:** nRF52833 (Cortex-M4F) on Micro:bit v2; `thumbv7em-none-eabihf`.
- **Build:** uses Cargo and a simple Makefile. See [microbit-firmware/Makefile](microbit-firmware/Makefile).
- **Flash:** via `cargo embed` using [microbit-firmware/Embed.toml](microbit-firmware/Embed.toml).
- **Serial:** outputs lines like `Measurement: gx, gy, gz, ax, ay, az` at 115200 baud and calibration dumps. Python listens on `/dev/ttyACM0`.

Setup and commands:

```bash
# Install Rust + target
curl https://sh.rustup.rs -sSf | sh -s -- -y
source "$HOME/.cargo/env"
rustup target add thumbv7em-none-eabihf

# Install probe-rs cargo-embed
cargo install cargo-embed

# Build
make -C microbit-firmware build

# Flash (connect Micro:bit v2 over USB)
make -C microbit-firmware flash
```

Notes:
- Manual calibration can be triggered by sending `SCAL` over UART; firmware responds with `Calibration: center_x, center_y, center_z, scale_x, scale_y, scale_z, radius`.
- Default calibration constants are embedded; see [microbit-firmware/src/main.rs](microbit-firmware/src/main.rs).

## Python Analysis
- **Location:** [src/utils](src/utils).
- **Modules:**
	- [serial_parser.py](src/utils/serial_parser.py): opens `/dev/ttyACM0`, parses `Measurement:` and `Calibration:` lines.
	- [quaternion.py](src/utils/quaternion.py): orientation estimation with FQA and Euler extraction.
	- [sphere.py](src/utils/sphere.py): textured sphere visualization with VisPy; exports `SphereOrientation.to_bytes()`.
	- [measure.py](src/utils/measure.py): data classes for `Measurement` and `Calibration`.

Install dependencies (as listed in [app.connect](app.connect)):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pyserial numpy vispy ahrs
```

## Nominal Connect
- **Entry:** [src/sphere_app.py](src/sphere_app.py) streams frames and orientation to a Nominal Connect client.
- **UI config:** [app.connect](app.connect) defines panels, sliders, and links the script.
- **Streams:** `yaw`, `pitch`, `roll` (radians) and an RGB `frame_buffer` of the sphere.
- **Calibration flow:** set `Calibration Type` to `manual` in the right panel to request `SCAL`; firmware sends new constants, which the app applies.

Troubleshooting:
- If no frames appear, confirm the sphere texture exists at [assets/earth_texture.jpg](assets/earth_texture.jpg).
- If serial parsing fails, check the device node (e.g., `/dev/ttyACM0`) in [src/utils/serial_parser.py](src/utils/serial_parser.py).
- Ensure Micro:bit v2 is flashed and streaming at 115200 baud.
