provider "openstack" {
}

data "openstack_images_image_v2" "debian-buster" {
  name        = "debian10"
  most_recent = true
}

data "openstack_compute_flavor_v2" "m1-micro" {
  name  = "magma-agw"
}

resource "openstack_compute_instance_v2" "debian-buster" {
  name            = "debian-buster"
  image_id        = data.openstack_images_image_v2.debian-buster.id
  flavor_id       = data.openstack_compute_flavor_v2.m1-micro.id
  security_groups = [
    openstack_networking_secgroup_v2.buster.name
  ]
  user_data       = data.template_file.debian.template

  metadata = {
    prometheus = "true"
    node_exporter = "true"
  }

  network {
    name = "SGI_ORAN"
  }
}

data "openstack_networking_floatingip_v2" "debian-buster-fip" {
    address  = "10.80.81.165"
}


resource "openstack_compute_floatingip_associate_v2" "debian-buster-fip" {
    floating_ip = data.openstack_networking_floatingip_v2.debian-buster-fip.address
    instance_id = openstack_compute_instance_v2.debian-buster.id
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