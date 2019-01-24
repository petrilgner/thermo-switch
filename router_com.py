#!/usr/bin/python

from librouteros import connect
import config


def change_ip(new_ip):
    api = connect(host=config.ROUTER_API_IP, username=config.ROUTER_API_USER, password=config.ROUTER_API_PASSWORD, port=config.ROUTER_API_PORT)
    out = api(cmd='/ip/firewall/nat/print')
    for entry in out:
        if 'comment' in entry:
            if entry['comment'] == config.ROUTER_DST_COMMENT:
                params = {'to-addresses': new_ip, '.id': entry['.id']}
                api(cmd='/ip/firewall/nat/set', **params)

            if entry['comment'] == config.ROUTER_SRC_COMMENT:
                params = {'dst-address': new_ip, '.id': entry['.id']}
                api(cmd='/ip/firewall/nat/set', **params)


