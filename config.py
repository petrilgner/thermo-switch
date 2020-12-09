LISTEN_IP = "172.20.1.10"
LISTEN_PORT = 5000

# Thermostats config
DATA_VALIDITY_SEC = 10
DEVICES = {
    "MalySal": {'ip': "172.20.9.10", 'display': "Malý sál"},
    "KingarnaP": {'ip': "172.20.9.11", 'display': "Přední Kingárna"},
    "KingarnaZ": {'ip': "172.20.9.12", 'display': "Zadní Kingárna"},
    # "Klubovna": {'ip': "172.20.9.14", 'display': "Klubovna"}

}
PORT_NUM = 4000
LOGIN_HEX = "10626a62323030fdfe0d0a"

MESSAGE = ""
MESSAGE_CLOSE = True

# Router Config
ROUTER_API_IP = "172.20.1.1"
ROUTER_API_PORT = 8728
ROUTER_API_USER = "admin"
ROUTER_API_PASSWORD = "branabjb"
ROUTER_DST_COMMENT = "ThermoDST"
ROUTER_SRC_COMMENT = "ThermoSRC"

# Stats Mysql Config
STATS_ENABLED = True
STATS_INTERVAL = 5 * 60
MYSQL_HOST = "localhost"
MYSQL_DB = "thermo_stats"
MYSQL_USER = "thermo_stats"
MYSQL_PASSWORD = "Thrbajb.741"
