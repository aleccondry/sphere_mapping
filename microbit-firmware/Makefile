.PHONY: default build flash clean

default: flash

build:
	cargo build --target thumbv7em-none-eabihf

flash:
	cargo embed --target thumbv7em-none-eabihf --release

clean:
	cargo clean
