data "template_file" "debian" {
  template = "${file("/home/capri/terraform/files/debian.tpl")}"
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
