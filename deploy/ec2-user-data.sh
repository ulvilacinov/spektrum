#!/bin/bash
# Paste into "Advanced details → User data" when launching the EC2 instance (Ubuntu 24.04).
# Installs Docker and the AWS CLI, adds swap for the small instance, prepares /opt/spektrum.
set -eux
export DEBIAN_FRONTEND=noninteractive

curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
systemctl enable --now docker
snap install aws-cli --classic

if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

mkdir -p /opt/spektrum
chown ubuntu:ubuntu /opt/spektrum
touch /opt/spektrum/.ready
