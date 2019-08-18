qvibe-analyser
==============

.. image:: https://travis-ci.org/3ll3d00d/qvibe-analyser.svg?branch=master
   :target: https://travis-ci.org/3ll3d00d/qvibe-analyser
   :alt: Continuous Integration

.. image:: https://codecov.io/gh/3ll3d00d/qvibe-analyser/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/3ll3d00d/qvibe-analyser
   :alt: Code Coverage

.. image:: https://landscape.io/github/3ll3d00d/qvibe-analyser/master/landscape.svg?style=flat
   :target: https://landscape.io/github/3ll3d00d/qvibe-analyser/master
   :alt: Code Health

.. image:: https://readthedocs.org/projects/qvibe-analyser/badge/?version=latest
   :target: http://qvibe.readthedocs.io/en/latest/
   :alt: readthedocs


An vibration measurement app for the RPI.

recorder setup
==============

Follow https://vibe.readthedocs.io/en/latest/install.html for the rpi setup, i.e. complete these sections up to
the vibe-recorder setup

ssh into your rpi and::

    $ ssh pi@myrpi
    $ sudo apt install python3 python3-venv python3-pip libyaml-dev git
    $ mkdir python
    $ cd python
    $ python3 -m venv qvibe
    $ cd qvibe
    $ . bin/activate
    $ pip install git+https://github.com/3ll3d00d/qvibe-recorder

(Optional) Starting vibe-recorder on bootup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is optional but recommended, it ensures the recorder app starts automatically whenever the rpi boots up and makes
sure it restarts automatically if it ever crashes.

We will achieve this by creating and enabling a `systemd`_ service.

1) Create a file qvibe.service in the appropriate location for your distro (e.g. ``/etc/systemd/system/`` for debian)::

    [Unit]
    Description=qvibe
    After=network.target

    [Service]
    Type=simple
    User=myuser
    WorkingDirectory=/home/pi
    ExecStart=/home/pi/python/qvibe/bin/qvibe-recorder
    Restart=always
    RestartSec=1

    [Install]
    WantedBy=multi-user.target

2) enable the service and start it up::

    $ sudo systemctl enable qvibe.service
    $ sudo service qvibe start
    $ sudo journalctl -u qvibe.service
    -- Logs begin at Sat 2019-08-17 12:17:02 BST, end at Sun 2019-08-18 21:58:43 BST. --
    Aug 18 21:58:36 swoop systemd[1]: Started qvibe.
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,345 - qvibe.app - WARNING - create_device - Loading smbus 1
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,350 - qvibe.app - WARNING - create_device - Loading mpu6050 mpu6050/500
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,354 - qvibe.mpu6050 - WARNING - set_accelerometer_sensitivity - Set accelerometer sensitivity = 2.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,355 - qvibe.mpu6050 - WARNING - set_gyro_sensitivity - Set gyro sensitivity = 500.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,356 - qvibe.mpu6050 - WARNING - set_sample_rate - Set sample rate = 500.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,893 - qvibe.mpu6050 - WARNING - set_accelerometer_sensitivity - Set accelerometer sensitivity = 2.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,894 - qvibe.mpu6050 - WARNING - set_gyro_sensitivity - Set gyro sensitivity = 500.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,897 - qvibe.accelerometer - WARNING - run - Running
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,907 - qvibe.mpu6050 - WARNING - set_accelerometer_sensitivity - Set accelerometer sensitivity = 2.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,909 - qvibe.mpu6050 - WARNING - set_gyro_sensitivity - Set gyro sensitivity = 500.0
    Aug 18 21:58:37 swoop qvibe-recorder[2224]: 2019-08-18 21:58:37,910 - qvibe.mpu6050 - WARNING - set_sample_rate - Set sample rate = 500.0

3) reboot and repeat step 2 to verify the recorder has automatically started
