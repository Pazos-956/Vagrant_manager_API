# Troubleshooting
* Si libvirt no es capaz de conectar a libvirt-sock, comprueba que libvirtd.service está activo.
* Si en libvirt sale el mensaje:
_no polkit agent available to authenticate action 'org.libvirt.unix.manage'_, comprueba que el usuario usando vagrant pertenece al grupo _libvirt_.
* Si en vmware_desktop sale el mensaje: _The VMware "vmnet" devices are failing to start_ , comprueba que vmware-networks.service está activo.
