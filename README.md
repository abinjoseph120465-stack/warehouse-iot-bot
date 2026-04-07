\# IoT-Based Warehouse Robot (Prototype)



\## Overview



This project is a prototype warehouse robot that combines line following, obstacle avoidance, IoT telemetry, and a remote camera system.



\## Features



\* Line following using multiple IR sensors

\* Obstacle detection using ultrasonic sensor

\* IoT telemetry using Blynk

\* Remote image capture using ESP32-CAM and Telegram



\## System Architecture



Sensors → Raspberry Pi Pico → Motor Control

↓

Blynk Cloud (Telemetry)



ESP32-CAM ← Serial Trigger ← Pico

↓

Telegram Image Upload



\## Working Principle



\### Line Following



The robot uses 5 sensors (3 analog + 2 digital) to detect the line position. A PD control algorithm adjusts motor speed to follow the path.



\### Obstacle Avoidance



When an obstacle is detected within 15 cm, the robot scans left and right using a servo-mounted ultrasonic sensor and chooses the clearer path.



\### Telemetry



Sensor values and distance data are sent to Blynk for real-time monitoring.



\### Camera System



The ESP32-CAM captures images when triggered via serial communication and sends them to Telegram.



\## Limitations



\* No autonomous navigation (only line following)

\* Obstacle avoidance is based on fixed movements

\* No real-time image processing

\* No CAD-based mechanical design



\## What I Learned



\* Implementation of PD control in embedded systems

\* Sensor calibration and normalization

\* IoT telemetry using Blynk

\* Memory handling issues in ESP32-CAM

\* Serial communication between microcontrollers



\## Images



(Add your images here)



\## Future Improvements



\* Add path planning or SLAM

\* Integrate camera with decision-making

\* Improve obstacle avoidance logic

\* Redesign using CAD and perform CFD analysis



\## Author



Abin Joseph



