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
        python3.9 \
        python3.9-dev \
        python3.9-distutils \
        python3.11 \
        python3.11-dev

sudo rm -rf /var/lib/apt/lists/*

export LANG=en_US.UTF-8
sudo update-locale
sudo locale-gen $LANG

sudo python3 -m pip install -U pip tox virtualenv
