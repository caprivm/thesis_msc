#cloud-config
packages:
 - prometheus-node-exporter
password: debian
chpasswd: { expire: False }
ssh_pwauth: True
