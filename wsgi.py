import uwsgi

from config import STATS_INTERVAL, STATS_ENABLED
from server import app, write_stats, init_thermos

init_thermos()

# setup updater signal
if STATS_ENABLED:
    write_stats()
    uwsgi.register_signal(99, "", write_stats)
    uwsgi.add_timer(99, STATS_INTERVAL)

if __name__ == "__main__":
    app.run()
