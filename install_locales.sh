#!/bin/bash
set -e

echo "Installing locale support..."
apt-get update
apt-get install -y locales

echo "Generating en_US.UTF-8 locale..."
localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8

echo "Setting environment variables..."
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

echo "Available locales:"
locale -a

echo "Adding locale environment variables to system profile..."
echo 'export LANG=en_US.UTF-8' >> /etc/profile.d/locale.sh
echo 'export LC_ALL=en_US.UTF-8' >> /etc/profile.d/locale.sh
echo 'export LANGUAGE=en_US.UTF-8' >> /etc/profile.d/locale.sh
chmod +x /etc/profile.d/locale.sh

echo "Locale setup complete."