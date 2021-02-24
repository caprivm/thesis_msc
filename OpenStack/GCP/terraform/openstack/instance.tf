data "openstack_images_image_v2" "ubuntu" {
  name        = "ubuntu"
  most_recent = true
}

resource "openstack_compute_flavor_v2" "m1-medium" {
  name  = "m1-medium"
  ram   = "4096"
  vcpus = "2"
  disk  = "20"
}


resource "openstack_compute_keypair_v2" "symphonyx" {
    name       = "symphonyx"
}

resource "openstack_compute_instance_v2" "ubuntu" {
  name            = "ubuntu"
  image_id        = data.openstack_images_image_v2.ubuntu.id
  flavor_id       = openstack_compute_flavor_v2.m1-medium.id
  key_pair        = openstack_compute_keypair_v2.symphonyx.name
  security_groups = [
    openstack_networking_secgroup_v2.buster.name
  ]
  user_data       = data.template_file.ubuntu.template

  metadata = {
    prometheus = "true"
    node_exporter = "true"
  }

  network {
    name = "test"
  }
}

resource "openstack_networking_floatingip_v2" "ubuntu-fip" {
    pool = "external"
}

resource "openstack_compute_floatingip_associate_v2" "ubuntu-fip" {
    floating_ip = openstack_networking_floatingip_v2.ubuntu-fip.address
    instance_id = openstack_compute_instance_v2.ubuntu.id
}

resource "openstack_networking_secgroup_v2" "buster" {
    name        = "buster"
    description = "Buster Security Group"
}

resource "openstack_networking_secgroup_rule_v2" "node_exporter" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 9100
  port_range_max    = 9100
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.buster.id
}

resource "openstack_networking_secgroup_rule_v2" "ssh" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.buster.id
}

resource "openstack_networking_secgroup_rule_v2" "icmp_v4" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "icmp"
  remote_ip_prefix  = "0.0.0.0/0"
  security_group_id = openstack_networking_secgroup_v2.buster.id
}
