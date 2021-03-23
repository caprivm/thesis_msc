#!/bin/bash

cd ~/autoscaling/OpenStack/OpenStack_LAB/terraform/scaling/debian
sudo terraform init 
sudo terraform apply -auto-approve
sleep 15
