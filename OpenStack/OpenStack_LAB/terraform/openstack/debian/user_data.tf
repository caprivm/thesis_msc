data "template_file" "debian" {
  template = file("/home/ubuntu/autoscaling/OpenStack/OpenStack_LAB/terraform/files/debian.tpl")
}

data "template_cloudinit_config" "debian" {
  gzip          = false
  base64_encode = false

  part {
    filename     = "init.cfg"
    content_type = "text/cloud-config"
    content      = data.template_file.debian.rendered
  }
}
