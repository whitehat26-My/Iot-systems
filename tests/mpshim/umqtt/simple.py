"""Stand-in for MicroPython's umqtt.simple, backed by paho on the PC.

Lets the real firmware's publish path run against a real broker, so a mismatch
between the topics the node sends and the topics the collector parses shows up
here instead of on hardware day.
"""

import paho.mqtt.client as _mqtt


class MQTTClient:
    def __init__(self, client_id, server, port=1883, keepalive=60, **kw):
        self.server, self.port, self.keepalive = server, port, keepalive
        self._c = _mqtt.Client(
            _mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id if isinstance(client_id, str) else client_id.decode(),
        )
        self.sent = []

    def set_last_will(self, topic, msg, retain=False, qos=0):
        self._c.will_set(topic, msg, qos=qos, retain=retain)

    def connect(self):
        self._c.connect(self.server, self.port, keepalive=self.keepalive)
        self._c.loop_start()

    def publish(self, topic, msg, retain=False, qos=0):
        t = topic.decode() if isinstance(topic, bytes) else topic
        m = msg.decode() if isinstance(msg, bytes) else msg
        self.sent.append((t, m))
        self._c.publish(t, m, qos=1, retain=retain).wait_for_publish(timeout=5)

    def disconnect(self):
        self._c.loop_stop()
        self._c.disconnect()
