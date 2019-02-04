import thermo

thermo = thermo.Thermo('192.168.11.4', 'FEKT')
thermo.set_debug()
thermo.connect()
print(thermo.get_status_data())
print(thermo.get_status_data())
thermo.disconnect()
