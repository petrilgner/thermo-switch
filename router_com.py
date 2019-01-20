#!/usr/bin/python

from librouteros import connect
from librouteros.login import login_plain

ROUTER_API_IP = "192.168.11.1"

api = connect(host=ROUTER_API_IP, username='admin', password='***', port=8728)
method = (login_plain, )


def change_ip(new_ip):
    params = {'comment': 'ThermoDST'}
    out = api(cmd='/ip/firewall/nat/print')
    for entry in out:
        if 'comment' in entry:
            if entry['comment'] == 'ThermoDST':
                params = {'to-addresses': new_ip, '.id': entry['.id']}
                api(cmd='/ip/firewall/nat/set', **params)

            if entry['comment'] == 'ThermoSRC':
                params = {'dst-address': new_ip, '.id': entry['.id']}
                api(cmd='/ip/firewall/nat/set', **params)


