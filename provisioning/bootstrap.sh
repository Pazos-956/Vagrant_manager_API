#!/bin/bash

sudo apt-get update

# Instalar FastApi
sudo apt-get install -y python3-pip sqlite3
pip install "fastapi[standard]" "python-vagrant" Jinja2 sqlmodel

sudo systemctl stop networkd-dispatcher.service unattended-upgrades.service

# Instalar VirtualBox
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox-2016.gpg] https://download.virtualbox.org/virtualbox/debian jammy contrib" | sudo tee -a /etc/apt/sources.list
wget -O- https://www.virtualbox.org/download/oracle_vbox_2016.asc | sudo gpg --yes --output /usr/share/keyrings/oracle-virtualbox-2016.gpg --dearmor
sudo apt-get -y update
sudo apt-get -y install virtualbox-7.1

# Instalar KVM
sudo apt-get -y install bridge-utils cpu-checker libvirt-clients libvirt-daemon qemu qemu-kvm libvirt-daemon-system

# Instalar Vagrant ultima version y plugins
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt -y update && sudo apt install -y vagrant
sudo su vagrant vagrant plugin install vagrant-hostmanager
sudo su vagrant vagrant plugin install vagrant-vbguest

# Cambio variable de entorno
if [[ ! $(grep "TERM=xterm" ".profile") ]]; then
 # Inserir as linhas iniciais 
 echo >> .profile
 echo "# TERM" >> .profile
else
 # Eliminar as entradas de execucions previas
 sed -i "/TERM=xterm/d" .profile
fi
echo "export TERM=xterm" >> .profile

sudo systemctl start networkd-dispatcher.service unattended-upgrades.service

mkdir /home/vagrant/users
chown vagrant:vagrant /home/vagrant/users
