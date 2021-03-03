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
  name            = "debian-buster-scaling"
  image_id        = data.openstack_images_image_v2.debian-buster.id
  flavor_id       = data.openstack_compute_flavor_v2.m1-micro.id
  security_groups = [
    data.openstack_networking_secgroup_v2.buster.name
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
    address  = "10.80.81.191"
}


resource "openstack_compute_floatingip_associate_v2" "debian-buster-fip" {
    floating_ip = data.openstack_networking_floatingip_v2.debian-buster-fip.address
    instance_id = openstack_compute_instance_v2.debian-buster.id
}

data "openstack_networking_secgroup_v2" "buster" {
    name        = "buster"
}
