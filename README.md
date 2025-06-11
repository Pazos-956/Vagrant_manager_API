# Preparación
* Para iniciar vmware asegurarse de que está iniciado `vmware-networks-configuration.service` y `vmware-networks.service`.
También tener cargados los módulos de vmware `modprobe -a vmw_vmci vmmon`
# Troubleshooting
* Si libvirt no es capaz de conectar a libvirt-sock, comprueba que libvirtd.service está activo.
* Si en libvirt sale el mensaje:
_no polkit agent available to authenticate action 'org.libvirt.unix.manage'_, comprueba que el usuario usando vagrant pertenece al grupo _libvirt_.
* Si en vmware_desktop sale el mensaje: _The VMware "vmnet" devices are failing to start_ , comprueba que vmware-networks.service está activo.
* En caso de que no funcione vmware en arch o distribuciones basadas en este: (Esto es lo que me funcionó)

    * Desisnstalar y las aplicaciones:
    
        - open-vm-tools
        - vagrant-vmware-utility-bin
        - vmware-keymaps
        - vmware-workstation
    * Borrar la carpeta /etc/vmware.
    * Reinstalar las aplicaciones anteriores.
    * en /etc/systemd/system/vagrant-vmware-utility.service sustituir ExecStart por: 
    `ExecStart=/opt/vagrant-vmware-desktop/bin/vagrant-vmware-utility api -config-file=/opt/vagrant-vmware-desktop/config/service.hcl -license-override professional`
    * Instalar el plugin de vagrant-vmware-desktop.
    * Reiniciar la máquina.
    * Iniciar los servicios vmware-networks-configuration, vmware-networks, vmware-usbarbitrator.
    - [vagrant-vmware-desktop snapshot error (ExecStart)](https://github.com/hashicorp/vagrant-vmware-desktop/issues/91#issuecomment-1631463671)
    - [Install vmware EndeavourOS](https://forum.endeavouros.com/t/vmware-workstation/67906/3)


