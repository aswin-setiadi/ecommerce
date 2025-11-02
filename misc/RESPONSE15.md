Ah — this is a **classic Kafka networking issue** when running multiple brokers (or restarting containers) with Bitnami images. Let’s carefully unpack what’s happening.

---

## 🔹 The error

```
Requirement failed: Configured endpoints kafka:9092 in advertised listeners are already registered by broker 1002
```

**Meaning:**

* Kafka tracks brokers using their **`broker.id`** (or `KAFKA_BROKER_ID` / `KAFKA_CFG_BROKER_ID`).
* The advertised listener `kafka:9092` is **already registered in Zookeeper** by broker `1002`.
* This usually happens when:

  * You restarted the container **without cleaning old volumes**, and Kafka/ZooKeeper still remembers the old broker.
  * Multiple Kafka containers are trying to use the **same broker ID** on the same network.

---

## 🔹 Common causes

1. **Persistent volumes not cleaned**

   * If you use Bitnami Kafka with a volume:

   ```yaml
   volumes:
     - kafka_data:/bitnami/kafka
   ```

   * Kafka stores its metadata (including broker ID) in that volume.
   * Restarting or re-creating the container **without clearing the volume** can cause this conflict.

2. **Multiple brokers using same broker ID**

   * Bitnami auto-assigns a `broker.id` sometimes.
   * If multiple brokers in the network advertise the same listener (`kafka:9092`) **and same broker ID**, ZooKeeper rejects the second one.

3. **Mixing container names with advertised listeners**

   * If your `KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092`, Kafka registers this name in ZooKeeper.
   * If the container restarts with the same listener but new broker ID, ZK may detect a conflict.

---

## 🔹 How to fix it

### Option 1 — Clean the old Kafka data

```bash
docker-compose down -v
```

* `-v` removes **all associated volumes**, including Kafka/ZooKeeper metadata.
* Then restart:

```bash
docker-compose up -d
```

✅ This works for **single-broker setups** when you don’t need persistent topics.

---

### Option 2 — Explicitly set a broker ID

```yaml
environment:
  - KAFKA_CFG_BROKER_ID=1
  - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092
```

* Make sure **each broker in a multi-broker cluster has a unique `broker.id`**.
* Example for a 2-broker cluster:

```yaml
kafka1:
  environment:
    - KAFKA_CFG_BROKER_ID=1
    - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://kafka1:9092

kafka2:
  environment:
    - KAFKA_CFG_BROKER_ID=2
    - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://kafka2:9092
```

---

### Option 3 — Use different advertised listener names

* If you restart containers frequently for dev, make sure `KAFKA_CFG_ADVERTISED_LISTENERS` matches the container name exactly.
* Avoid hardcoding `kafka:9092` if the broker ID or container changes.

---

### 🔹 TL;DR

| Problem                               | Fix                                                 |
| ------------------------------------- | --------------------------------------------------- |
| Kafka broker conflict in ZooKeeper    | 1. Remove old volumes with `docker-compose down -v` |
| Multiple brokers using same broker ID | 2. Assign unique `KAFKA_CFG_BROKER_ID` per broker   |
| Restarting single broker repeatedly   | 3. Make advertised listener match container name    |

---

💡 **Tip for dev setups:**

If you’re doing local testing with Docker Compose and **don’t care about persistence**, just run:

```bash
docker-compose down -v
docker-compose up -d
```

This clears any old broker registrations in ZooKeeper and avoids this error entirely.

---

If you want, I can write a **complete Kafka + Zookeeper Docker Compose file** that is **restart-safe** and avoids this broker registration conflict for single or multi-broker dev setups.

Do you want me to do that?
