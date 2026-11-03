# What the equipment does

The [two-page inventory](source/Hackathon%20Hardware%20Details.pdf) promises the baseline kit below and lists the remaining equipment as **shared checkout hardware**. It gives categories, not most model numbers. Integrations require matching voltage, connectors, drivers and availability.

## The baseline kit

| Equipment | Simple description | Useful role and connections |
|---|---|---|
| Raspberry Pi 5, 16 GB | A small Linux computer; RAM holds running programs | Main coordinator: receive readings over USB, store events, run a web dashboard and process images |
| 26 TOPS AI accelerator | A specialized processor for supported trained models; TOPS means trillions of operations per second | Accelerated vision if the model/runtime matches. The rating resembles Hailo-8 AI HAT+, but the identity is unconfirmed; it does not promise arbitrary models or chatbot support |
| Storage | Persistent space for the operating system and files | Keep code, models, logs and image evidence locally; medium and capacity unspecified |
| Power supply | Supplies the board's required voltage and current | Powers fixed operation; batteries and motors require their own compatibility checks |
| Arduino-compatible microcontroller | A small controller repeatedly running a firmware program | Read sensors and control simple outputs; USB serial provides an easy link to the Pi |
| Grove expansion shield | A board of convenient sensor connectors | Connect compatible modules to the correct analog, digital, I2C or UART port |
| Grove 40-in-1 kit | A collection of modular sensors and actuators | Start with one known input and one output. The PDF does not identify the 40 modules |
| Development accessories | Interconnect and prototyping parts | Connect the boards and modules; check pinout, polarity and voltage rather than plug shape alone |

