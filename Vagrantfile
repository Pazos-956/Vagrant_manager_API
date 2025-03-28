# -*- mode: ruby -*-
# vi: set ft=ruby :
# Preguntar
# require_relative 'provisioning/vbox.rb'
# VBoxUtils.check_version('7.1.6')
# Vagrant.require_version ">= 2.4.3"


HOSTNAME_VM="Manager-API"
CPU=4
MEM=4096

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.box_version = "20241002.0.0"
  config.vm.box_check_update = false
  config.vm.hostname = HOSTNAME_VM

  # Configure hostmanager and vbguest plugins
  config.hostmanager.enabled = true
  config.hostmanager.manage_host = true
  config.hostmanager.manage_guest = true
  config.vbguest.auto_update = false

  config.vm.network "private_network", ip: "192.168.60.10"
  config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.network "forwarded_port", guest: 8000, host: 8000

  config.vm.provider "virtualbox" do |vbox,  override|
    vbox.customize ['modifyvm', :id, '--nested-hw-virt', 'on']
    vbox.name = "TFG-VM-API"
    vbox.cpus = CPU
    vbox.memory = MEM
    vbox.gui = false
  end
  config.vm.provision "global", type: "shell", run: "once", path: "provisioning/bootstrap.sh"
end
