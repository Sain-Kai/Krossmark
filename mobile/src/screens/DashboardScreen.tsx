import React, { useEffect, useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { getLatestResult } from "../services/api";

const C = {
  bg: "#050C14",
  card: "#0D1F35",
  border: "#1A3050",
  accent: "#00D4FF",
  red: "#FF3B4E",
  amber: "#FFAA00",
  green: "#00FF9F",
  text: "#E0F0FF",
  muted: "#4A6A8A",
};

export default function DashboardScreen() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    const res = await getLatestResult();
    if (res?.status === "ok") setData(res.data);
  };

  if (!data) {
    return (
      <View style={styles.center}>
        <Text style={{ color: C.text }}>Connecting...</Text>
      </View>
    );
  }

  const threatColor =
    data.threat_level >= 5
      ? C.red
      : data.threat_level >= 3
      ? C.amber
      : C.green;

  return (
    <View style={styles.container}>
      {/* HEADER */}
      <Text style={styles.header}>KROSS MARK · LIVE FEED</Text>

      {/* ALERT CARD */}
      <View style={[styles.card, { borderLeftColor: threatColor }]}>
        <View style={styles.row}>
          <Text style={styles.id}>EVENT-001</Text>
          <Text style={[styles.level, { color: threatColor }]}>
            T{data.threat_level}
          </Text>
        </View>

        {/* Threat bar */}
        <View style={styles.barRow}>
          {[...Array(10)].map((_, i) => (
            <View
              key={i}
              style={{
                width: 10,
                height: 14,
                marginRight: 3,
                backgroundColor:
                  i < data.threat_level ? threatColor : C.border,
                opacity: i < data.threat_level ? 1 : 0.3,
              }}
            />
          ))}
        </View>

        <Text style={styles.text}>
          Confidence: {(data.confidence * 100).toFixed(1)}%
        </Text>
        <Text style={styles.text}>Group: {data.group_intent}</Text>
        <Text style={styles.text}>Scene: {data.scene_intent}</Text>
        <Text style={styles.briefing}>{data.briefing}</Text>
        <Text style={styles.text}>
          Actors: {data.actors?.length ?? 0}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: C.bg,
    padding: 16,
  },
  header: {
    color: C.accent,
    fontSize: 14,
    marginBottom: 10,
    letterSpacing: 1,
  },
  card: {
    backgroundColor: C.card,
    borderWidth: 1,
    borderColor: C.border,
    borderLeftWidth: 4,
    borderRadius: 6,
    padding: 14,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  id: {
    color: C.accent,
    fontFamily: "monospace",
  },
  level: {
    fontSize: 18,
    fontWeight: "bold",
  },
  barRow: {
    flexDirection: "row",
    marginVertical: 8,
  },
  text: {
    color: C.text,
    fontSize: 13,
    marginTop: 4,
  },
  briefing: {
    color: C.muted,
    fontSize: 12,
    marginTop: 8,
    lineHeight: 18,
  },
  center: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: C.bg,
  },
});