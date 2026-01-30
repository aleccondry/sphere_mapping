#![no_main]
#![no_std]

mod calibration;
mod led;
mod serial_setup;

use core::fmt::Write;
use cortex_m_rt::entry;
use embedded_hal_nb::serial::Read;
use heapless::Vec;
use libm::{atan2f, sqrtf};
use lsm303agr::{AccelMode, AccelOutputDataRate, AccelScale, Lsm303agr};
use lsm303agr::{MagMode, MagOutputDataRate};
use microbit::display::blocking::Display;
use microbit::hal::prelude::*;
use microbit::hal::twim;
use microbit::hal::uarte::{self, Baudrate, Parity};
use microbit::hal::Timer;
use microbit::pac::twim0::frequency::FREQUENCY_A;
use panic_rtt_target as _;
use rtt_target::{rprintln, rtt_init_print};

use serial_setup::UartePort;

use crate::calibration::{calc_calibration, calibrated_measurement, Calibration, Measurement};
use crate::led::{dir_from_theta, direction_to_led, Direction};

const CALIBRATION: Calibration = Calibration {
    center: Measurement {
        x: 20962,
        y: 34322,
        z: -23924,
    },
    scale: Measurement {
        x: 1203,
        y: 1177,
        z: 1133,
    },
    radius: 48098,
};

#[entry]
fn main() -> ! {
    rtt_init_print!();
    let board = microbit::Board::take().unwrap();

    // Initialize serial uart.
    let mut serial = {
        // Set up UARTE for microbit v2 using UartePort wrapper
        let serial = uarte::Uarte::new(
            board.UARTE0,
            board.uart.into(),
            Parity::EXCLUDED,
            Baudrate::BAUD115200,
        );
        UartePort::new(serial)
    };

    // Iniitalize I2C peripheral for communication with LSM303AGR
    let i2c = { twim::Twim::new(board.TWIM0, board.i2c_internal.into(), FREQUENCY_A::K100) };

    // Initialize timer peripherals
    let mut timer0 = Timer::new(board.TIMER0);
    let mut timer1 = Timer::new(board.TIMER1);

    // Initialize LED display
    let mut display = Display::new(board.display_pins);

    // Initialize LSM303AGR sensor
    let mut sensor = Lsm303agr::new_with_i2c(i2c);
    sensor.init().unwrap();

    // Configure the sensor
    sensor
        .set_accel_mode_and_odr(&mut timer0, AccelMode::Normal, AccelOutputDataRate::Hz50)
        .unwrap();
    sensor
        .set_mag_mode_and_odr(
            &mut timer0,
            MagMode::HighResolution,
            MagOutputDataRate::Hz10,
        )
        .unwrap();
    sensor.set_accel_scale(AccelScale::G16).unwrap();

    let mut sensor = sensor.into_mag_continuous().ok().unwrap();
    let calibration = CALIBRATION.clone();
    // let calibration = calc_calibration(&mut sensor, &mut display, &mut timer0);
    rprintln!("Calibration: {:?}", calibration);
    rprintln!("Calibration done, entering busy loop");
    write!(serial, "Calibration: {:?}\r\n", calibration).unwrap();

    loop {
        while !sensor.mag_status().unwrap().xyz_new_data() {}
        let data = sensor.magnetic_field().unwrap();
        let data = calibrated_measurement(data, &calibration);

        while !sensor.accel_status().unwrap().xyz_new_data() {}
        let accel_data = sensor.acceleration().unwrap();

        let ax = accel_data.x_mg();
        let ay = accel_data.y_mg();
        let az = accel_data.z_mg();

        let gx = data.x as f32;
        let gy = data.y as f32;
        let gz = data.z as f32;

        write!(
            serial,
            "Measurement: {gx:.2}, {gy:.2}, {gz:.2}, {ax:.2}, {ay:.2}, {az:.2}\r\n"
        )
        .unwrap();

        // // Try to read one byte non-blocking
        // match serial.read() {
        //     Ok(byte) => {
        //         rprintln!("Received byte: {}", byte);
        //     }
        //     Err(nb::Error::WouldBlock) => {
        //         // No data available, continue
        //     }
        //     Err(_) => {
        //         // Handle other errors if needed
        //     }
        // }

        // Get magnitude and angle of the magnetic field.
        // Figure out the direction based on theta
        let dir = send_theta_mag(data);

        display.show(&mut timer0, direction_to_led(dir), 100);
    }
}

fn send_theta_mag(measurement: Measurement) -> Direction {
    let gx = measurement.x as f32;
    let gy = measurement.y as f32;
    let gz = measurement.z as f32;

    // Get magnitude and angle of the magnetic field.
    let theta = atan2f(gy, gx);
    let magnitude = sqrtf(gx * gx + gy * gy + gz * gz);
    rprintln!(
        "{} nT, {} mG, theta: {} rad",
        magnitude,
        magnitude / 100.0,
        theta
    );
    dir_from_theta(theta)
}

fn run_rev<T>(serial: &mut UartePort<T>) -> !
where
    T: uarte::Instance,
{
    let mut buffer = Vec::<u8, 32>::new();
    loop {
        let byte = nb::block!(serial.read()).unwrap();
        if byte == b'\r' {
            rprintln!("Received: {:?}", core::str::from_utf8(&buffer).unwrap());
            rprintln!(
                "Reversed: {:?}",
                core::str::from_utf8(&buffer.iter().rev().cloned().collect::<Vec<u8, 32>>())
                    .unwrap()
            );
            buffer.clear();
        } else {
            buffer.push(byte).unwrap();
        }
    }
}
