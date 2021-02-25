#cloud-config
package_upgrade: true

packages:
 - prometheus-node-exporter

password: orion
chpasswd: { expire: False }
ssh_pwauth: True

runcmd:
 - [ sh, -c, 'echo "nameserver 8.8.8.8" >> /etc/resolv.conf' ]
 - sudo apt update && sudo apt install apache2
 - systemctl restart apache2
