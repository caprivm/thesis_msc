data "openstack_images_image_v2" "debian-buster" {
  name        = "debian-buster"
  most_recent = true
}

resource "openstack_compute_flavor_v2" "m1-micro" {
  name  = "m1.micro"
  ram   = "512"
  vcpus = "1"
  disk  = "5"
}


resource "openstack_compute_keypair_v2" "symphonyx" {
    name       = "symphonyx"
}

resource "openstack_compute_instance_v2" "debian-buster" {
  name            = "debian-buster"
  image_id        = data.openstack_images_image_v2.debian-buster.id
  flavor_id       = openstack_compute_flavor_v2.m1-micro.id
  key_pair        = openstack_compute_keypair_v2.symphonyx.name
  security_groups = [
    openstack_networking_secgroup_v2.buster.name
  ]
  user_data       = data.template_file.debian.template

  metadata = {
    prometheus = "true"
    node_exporter = "true"
  }

  network {
    name = "test"
  }
}

resource "openstack_networking_floatingip_v2" "debian-buster-fip" {
    pool = "external"
}

resource "openstack_compute_floatingip_associate_v2" "debian-buster-fip" {
    floating_ip = openstack_networking_floatingip_v2.debian-buster-fip.address
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