Pi GPIO uses **3.3 V logic and is not 5 V tolerant**. A Grove connector does not guarantee the correct voltage or protocol. Start with USB between the controller and Pi where possible. [Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html), [Grove system](https://wiki.seeedstudio.com/Grove_System/), [AI HAT comparison](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html)

## Additional computing

| Shared item | What it is | Possible use and integration |
|---|---|---|
| Raspberry Pi Zero | Smaller, less powerful Linux computer | Lightweight logging or remote camera node. Zero variants differ; “Zero” alone does not guarantee Wi-Fi or a 64-bit processor |
| ESP32 | Microcontroller family with model-dependent wireless features | Wireless sensor node feeding the Pi; inspect the exact variant before choosing Wi-Fi/Bluetooth features or board package |
| Arduino | Additional microcontrollers | Put a controller near each sensor or motor group; forward readings to the main computer |
| NVIDIA Jetson | Linux computer with NVIDIA GPU acceleration | More demanding vision/robotics; use its supported JetPack image and vendor examples |
| Other embedded boards | Unspecified computers or controllers | Potential alternate nodes; identify the board before choosing software |

Sources: [Pi Zero](https://www.raspberrypi.com/products/raspberry-pi-zero/), [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/index.html), [Arduino pins](https://docs.arduino.cc/learn/microcontrollers/digital-pins/), [JetPack supported hardware](https://developer.nvidia.com/embedded/jetpack/downloads).

## Cameras, infrared and distance

| Shared item | What it senses | Useful integration and limit |
|---|---|---|
| Standard camera | Ordinary images/video | USB or CSI → Pi/Jetson → candidate-person detection and evidence |
| Wide-angle camera | A broader image of a scene | More coverage for a fixed node or robot; distant subjects occupy fewer pixels for a given resolution |
| Low-light / NoIR camera | Dim-scene imagery / near-infrared light | A compatible illuminator can help in darkness. NoIR is not thermal imaging and creates no illumination by itself |
| AI-enabled camera | Images plus onboard inference, depending on model | Feed detections to the Pi; camera-specific toolchain can differ from the Pi's accelerator |
| Depth camera | Distance at many image locations | Estimate range to a visible object or obstacles; requires matching SDK and calibration |
| Thermal imaging camera | Emitted infrared energy represented as thermal contrast | Compare warm regions with visible imagery. It cannot see through walls; ordinary glass obstructs typical long-wave thermal imaging |
| Infrared sensor | Module-dependent IR light, proximity or temperature | Small trigger or temperature measurement; the category does not guarantee a thermal image |
| 2D LiDAR | Distances in a scanning plane | Robot obstacle map; objects outside the scan plane can be missed |
| 3D LiDAR | Spatial samples forming a point cloud | Map geometry or routes; points do not automatically classify people |
| Time-of-flight sensor | Distance from reflected light timing | Small obstacle/clearance sensor; range depends on device and scene |
| Ultrasonic rangefinder | Distance from a sound echo | Simple rover obstacle detection via microcontroller; soft/angled surfaces and mounting affect echoes |

Camera connections and model capabilities: [Pi camera documentation](https://www.raspberrypi.com/documentation/accessories/camera.html), [AI Camera example](https://www.raspberrypi.com/documentation/accessories/ai-camera.html). Thermal limits: [FLIR](https://www.flir.com/en-gb/discover/home-outdoor/can-thermal-imaging-see-through-walls/). Distance examples, not supplied-model promises: [Ouster LiDAR](https://docs.ouster.com/sensor-docs/overview/welcome), [ST time-of-flight](https://www.st.com/en/imaging-and-photonics-solutions/vl53l1X), [Grove ultrasonic](https://wiki.seeedstudio.com/Grove-Ultrasonic_Ranger/).

## Position and movement

| Shared item | Simple description | Use and limitation |
|---|---|---|
| GPS/GNSS receiver | Satellite-based position/time receiver; GPS is one GNSS constellation | Geotag the receiver outdoors. It does not locate an uninstrumented victim; indoor and obstructed fixes degrade |
| Positioning module | General term for location hardware | Could be GNSS, UWB or something else; identify it first |
| IMU | Combined motion sensors, usually accelerometer and gyroscope | Robot/camera orientation and motion estimates; requires calibration and fusion |
| Accelerometer | Measures acceleration, including gravity's effect | Tilt, vibration and movement cues; does not directly report position |
| Gyroscope | Measures rotation rate | Stabilization and orientation tracking; accumulated bias causes drift |
| Magnetometer | Measures magnetic field | Compass heading after calibration; nearby metal/electronics can distort it |
| mmWave radar | High-frequency radio sensing; capabilities depend on module | Suitable modules estimate presence, range, velocity or angle. Specialized vital-sign demos do not establish rescue performance through rubble |
| Doppler radar | Detects motion from frequency changes | Wake a camera or flag movement; basic modules do not necessarily measure distance |
| PIR motion sensor | Detects changes in infrared energy | Low-power movement trigger; not a camera or reliable stationary-person detector |

Sources: [GPS limitations](https://www.gps.gov/gps-accuracy-0), [inertial navigation drift](https://rotations.berkeley.edu/strapdown-inertial-navigation/), [TI mmWave training](https://www.ti.com/video/series/mmwave-training-series.html), [Doppler module example](https://wiki.seeedstudio.com/Grove-Doppler-Radar/), [PIR explanation](https://learn.adafruit.com/pir-passive-infrared-proximity-motion-sensor).

## Communications

| Shared item | Simple description | Integration and constraint |
|---|---|---|
| Software-defined radio (SDR) | Radio with software-configurable signal processing | USB samples → GNU Radio for a specific RF experiment. Receive/transmit capability and drivers depend on hardware; it is not a ready-made emergency network |
| Wi-Fi adapter | Local wireless network interface | Dashboard, images and control over a local access point. Internet is optional; access-point mode needs driver support |
| Bluetooth | Nearby device/peripheral radio link | Phone setup or sensor connection; Bluetooth Classic/BLE roles vary |
| LoRa | Low-rate radio physical layer | Compact alerts between compatible radios. It does not itself supply LoRaWAN, mesh routing or a dashboard |
| UWB ranging | Precise radio timing between compatible endpoints | Range to a tag; positioning requires appropriate anchors/geometry or supported angle methods. It does not locate arbitrary untagged people |
| Other wireless modules | Unspecified radios | Verify frequency, antenna, protocol, firmware and permitted configuration before planning an integration |

References: [SDR example](https://www.greatscottgadgets.com/hackrf/one/), [local Pi networking](https://www.raspberrypi.com/documentation/computers/configuration.html), [LoRa explanation](https://www.semtech.com/lora/what-is-lora), [Qorvo UWB](https://www.qorvo.com/products/wireless-connectivity/ultra-wideband). See the [crash course](crash-course.md) for the different network layers.

## Environmental and acoustic sensing

| Shared item | What it measures or does | Useful role and limitation |
|---|---|---|
| Temperature | Heat-related measurement at a specified sensor/target | Flag environmental changes; ambient, contact and infrared modules measure different things |
| Humidity | Water vapor, often relative humidity | Context for conditions and compensation of other readings |
| Pressure | Air pressure | Environmental context or relative altitude clues; not a standalone indoor positioning system |
| Gas | Response to selected chemicals | Conditional hazard-change demonstration; species, cross-sensitivity, warm-up and calibration are essential |
| Air quality | Device-specific particle, VOC or gas metric | Show the actual metric and unit; avoid translating it into a universal “safe air” judgment |
| Light | Incident light level | Detect lighting loss or adapt an indicator/camera; raw values may not be calibrated lux |
| Other environmental sensors | Unspecified probes | Inventory first; oxygen, radiation, water and flame sensors are not specifically promised |
| Microphone | Converts sound into a signal | Record calls or classify sounds; USB, I2S and analog inputs differ. One microphone is not a directional array |
| Speaker | Converts an amplified audio signal into sound | Local alarm/instructions; use an appropriate output/amplifier, not bare GPIO |
| Acoustic sensor | Broad category including sound level or vibration | Trigger closer inspection; may not provide a usable audio waveform |
| Audio processing module | Preprocesses microphone signals | Noise reduction, voice activity or direction cues if supported; array layout/firmware matter |

Sources: [Seeed sensor catalog](https://wiki.seeedstudio.com/Sensor_Network/), [Sensirion environmental example](https://sensirion.com/products/catalog/SVM30), [gas sensor design considerations](https://sensirion.com/media/documents/45B45DA4/66D9B5CD/TC_AN_STC31-C_Design_Guide_D1.pdf), [Seeed audio example](https://wiki.seeedstudio.com/respeaker_xvf3800_xiao_getting_started/). No named gas module or calibration is supplied in the PDF.

## Robots, drones and actuators

| Shared item | What it does | Practical integration |
|---|---|---|
| Wheeled robot | Moves on wheels | Carry camera/sensors on suitable ground; use its existing motor controller and SDK |
| Tracked robot | Moves on continuous tracks | Potential uneven-surface carrier; payload and terrain capability remain unknown |
| Legged robot | Moves with articulated legs | Inspection platform if working locomotion APIs exist; do not start by writing balance control |
| Robotic arm | Positions an end effector through several joints | Aim sensors or manipulate a demonstration object; requires kinematics/controller support |
| Mobile robotics development kit | Packaged robot platform | Start from the vendor's known-good motion and sensing example |
| Programmable microdrone | Small aircraft with some software interface | Controlled scouting demo; API, radio, payload and positioning vary |
| FPV drone | Aircraft giving a pilot a first-person video view | Human-guided inspection. FPV does not guarantee programmability or MAVLink |
| Drone development platform | Aircraft/autopilot intended for experimentation | Match actual flight controller and firmware to PX4/MAVSDK or another supported ecosystem |
| DC motor | Rotates when powered | Drive wheels via a suitable motor driver; never power directly from GPIO |
| Servo | Commonly moves to a commanded angle | Aim a sensor; verify whether positional or continuous-rotation and its power requirement |
| Motor controller | Supplies motor power in response to commands | Match voltage/current including startup/stall demand; control may be PWM, serial or a bus |
| Pan-tilt mechanism | Two axes for aiming a payload | Point a camera at a detected region or sound cue; calibrate mounting geometry |
| Other actuators | Cause a physical change | Identify power and control needs individually |

No particular robot/drone model is promised. Example ecosystems: [PX4 flight controllers](https://docs.px4.io/main/en/flight_controller/), [Bitcraze](https://www.bitcraze.io/documentation/system/). Basic actuation: [Adafruit motor control](https://learn.adafruit.com/adafruit-raspberry-pi-lesson-9-controlling-a-dc-motor?view=all), [actuator types](https://learn.adafruit.com/use-dc-stepper-servo-motor-solenoid-rp2040-pico). Begin with teleoperation and a lost-link stop; any flight demonstration depends on event permission and the platform's procedures.

## Prototyping, debugging and assembly

| Shared item | What it is for | Where it helps |
|---|---|---|
| Breadboard | Temporary solderless circuit connections | Test a small circuit before making permanent joints |
| Jumper wires | Short reusable connections | Join headers/breadboard points; document the pin map |
| Connectors | Detachable joins | Modular sensor and power wiring; verify pinout |
| Resistors | Limit current or establish electrical states | LED current limit and required pull-up/down connections |
| LEDs | Small indicator lights | Show power, status or alerts with appropriate current limiting |
| Switches | Manually open/close a connection | Test, SOS or acknowledgment input; handle contact bounce |
| Other components | Unspecified circuit parts | Determine ratings and purpose before use |
| Multimeter | Measures voltage, current, resistance and continuity | Check supply voltage and broken connections first |
| Oscilloscope | Displays voltage over time | Inspect noisy power, pulses and electrical signal quality |
| Logic analyzer | Records digital signal timing | Decode I2C/SPI/UART and find protocol faults |
| USB serial adapter | Connects host USB to a serial port | Console logs or UART sensors; TTL UART voltage and RS-232 are not interchangeable |
| Bench power supply | Adjustable lab power source | Controlled bring-up at the specified voltage/current limit |
| Soldering station and solder | Heated tool and metal alloy for permanent joints | Secure a circuit after its temporary version works |
| Wire | Carries power/signals | Choose gauge and insulation for the load and mounting |
| Heat-shrink tubing | Insulating sleeve that shrinks with heat | Cover exposed splices |
| Crimping tools | Attach matching terminals mechanically | Make detachable, reliable leads |
| Hand tools and assembly supplies | Cutters, drivers and mounting materials | Secure boards and strain-relieve cables |
| Portable monitor | Local screen | Pi/Jetson setup or responder display; confirm video connector |
| USB hub | Adds USB ports | More peripherals; total bandwidth and power are still limited |
| Extra power supplies | Electrical sources for peripherals/boards | Match voltage, polarity, current and grounding requirements |
| Batteries | Stored energy | Mobile/outage operation; measure runtime under actual load and use compatible regulation/charging |
| Cables and adapters | Physical interconnects | Data-capable USB, correct camera ribbon, Ethernet and display connections |

These are generic tool functions, not device-specific operating instructions. Useful primers: [breadboards](https://learn.adafruit.com/breadboards-for-beginners/breadboard-usage), [LED resistors](https://learn.adafruit.com/all-about-leds/revisiting-resistors), [multimeters](https://learn.adafruit.com/multimeters/overview), [logic analyzer versus oscilloscope](https://articles.saleae.com/logic-analyzers/logic-analyzer-vs.-oscilloscope), [soldering tools](https://learn.adafruit.com/adafruit-guide-excellent-soldering/tools), [Pi setup/power](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## Three integrations worth understanding first

1. **Baseline sensing:** Grove module → controller → USB → Pi → local incident board.
2. **Vision extension:** compatible camera → local model → candidate detection plus evidence → human review. Compact summaries can go over a separate radio.
3. **Mobile inspection:** camera/sensors → onboard computer; high-level commands → motor controller → motors. Position and range sensors supply context, not automatic autonomy.

No range, battery endurance, detection accuracy, calibrated hazard threshold or ruggedness has been established. The [preflight checklist](../04-software/preflight-checklist.md) turns those unknowns into concrete arrival checks.
