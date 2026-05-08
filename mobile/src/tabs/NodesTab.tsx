import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  Platform,
} from "react-native";
import { getDevices, getBursts, getHealth } from "../services/api";
import C from "../constants/colors";

// ── Known node roles ──────────────────────────────────────────────
const NODE_LABEL: Record<string, string> = {
  leaf: "NODE 1 — TRIGGER",
  sensor: "NODE 2A — SENSORS",
  pi: "NODE 3 — RELAY PI",
  command_center: "NODE 4 — BACKEND",
  relay: "RELAY",
};

function timeSince(iso: string | null) {
  if (!iso) return "never";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

function statusColor(device: any) {
  if (!device?.is_active) return C.textDim;
  if (!device?.last_seen) return C.amber;

  const diff = (Date.now() - new Date(device.last_seen).getTime()) / 1000;
  if (diff < 30) return C.green;
  if (diff < 120) return C.amber;
  return C.red;
}

function statusLabel(device: any) {
  if (!device?.is_active) return "OFFLINE";
  if (!device?.last_seen) return "REGISTERED";

  const diff = (Date.now() - new Date(device.last_seen).getTime()) / 1000;
  if (diff < 30) return "ACTIVE";
  if (diff < 120) return "IDLE";
  return "STALE";
}

type Device = {
  id: string;
  name: string;
  serial_number: string;
  device_type: string;
  location_tag: string;
  is_active: boolean;
  last_seen: string | null;
  created_at: string;
};

// ── Backend card ─────────────────────────────────────────────────
function BackendCard({ health }: { health: any }) {
  const ok = !!health;

  return (
    <View style={[styles.card, { borderLeftColor: ok ? C.green : C.red }]}>
      <View style={styles.cardTop}>
        <Text style={styles.nodeName}>BACKEND — DJANGO</Text>
        <View
          style={[
            styles.statusPill,
            {
              backgroundColor: (ok ? C.green : C.red) + "22",
              borderColor: ok ? C.green : C.red,
            },
          ]}
        >
          <Text style={[styles.statusText, { color: ok ? C.green : C.red }]}>
            {ok ? "ONLINE" : "OFFLINE"}
          </Text>
        </View>
      </View>

      {health && <Text style={styles.meta}>Service: {health.service}</Text>}
      <Text style={styles.meta}>AI Pipeline · SQLite · REST API</Text>
    </View>
  );
}

// ── Device card ──────────────────────────────────────────────────
function DeviceCard({
  device,
  burstCount,
}: {
  device: Device;
  burstCount: number;
}) {
  const col = statusColor(device);
  const label = statusLabel(device);
  const role =
    NODE_LABEL[device.device_type] ??
    device.device_type?.toUpperCase() ??
    "UNKNOWN";

  return (
    <View style={[styles.card, { borderLeftColor: col }]}>
      <View style={styles.cardTop}>
        <View style={{ flex: 1 }}>
          <Text style={styles.nodeRole}>{role}</Text>
          <Text style={styles.nodeName}>{device.name}</Text>
        </View>

        <View
          style={[
            styles.statusPill,
            { backgroundColor: col + "22", borderColor: col },
          ]}
        >
          <Text style={[styles.statusText, { color: col }]}>{label}</Text>
        </View>
      </View>

      <View style={styles.metaRow}>
        <Text style={styles.meta}>S/N {device.serial_number}</Text>
        {device.location_tag ? (
          <Text style={styles.meta}>{device.location_tag}</Text>
        ) : null}
      </View>

      <View style={styles.statsRow}>
        <View>
          <Text style={styles.statVal}>{burstCount}</Text>
          <Text style={styles.statLabel}>BURSTS</Text>
        </View>

        <View>
          <Text style={styles.statVal}>
            {timeSince(device.last_seen)}
          </Text>
          <Text style={styles.statLabel}>LAST SEEN</Text>
        </View>
      </View>
    </View>
  );
}

// ── MAIN ─────────────────────────────────────────────────────────
export default function NodesTab() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [bursts, setBursts] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);

      const [d, b, h] = await Promise.all([
        getDevices(),
        getBursts(),
        getHealth(),
      ]);

      console.log("DEVICES:", d);
      console.log("BURSTS:", b);
      console.log("HEALTH:", h);

      setDevices(d || []);
      setBursts(b || []);
      setHealth(h || null);
    } catch (err) {
      console.log("LOAD ERROR:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  const burstCount = (deviceId: string) =>
    (bursts || []).filter(
      (b: any) =>
        b.device === deviceId ||
        b.device_id === deviceId ||
        b.device?.id === deviceId
    ).length;

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={C.accent} />
      </View>
    );
  }

  return (
    <FlatList
      data={devices}
      keyExtractor={(d) => d.id}
      extraData={bursts}
      contentContainerStyle={styles.list}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => load(true)}
          tintColor={C.accent}
        />
      }
      ListHeaderComponent={
        <>
          <Text style={styles.sectionTitle}>SYSTEM NODES</Text>
          <BackendCard health={health} />
          <Text style={[styles.sectionTitle, { marginTop: 16 }]}>
            REGISTERED DEVICES
          </Text>
        </>
      }
      ListEmptyComponent={
        <Text style={styles.empty}>No devices registered</Text>
      }
      renderItem={({ item }) => (
        <DeviceCard
          device={item}
          burstCount={burstCount(item.id)}
        />
      )}
    />
  );
}

// ── STYLES ───────────────────────────────────────────────────────
const styles = StyleSheet.create({
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: C.bg,
  },

  list: {
    padding: 12,
    paddingBottom: 30,
    backgroundColor: C.bg,
  },

  sectionTitle: {
    color: C.textDim,
    fontSize: 9,
    letterSpacing: 3,
    marginBottom: 8,
  },

  empty: {
    color: C.textDim,
    textAlign: "center",
    marginTop: 30,
    letterSpacing: 2,
    fontSize: 11,
  },

  card: {
    backgroundColor: C.bgCard,
    borderWidth: 1,
    borderColor: C.border,
    borderLeftWidth: 4,
    borderRadius: 6,
    padding: 14,
    marginBottom: 10,
  },

  cardTop: {
    flexDirection: "row",
    alignItems: "flex-start",
    marginBottom: 8,
  },

  nodeRole: {
    color: C.textDim,
    fontSize: 9,
    letterSpacing: 2,
    marginBottom: 2,
  },

  nodeName: {
    color: C.text,
    fontSize: 13,
    fontWeight: "bold",
  },

  statusPill: {
    borderWidth: 1,
    borderRadius: 3,
    paddingHorizontal: 7,
    paddingVertical: 3,
    marginLeft: 8,
  },

  statusText: {
    fontSize: 9,
    letterSpacing: 1,
    fontWeight: "bold",
  },

  metaRow: {
    flexDirection: "row",
    gap: 16,
    marginBottom: 10,
  },

  meta: {
    color: C.textDim,
    fontSize: 10,
    fontFamily: Platform.OS === "android" ? "monospace" : "Courier",
  },

  statsRow: {
    flexDirection: "row",
    gap: 24,
  },

  statVal: {
    color: C.accent,
    fontSize: 14,
    fontWeight: "bold",
  },

  statLabel: {
    color: C.textDim,
    fontSize: 9,
    letterSpacing: 1,
  },
});