import logging
import os
import random
import time

import redis
from flask import Flask, jsonify, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

APP_REVISION = os.environ.get("APP_REVISION", "v1")
# Injected by the deploy pipeline. A healthy deploy sets an integer (e.g. "50").
# A bad deploy can inject a non-integer value here.
MAX_CART_ITEMS_RAW = os.environ.get("MAX_CART_ITEMS", "50")

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [rev={APP_REVISION}] %(levelname)s %(message)s",
)
log = logging.getLogger("checkout-api")

app = Flask(__name__)
rdb = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=1)

# ---- Metrics --------------------------------------------------------------
REQUESTS = Counter(
    "checkout_requests_total", "Total checkout requests", ["status"]
)
LATENCY = Histogram(
    "checkout_latency_seconds", "Checkout request latency in seconds"
)
INFO = Gauge("checkout_app_info", "Deployed app info", ["revision"])
INFO.labels(revision=APP_REVISION).set(1)


def _seed_inventory():
    try:
        if not rdb.exists("inventory:sku-1001"):
            rdb.set("inventory:sku-1001", 500)
        log.info("connected to inventory store, seed ok")
    except Exception as exc:  # noqa: BLE001
        log.error("could not reach inventory store: %s", exc)


@app.route("/")
def health():
    return jsonify(status="ok", revision=APP_REVISION)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    start = time.time()
    try:
        cart_items = int(request.args.get("items", random.randint(1, 5)))

        # Guardrail: reject carts larger than the configured maximum.
        # MAX_CART_ITEMS is provided by the deploy pipeline as config.
        max_items = int(MAX_CART_ITEMS_RAW)

        if cart_items > max_items:
            REQUESTS.labels(status="rejected").inc()
            return jsonify(error="cart too large"), 422

        stock = rdb.decrby("inventory:sku-1001", cart_items)
        if stock < 0:
            rdb.incrby("inventory:sku-1001", cart_items)
            REQUESTS.labels(status="rejected").inc()
            return jsonify(error="out of stock"), 409

        REQUESTS.labels(status="ok").inc()
        return jsonify(status="confirmed", items=cart_items, stock_left=stock)
    except Exception as exc:  # noqa: BLE001
        REQUESTS.labels(status="error").inc()
        log.error("checkout failed: %s: %s", type(exc).__name__, exc)
        return jsonify(error="internal server error"), 500
    finally:
        LATENCY.observe(time.time() - start)


@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    log.info("starting checkout-api revision=%s max_cart_items=%r",
             APP_REVISION, MAX_CART_ITEMS_RAW)
    _seed_inventory()
    app.run(host="0.0.0.0", port=8080)
