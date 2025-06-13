#!/usr/bin/env bash
set -eux
exec ansible-playbook -i inventory.ini playbook.yaml
