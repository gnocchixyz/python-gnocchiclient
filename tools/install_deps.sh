#!/bin/bash -ex

sudo apt-get update -y && sudo apt-get install -qy gnupg software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update -y && sudo apt-get install -qy \
        locales \
        git \
        wget \
        curl \
        python3 \
        python3-dev \
        python3-pip \
        python3.10 \
        python3.10-dev \
        python3.10-distutils \
        python3.11 \
        python3.11-dev \
        python3.11-distutils \
        tox

sudo rm -rf /var/lib/apt/lists/*

export LANG=en_US.UTF-8
sudo update-locale
sudo locale-gen $LANG

sudo python3 -m venv /tmp/gnocchi-tox-env
sudo /tmp/gnocchi-tox-env/bin/python3 -m pip install -U pip tox virtualenv
