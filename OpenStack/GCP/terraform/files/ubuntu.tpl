#cloud-config
packages:
 - prometheus-node-exporter
password: orion
chpasswd: { expire: False }
ssh_pwauth: True
