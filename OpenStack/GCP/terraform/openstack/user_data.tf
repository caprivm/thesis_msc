data "template_file" "ubuntu" {
  template = file("/home/jcaviede/autoscaling/OpenStack/GCP/terraform/files/ubuntu.tpl")
}

data "template_cloudinit_config" "ubuntu" {
  gzip          = false
  base64_encode = false

  part {
    filename     = "init.cfg"
    content_type = "text/cloud-config"
    content      = data.template_file.ubuntu.rendered
  }
}
