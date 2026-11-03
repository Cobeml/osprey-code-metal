# Hackathon hardware capabilities and integration

Research checked 2026-10-29. Inventory authority is the user's two-page [equipment PDF](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf); the correct project-relative PDF path from the eventual equipment guide is `source/Hackathon Hardware Details.pdf`. These notes are for the report writer; all usage ideas and integrations below are proposals, not hardware-tested results. Manufacturer examples explain a class of equipment, not a claim that a particular SKU will be provided.

## What equipment is available and what does it do?

### Takeaway

Every team has access to a Raspberry Pi 5 with 16 GB RAM and a 26 TOPS AI accelerator, an Arduino-compatible microcontroller with Grove shield, a Grove 40-in-1 kit, storage, power and development accessories. All other listed categories belong to a shared checkout library; the PDF supplies no model numbers, quantities, reservation guarantees, driver versions or precise sensor specifications. [User inventory, pages 1–2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf)

### Cited Findings

The following tables explain the complete inventory. “Use / link” is an engineering proposal based on the described interfaces; confirm the actual device before wiring or installing a driver.

#### Baseline and additional compute

| Item | Plain description | Proposed use / link | Limits and evidence |
|---|---|---|---|
| Raspberry Pi 5, 16 GB | A small Linux computer: the project's main brain. RAM holds running programs and data. | Receive sensor data over USB serial, process images, store evidence, host a local browser dashboard. | GPIO is 3.3 V and not 5 V tolerant. USB, Ethernet, camera connectors and GPIO serve different purposes. [Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) |
| 26 TOPS AI accelerator | A specialized chip that executes supported neural-network calculations efficiently. TOPS means trillions of operations per second, not a guaranteed camera frame rate. | Camera → compatible model → person detection on the Pi without cloud. | The number matches Hailo-8 AI HAT+, but SKU is **unconfirmed**. The official 26 TOPS HAT+ supports vision, not the HAT+ 2's LLM/VLM features. [AI HAT comparison](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html) |
| Storage | Persistent space for the OS, code, models, recordings and logs. | Keep an offline software/model cache and timestamped event history. | PDF does not identify medium/capacity. Pi OS can be installed using Raspberry Pi Imager; do not overwrite an organizer image without checking it. [Pi getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html) |
| Power supply | Converts wall power into the voltage/current the board needs. | Run the Pi and attached low-power peripherals. | Pi 5 recommended supply mode is 5 V/5 A; 5 V/3 A reduces peripheral allowance. Battery suitability depends on output mode, not a large advertised wattage alone. [Power guidance](https://www.raspberrypi.com/documentation/computers/getting-started.html) |
| Arduino-compatible microcontroller | A small controller running a compact program to repeatedly read sensors and drive outputs. | Read Grove modules and send lines of readings over USB to the Pi; handle simple motor timing. | Exact processor, board package, logic voltage and pin mapping are unknown. [Arduino digital pins](https://docs.arduino.cc/learn/microcontrollers/digital-pins/), [Grove introduction](https://wiki.seeedstudio.com/Grove_System/) |
| Grove expansion shield | Connector board that makes attaching modules easier. | Plug compatible sensors into the correct analog, digital, I2C or UART port. | Matching plug shape does not mean matching protocol or voltage; keyed Grove plugs do not guarantee 3.3 V compatibility. [Grove system](https://wiki.seeedstudio.com/Grove_System/) |
| Grove 40-in-1 kit | A collection of modular sensors and outputs; the supplied list does not name the 40 modules. | Start with one verified module, then build an alert light/button/environment demo. | Do not invent a module inventory from a similarly named online kit. Four Grove interface types are common: digital, analog, I2C, UART. [Grove system](https://wiki.seeedstudio.com/Grove_System/) |
| Development accessories | Cables, adapters and prototyping parts used between boards. | Join the controller, sensors and Pi into one system. | Inspect connector, polarity, pinout and voltage; hardware interface compatibility remains device-specific. [Grove system](https://wiki.seeedstudio.com/Grove_System/) |
| Raspberry Pi Zero | A smaller Linux computer suitable for lightweight distributed nodes. | Remote sensor logger or simple camera node. | Zero, Zero W and Zero 2 W are different; do not assume Wi-Fi or 64-bit CPU from “Zero.” Original Zero has 512 MB RAM and needs a special camera cable. [Official Zero](https://www.raspberrypi.com/products/raspberry-pi-zero/) |
| ESP32 | A microcontroller family often used for wireless sensors. | Battery sensor node → local Wi-Fi → Pi; small actuator controller. | Original ESP32 supports Wi-Fi and Bluetooth; capabilities differ across family members, so identify suffix and board. [ESP-IDF introduction](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html) |
| Additional Arduino boards | More controllers for local sensors or motor loops. | Put one near each sensor group and forward readings to the Pi. | Board identity determines compiler/core and voltage. [Arduino digital pins](https://docs.arduino.cc/learn/microcontrollers/digital-pins/) |
| NVIDIA Jetson | Embedded Linux compute with NVIDIA GPU acceleration. | More demanding vision or robotics processing if the supplied model supports the required SDK. | JetPack bundles GPU/AI tooling; releases have explicit supported hardware lists. Do not install a current release blindly on an unidentified Jetson. [JetPack](https://developer.nvidia.com/embedded/jetpack), [supported hardware](https://developer.nvidia.com/embedded/jetpack/downloads) |
| Other embedded boards | Unspecified computers or controllers. | Possible replacement or specialized node. | No useful compatibility promise until identified. [User inventory, p1](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf) |

#### Seeing, measuring distance and locating

| Item | Plain description | Proposed use / link | Limits and evidence |
|---|---|---|---|
| Standard camera | Produces ordinary images/video. | Camera into Pi/Jetson, then person detector and saved evidence. | USB UVC and CSI cameras use different connection/software paths; verify supplied camera. [Camera hardware](https://www.raspberrypi.com/documentation/accessories/camera.html) |
| Wide-angle camera | Sees more of the scene at once. | Watch a larger sector or cover a robot's surroundings. | More scene coverage does not guarantee more detail on a distant person; verify field of view and calibrate lens geometry. [Camera specifications](https://www.raspberrypi.com/documentation/accessories/camera.html) |
| Low-light/NoIR camera | Low-light sensors improve dim-scene capture; NoIR omits the IR-cut filter so near-infrared light can be captured. | Pair compatible NoIR with an appropriate illuminator for a dark-room demo. | NoIR is not a thermal camera and does not by itself illuminate complete darkness. [Camera hardware](https://www.raspberrypi.com/documentation/accessories/camera.html) |
| AI-enabled camera | Has inference processing in or near the camera. | Export detections as well as images; potentially reduce host compute load. | Pi AI Camera is a specific IMX500 example, not a confirmed inventory item. Models/toolchain differ from Hailo. [AI Camera](https://www.raspberrypi.com/documentation/accessories/ai-camera.html) |
| Depth camera | Provides a distance image or 3D data alongside images. | Estimate distance to a visible target; obstacle avoidance. | Stereo and active-depth products differ; SDK, range, USB bandwidth and lighting limitations depend on SKU. Manufacturer reference could not be fetched in full. [Luxonis depth documentation](https://docs.luxonis.com/hardware/platform/depth/depth-accuracy/) |
| Thermal imaging camera | Images emitted infrared energy as thermal contrast. | Search for visible warm bodies or hot equipment; compare with normal camera. | Cannot see people through walls; ordinary glass obstructs typical long-wave thermal imaging. Thermal contrast is not reliable person identification. [FLIR explanation](https://www.flir.com/en-gb/discover/home-outdoor/can-thermal-imaging-see-through-walls/) |
| Infrared sensors | Broad category: may measure IR light, proximity or temperature depending on module. | Small proximity trigger or contactless temperature measurement, once identified. | “Infrared” does not imply a thermal image or any particular output. [Seeed sensor catalog](https://wiki.seeedstudio.com/Sensor_Network/) |
| 2D LiDAR | Measures distance over a plane, commonly producing a scan around a robot. | Detect obstacles and build a floor-level occupancy map using suitable mapping software. | Scan geometry and driver are device-specific; a 2D slice misses objects above/below the scan. [SLAMTEC combined sensing example](https://wiki.slamtec.com/download/attachments/83066883/SLAMTEC%20Aurora%20DatasheetV1.0_EN_20240928.pdf?api=v2&modificationDate=1733305392851&version=1) |
| 3D LiDAR | Samples distances in multiple directions to create a point cloud. | Map spatial structure or show routes/obstacles. | More data and calibration than a single distance sensor; cloud points do not automatically identify people. [Ouster documentation](https://docs.ouster.com/sensor-docs/overview/welcome) |
| Time-of-flight sensor | Times reflected light to estimate distance, often one small zone or a small array. | Measure a doorway clearance or short-range obstacle. | Range depends on module, reflectivity and lighting. ST VL53L1X's 4 m is a manufacturer example, not a hackathon guarantee. [ST product](https://www.st.com/en/imaging-and-photonics-solutions/vl53l1X), [performance conditions](https://www.st.com/resource/en/datasheet/vl53l1x.pdf) |
| Ultrasonic rangefinder | Sends sound pulses and times the returning echo. | Simple distance trigger or rover obstacle detector. | Usually best read by a microcontroller; mounting/surface shape matter. The Grove example uses one signal pin, while other sensors use separate trigger/echo. [Grove ultrasonic](https://wiki.seeedstudio.com/Grove-Ultrasonic_Ranger/) |
| GPS/GNSS receiver | Receives satellite signals to estimate its own location and time. GNSS is the umbrella term, GPS one constellation. | Outdoor geotagging of a sensor or robot; forward coordinates with alerts. | Buildings, indoor/underground use and multipath degrade positioning. It does not directly locate an uninstrumented victim. [GPS accuracy](https://www.gps.gov/gps-accuracy-0) |
| Positioning module | General term for a board providing location information. | Use as a position source for incident messages. | Could mean GNSS, UWB or another system; cannot select a driver from the category alone. [User inventory, p1](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf) |
| IMU | A bundle of inertial sensors, usually accelerometer plus gyroscope, sometimes magnetometer. | Track orientation, detect movement and help stabilize robot estimates. | Needs calibration and fusion; do not treat integrated acceleration as a drift-free indoor GPS. [Analog Devices localization discussion](https://www.analog.com/en/resources/analog-dialogue/articles/enhancing-robotic-localization.html) |
| Accelerometer | Measures acceleration including the gravity-related component. | Tilt, vibration and movement cues. | Orientation and motion must be separated in software. [IMU explanation](https://learn.adafruit.com/adafruit-9-dof-imu-breakout/introduction) |
| Gyroscope | Measures angular velocity: how fast the device rotates. | Stabilize a camera/robot and improve orientation estimates. | Bias accumulates if rotation is integrated without correction. [Analog Devices](https://www.analog.com/en/resources/analog-dialogue/articles/enhancing-robotic-localization.html) |
| Magnetometer | Measures magnetic field, usable as a compass after calibration. | Add heading information to an outdoor alert or robot. | Metal and electronics can distort heading; use it as evidence with quality checks. [Accelerometer/compass](https://learn.adafruit.com/lsm303-accelerometer-slash-compass-breakout?view=all) |

#### Radios, motion, environmental and audio sensing

| Item | Plain description | Proposed use / link | Limits and evidence |
|---|---|---|---|
| Software-defined radio (SDR) | Radio whose signal processing is largely software-configured. | Explore a permitted test beacon or spectrum; feed USB samples to a laptop/Pi. | Receive/transmit capability depends on hardware; HackRF is one half-duplex transceiver example, not the expected device. SDR is not a ready-made emergency network. [HackRF](https://www.greatscottgadgets.com/hackrf/one/) |
| Wi-Fi adapter | Gives a host a local wireless network interface. | Local dashboard/video on a team access point without Internet. | Adapter/driver must support required client or AP mode. Network infrastructure and Internet are separate. [Pi network configuration](https://www.raspberrypi.com/documentation/computers/configuration.html) |
| Bluetooth | Short-range wireless connection used for peripherals, setup and small messages. | Phone setup link or local sensor connection. | Classic Bluetooth versus BLE and supported roles vary by board. [ESP32 documentation](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html) |
| LoRa module | Low-power radio modulation designed for long-range, low-rate links. | Send compact SOS, hazard value, location and timestamp between compatible radios. | LoRa is not LoRaWAN and does not imply mesh; matching radios/firmware required. Small alert messages are a better fit than images/video. [Semtech LoRa FAQ](https://www.semtech.com/design-support/faq/P120), [LoRa vs LoRaWAN](https://www.semtech.com/design-support/faq/faq-lorawan/P20) |
| UWB ranging | Radios that estimate distance through very precise radio timing. | Locate tagged responders/assets relative to placed anchors. | Requires compatible endpoints and known geometry for position; does not locate arbitrary people without tags. Do not promise smartphone interoperability. [Qorvo overview](https://www.qorvo.com/resources/d/qorvo-getting-back-to-basics-with-ultra-wideband-uwb-white-paper) |
| Other wireless modules | Unspecified radios. | Possible alternate communication link. | Frequency, antenna, protocol, permissions and driver unknown. [User inventory, p1](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf) |
| mmWave radar | High-frequency radio sensing; suitable FMCW modules estimate range, speed and angle. | Presence/motion cue to confirm a camera alert or point a camera. | Some vendor demos infer breathing under constrained conditions; not proof of victim detection through rubble or a medical measurement. [TI training](https://www.ti.com/video/series/mmwave-training-series.html), [vital-signs demo](https://www.ti.com/content/dam/videos/external-videos/es-mx/2/3816841626001/5428037798001.mp4/subassets/mmwave_vital_signs_lab_user_guide.pdf) |
| Doppler radar | Uses frequency changes in reflections to sense motion. | Trigger a closer inspection when movement occurs. | Basic Doppler modules are not automatically range/angle sensors. Exact output/algorithm depends on model. [Seeed example](https://wiki.seeedstudio.com/Grove-Doppler-Radar/) |
| PIR motion sensor | Detects changes in infrared energy as warm objects move. | Cheap low-power wake-up trigger for camera/lighting. | Not a camera, rangefinder, person counter or reliable stationary-person detector. [Adafruit PIR guide](https://learn.adafruit.com/pir-passive-infrared-proximity-motion-sensor) |
| Temperature sensor | Measures temperature at the sensor or specified target. | Flag a changed local condition. | Distinguish ambient, contact and remote infrared devices. [Environmental sensor catalog](https://wiki.seeedstudio.com/Sensor_Network/) |
| Humidity sensor | Measures water vapor, commonly relative humidity. | Environmental context and compensation for other sensors. | Humidity can influence gas readings. [Sensirion SVM30](https://sensirion.com/products/catalog/SVM30) |
| Pressure sensor | Measures air pressure, often usable for relative altitude estimation. | Add environmental context or floor-change clues. | Not a standalone accurate indoor location source. [IMU/barometer example](https://learn.adafruit.com/adafruit-9-dof-imu-breakout/introduction) |
| Gas sensor | Responds to one or more chemicals according to its sensing technology. | Demonstrate a gas-change alert using safe test inputs. | Species, warm-up, calibration and cross-sensitivity are crucial. Do not label an unspecified gas sensor a CO detector or life-safety instrument. [Sensirion design guide](https://sensirion.com/media/documents/45B45DA4/66D9B5CD/TC_AN_STC31-C_Design_Guide_D1.pdf) |
| Air-quality sensor | Reports a pollutant-related metric such as particles, VOC index or gas estimate, depending on device. | Visualize local change and report the exact measurement/units. | An air-quality index is not a general “safe air” determination. [Sensirion module example](https://sensirion.com/products/catalog/SVM30) |
| Light sensor | Measures incident light rather than creating an image. | Detect lighting loss or adapt a camera/indicator. | Raw analog level may not equal calibrated lux. [Seeed sensors](https://wiki.seeedstudio.com/Sensor_Network/) |
| Other environmental sensors | Unspecified physical/environmental probes. | Decide only after inventory inspection. | No guaranteed water, flame, radiation or oxygen sensor is named. [User inventory, p1](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf) |
| Microphones | Convert sound into an electrical/digital signal. | Listen for calls, record short evidence, or classify sounds locally. | USB, I2S and analog microphones require different inputs; one mic is not a direction-finding array. [Seeed audio example](https://wiki.seeedstudio.com/respeaker_xvf3800_xiao_getting_started/) |
| Speakers | Convert audio signals into sound. | Local alarm or recorded instructions. | Need a suitable audio output and amplifier; do not power a bare loudspeaker from GPIO. [Seeed audio system](https://wiki.seeedstudio.com/ReSpeaker_Mic_Array_v2.0/) |
| Acoustic sensors | Broad category, possibly sound-level, vibration or contact sensors. | Threshold trigger for a follow-up inspection. | Do not assume full audio waveform or human-speech recognition. [Seeed sensor catalog](https://wiki.seeedstudio.com/Sensor_Network/) |
| Audio processing modules | Boards that preprocess audio, possibly noise suppression, voice activity or direction estimation. | Microphone array → direction cue → pan-tilt camera. | Features require the right array/firmware; Seeed's USB and I2S modes illustrate why hardware identity matters. [Seeed audio module](https://wiki.seeedstudio.com/respeaker_xvf3800_xiao_getting_started/) |

#### Robotics, actuation, electronics, testing and assembly

These descriptions are generic functions, not claims about an unnamed robot's API or ruggedness. Robotics integration feasibility remains a gap until checkout inventory is known.

| Item | Plain description / proposed use | Integration and evidence |
|---|---|---|
| Wheeled robot | Motorized vehicle; carry a sensor/camera over smooth ground. | Pi sends high-level commands to existing motor controller; verify vendor SDK and emergency stop. Underlying motor control example: [Adafruit](https://learn.adafruit.com/adafruit-raspberry-pi-lesson-9-controlling-a-dc-motor?view=all). |
| Tracked robot | Vehicle using continuous tracks; potential sensor carrier over some uneven surfaces. | Exact terrain capability/payload unknown; same command/controller separation. [Inventory p2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf). |
| Legged robot | Uses articulated legs; could inspect spaces or carry sensing payloads. | Locomotion, balance and SDK are vendor-dependent; reserve only if working examples exist. [Inventory p2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf). |
| Robotic arm | Several controlled joints move an end effector. | Point a sensor, manipulate a demo object; kinematics and controller API needed. [Actuator overview](https://learn.adafruit.com/use-dc-stepper-servo-motor-solenoid-rp2040-pico). |
| Mobile robotics kit | A packaged robot development platform. | Prefer its proven motion/sensor examples before adding autonomy. Exact contents unknown. [Inventory p2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf). |
| Programmable microdrone | Small aircraft with some programmatic control. | Short controlled scouting demo; payload and positioning often restrictive. Crazyflie is an example ecosystem with Python API, radio and positioning systems, not a confirmed supplied drone. [Bitcraze](https://www.bitcraze.io/documentation/system/). |
| FPV drone | Aircraft optimized for pilot-view video; useful for a human-guided inspection view. | FPV does not imply an SDK or autonomous flight; controller identity is unresolved. [Inventory p2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf). |
| Drone development platform | Airframe/autopilot intended for software experiments. | FPV does not itself imply autonomous control or an SDK. PX4 flight controllers are one ecosystem; confirm actual firmware before choosing MAVLink/PX4 tools. [PX4 flight controller overview](https://docs.px4.io/main/en/flight_controller/). |
| DC motor | Rotates when powered; speed/direction controlled through a driver. | Drive wheels/fan; GPIO commands driver, driver supplies motor power. [DC motor guide](https://learn.adafruit.com/adafruit-raspberry-pi-lesson-9-controlling-a-dc-motor?view=all). |
| Servo | Actuator commonly commanded to an angle; some versions rotate continuously. | Pan camera or position an indicator; verify command format and power. [Actuator guide](https://learn.adafruit.com/use-dc-stepper-servo-motor-solenoid-rp2040-pico). |
| Motor controller | Power electronics between control signals and motors. | Match motor voltage/current including startup/stall demand; commands may be PWM, serial or bus. [DC motor guide](https://learn.adafruit.com/adafruit-raspberry-pi-lesson-9-controlling-a-dc-motor?view=all). |
| Pan-tilt mechanism | Two axes that aim an attached device. | Sweep a camera or point it at an audio cue; requires mounting and calibration. [Servo/actuator guide](https://learn.adafruit.com/use-dc-stepper-servo-motor-solenoid-rp2040-pico). |
| Other actuators | Components that cause physical change. | Determine power, driver and control interface individually. [Actuator guide](https://learn.adafruit.com/use-dc-stepper-servo-motor-solenoid-rp2040-pico). |
| Breadboard | Solderless contact grid for temporary circuits. | Build a small sensor/LED circuit before making it permanent. [Adafruit breadboards](https://learn.adafruit.com/breadboards-for-beginners/breadboard-usage). |
| Jumper wires | Reusable short interconnect wires. | Join header pins and breadboard contacts; pin map should be recorded. [Breadboard guide](https://learn.adafruit.com/breadboards-for-beginners/breadboard-usage). |
| Connectors | Detachable electrical/mechanical joining parts. | Reliable modular wiring; identical appearance is not proof of matching pinout. [Grove connector system](https://wiki.seeedstudio.com/Grove_System/). |
| Resistors | Limit current or establish voltage/pin states. | Current limit for an LED; pull-up/down when required. [LED/resistor guide](https://learn.adafruit.com/all-about-leds/revisiting-resistors). |
| LEDs | Small light emitters. | Status and alert indicators; use suitable current limiting. [LED guide](https://learn.adafruit.com/adafruit-arduino-lesson-3-rgb-leds/breadboard-layout). |
| Switches | Manually open/close an electrical connection. | SOS/test/acknowledge input; account for contact bounce in firmware. [Digital input basics](https://docs.arduino.cc/learn/microcontrollers/digital-pins/). |
| Other components | Unspecified passive/active electronics. | No inventory-specific promises. [Inventory p2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf). |
| Multimeter | Measures voltage, current, resistance and continuity. | First tool for checking power and broken connections. [Adafruit multimeters](https://learn.adafruit.com/multimeters/overview). |
| Oscilloscope | Shows actual voltage as it changes over time. | Diagnose noisy power, pulse timing and electrical signal quality. [Saleae comparison](https://articles.saleae.com/logic-analyzers/logic-analyzer-vs.-oscilloscope). |
| Logic analyzer | Records digital high/low timing on multiple wires. | Inspect I2C, SPI or UART messages and locate protocol problems. [Saleae comparison](https://blog.saleae.com/what-is-the-difference-between-a-logic-analyzer-and-an-oscilloscope/). |
| USB serial adapter | Bridges USB on the laptop to a device's serial port. | Read console/debug logs or UART sensor output. Select the correct electrical standard/voltage; TTL UART is not RS-232. [Pi UART](https://www.raspberrypi.com/documentation/computers/configuration.html#configuring-uarts). |
| Bench power supply | Adjustable laboratory power source. | Bring up a prototype at specified voltage with appropriate current limit. | 
| Soldering station and solder | Controlled heated tool plus metal alloy for permanent electrical joints. | Secure tested circuits/connectors after breadboard prototype works. [Adafruit soldering tools](https://learn.adafruit.com/adafruit-guide-excellent-soldering/tools). |
| Wire | Carries power or signals. | Choose gauge/connectors for current and mechanical use. [Soldering tools](https://learn.adafruit.com/adafruit-guide-excellent-soldering/tools). |
| Heat-shrink tubing | Insulating sleeve that shrinks when heated. | Cover exposed splices and reduce accidental shorts. | 
| Crimping tools | Mechanically attach compatible terminals to wires. | Make removable sensor/power leads; match tool to terminal. | 
| Hand tools / assembly supplies | Cutters, strippers, drivers and mounting supplies. | Fasten boards and route cables so a demo survives handling. [Soldering/assembly tools](https://learn.adafruit.com/adafruit-guide-excellent-soldering/tools). |
| Portable monitor | Local display for setup or responder information. | HDMI/compatible display output from Pi/Jetson; confirm connector. [Pi getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html). |
| USB hub | Expands USB ports; powered versions may help peripheral power. | Connect camera, serial devices and keyboard. Aggregate bandwidth/power are shared. [Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html). |
| Extra power supplies | Sources for other boards, motors or peripherals. | Verify voltage/polarity/current and common-ground needs. [Pi power guide](https://www.raspberrypi.com/documentation/computers/getting-started.html). |
| Batteries | Stored energy for a mobile/offline node. | Plan runtime from measured watts and usable watt-hours; verify charger/regulator compatibility. Specific capacity and safety features unknown. [Inventory p2](../../../02-equipment/source/Hackathon%20Hardware%20Details.pdf). |
| Cables and adapters | Bridge physical connections. | Bring data-capable USB cable, appropriate camera ribbon, Ethernet and display adapter. Correct connector alone does not prove data/power compatibility. [Pi getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html). |

### Inferences

- Lowest-friction architecture: Grove module → compatible shield/controller → USB serial → Pi → local log/dashboard. Add a camera or radio only after this path works.
- Camera + supported local model is plausible for “person visible here”; thermal/radar/audio may add corroboration but cannot establish rescue certainty.
- Build on guaranteed hardware; make shared thermal, LoRa, UWB or robot equipment optional enhancement paths.
- The common Pi5 26 TOPS match is Hailo-8, **not a confirmed identity**. If confirmed, use the maintained Raspberry Pi camera/Hailo stack. Do not assume the accelerator runs arbitrary PyTorch models directly or accelerates a local chatbot.

### Gaps

- Exact model and connection for every shared item; Grove kit contents; microcontroller voltage and bootloader; camera and accelerator identities.
- Bench supply, heat-shrink and crimp-tool rows give basic generic definitions; these were not independently researched to a specific manufacturer document. No SKU compatibility claim is made.
- Full-page fetches for several SparkFun tutorials failed (403); Arduino pages exposed only their JS wrapper. Adafruit and manufacturer sources supplied most basic explanations. Luxonis depth page fetch failed; depth performance remains deliberately unspecified.

## How do the systems fit together, and where do integrations fail?

### Takeaway

A useful prototype needs a sensing chain, a compute chain, a communication chain, and power for all three. A connector, a network link and a software protocol solve different problems; shared shapes and brand names do not guarantee interoperability.

### Cited Findings

- An analog-output sensor needs an ADC (often provided on a microcontroller or external converter); Raspberry Pi GPIO does not directly digitize analog voltage. Verify both the sensor output range and the ADC input limit. [Arduino analog inputs](https://docs.arduino.cc/learn/microcontrollers/analog-input/)
- GPIO pins carry simple digital signals. I2C, SPI, UART and PWM repurpose pins for structured communication or control. Pi pins are 3.3 V and must not receive 5 V logic. [Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- Grove standardizes connectors, while digital, analog, I2C and UART remain distinct electrical/data interfaces. A module needs the matching port and driver. [Seeed Grove](https://wiki.seeedstudio.com/Grove_System/)
- The Hailo accelerator uses PCIe on Pi5. `rpicam-apps` and Picamera2 can use supported Hailo networks after dependencies/models are installed. Current official directions name 64-bit Raspberry Pi OS Trixie; do not combine old Bookworm-era instructions with current packages without checking the supplied image. [AI installation](https://www.raspberrypi.com/documentation/computers/ai.html)
- LoRa PHY and LoRaWAN network architecture are distinct. LoRaWAN adds gateways and a network server; two compatible radios can instead use another supported point-to-point protocol. [Semtech](https://www.semtech.com/design-support/faq/faq-lorawan/P20)
- Ranging to a tag, estimating own position, and detecting an untagged person are different tasks. UWB two-way ranging uses cooperating endpoints; GNSS determines receiver position; image/radar/audio detectors measure scene evidence. [Qorvo](https://www.qorvo.com/resources/d/qorvo-getting-back-to-basics-with-ultra-wideband-uwb-white-paper), [GPS](https://www.gps.gov/gps-accuracy-0)
- Thermal imaging is based on the surface/object infrared energy reaching the camera, not seeing through solid rubble. [FLIR](https://www.flir.com/en-gb/discover/home-outdoor/can-thermal-imaging-see-through-walls/)
- An autopilot controls flight; companion software should use the actual supported controller interface. Small drones can depend on external positioning infrastructure for autonomous operation. [PX4](https://docs.px4.io/main/en/flight_controller/), [Bitcraze](https://www.bitcraze.io/documentation/system/)

### Inferences

Recommended integration ladder:

1. **Read one sensor.** Verify units and sample interval on the controller's serial console.
2. **Transmit to the Pi.** One JSON line per event is a simple proposed contract; include sensor ID, sequence, measurement, unit and timestamp quality.
3. **Store and display locally.** A dashboard must load its JavaScript, fonts, icons and maps locally to work when Internet access disappears.
4. **Add inference.** Keep original sensor evidence and model confidence separate; a “person” detection is a hypothesis.
5. **Add low-rate radio.** Send alert summaries rather than raw video. Include freshness, acknowledgement and retries so “delivered” has a concrete meaning.
6. **Add location.** Say whether coordinates locate the sensor, a tagged responder, or an inferred target. If location is unknown, show unknown rather than false precision.
7. **Add a robot last.** Start with manual teleoperation and a stop mechanism before autonomous navigation.

Example architectures to diagram:

- Baseline: Grove sensor → Arduino → USB → Pi → local browser + local storage.
- Vision: camera → Pi/Hailo → detection event + image evidence → local dashboard; optional LoRa relay for compact metadata.
- Tagged-person location: UWB anchors + responder tag → Pi positioning service → local map. Requires enough compatible ranging hardware and known anchor placement.
- Inspection robot: sensor/camera → onboard Pi; Pi → motor controller → motors; controller/IMU/range sensors → feedback; local radio carries commands/observations.

### Gaps

No hardware is attached or tested. No range, battery runtime, detection accuracy, radio delivery reliability, rough-terrain capability or through-obstacle performance can be promised from this inventory. Power budgets, timestamps, coordinate frames and mounting calibration must be measured on the eventual prototype.

## What should be clarified before the hackathon?

### Takeaway

The highest-value organizer request is an exact SKU list plus preinstalled images and known-good demos. That determines which code can run immediately; the generic category list cannot.

### Cited Findings

- Current Raspberry Pi AI setup has specific OS and accelerator dependencies; vision requires a supported camera. [AI software](https://www.raspberrypi.com/documentation/computers/ai.html)
- NVIDIA's supported Jetson hardware varies with JetPack release. [JetPack downloads](https://developer.nvidia.com/embedded/jetpack/downloads)
- ESP32 family board identity determines the setup procedure, USB path and compiler target. [Espressif setup](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html)

### Inferences

Ask organizers, in priority order:

1. Exact Pi accelerator make/model, OS image/version, cooling, preloaded libraries/models, and whether a camera is guaranteed.
2. Arduino-compatible board and Grove shield model, logic voltage, kit contents, known-good examples and data cables.
3. Shared-device checkout list with exact model, quantities, APIs and working starter projects; request reservations for any project-critical component.
4. LoRa frequency variants, antenna availability and permitted configuration; UWB anchor/tag count and firmware; local AP/router provision.
5. Battery capacities/output modes, charging facilities, permitted use areas for drones/robots and available demo space.
6. Whether participants must use a sponsor toolchain or comply with repository/license/release requirements.

Glossary for the crash course: **firmware** is code flashed onto a controller; **driver** lets software operate a device; **SDK** bundles APIs/tools/examples; **GPIO** is programmable digital pins; **ADC** converts analog voltage into numbers; **I2C/SPI/UART** are wired interfaces; **PWM** is pulse timing for control; **CSI** carries camera data; **PCIe** attaches fast peripherals such as an accelerator; **inference** executes a trained model; **sensor fusion** combines measurements with assumptions about time/location; **SLAM** builds a map while estimating motion through it; **edge AI** runs inference at the device; **local network** can exist without Internet; **point cloud** is a set of measured 3D points. Treat these as teaching definitions, not confirmed features of every supplied board.

### Gaps

No organizer answers, confirmed event date/location or equipment reservations were supplied. “Next week” is user context, not an exact event date. No external messages have been sent.
