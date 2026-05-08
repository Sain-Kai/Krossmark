import React, { useCallback, useEffect, useState } from "react";
import {
  View, Text, FlatList, TouchableOpacity,
  Modal, StyleSheet, ActivityIndicator, RefreshControl,
} from "react-native";
import { getAlerts, ackAlert } from "../services/api";
import C from "../constants/colors";

const SEV_COLOR: Record<string, string> = {
  critical: C.red,
  high:     C.red,
  medium:   C.amber,
  low:      C.green,
  info:     C.accent,
};

const SEV_ORDER: Record<string, number> = {
  critical: 0, high: 1, medium: 2, low: 3, info: 4,
};

function severityColor(s: string) { return SEV_COLOR[s] ?? C.textMid; }

function TimeAgo({ iso }: { iso: string }) {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  const label =
    diff < 60   ? `${diff}s ago` :
    diff < 3600 ? `${Math.floor(diff / 60)}m ago` :
                  `${Math.floor(diff / 3600)}h ago`;
  return <Text style={styles.timeAgo}>{label}</Text>;
}

type Alert = {
  id: string;
  severity: string;
  title: string;
  message: string;
  acknowledged: boolean;
  created_at: string;
  analysis_result?: string;
};

export default function AlertsTab() {
  const [alerts,      setAlerts]    = useState<Alert[]>([]);
  const [loading,     setLoading]   = useState(true);
  const [refreshing,  setRefreshing]= useState(false);
  const [selected,    setSelected]  = useState<Alert | null>(null);
  const [acking,      setAcking]    = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    const data = await getAlerts();
    const sorted = [...data].sort((a: Alert, b: Alert) => {
      if (a.acknowledged !== b.acknowledged) return a.acknowledged ? 1 : -1;
      const so = (SEV_ORDER[a.severity] ?? 5) - (SEV_ORDER[b.severity] ?? 5);
      if (so !== 0) return so;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    setAlerts(sorted);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(() => load(), 5000);
    return () => clearInterval(id);
  }, []);

  const handleAck = async () => {
    if (!selected) return;
    setAcking(true);
    const ok = await ackAlert(selected.id);
    if (ok) {
      setAlerts(prev =>
        prev.map(a => a.id === selected.id ? { ...a, acknowledged: true } : a)
      );
      setSelected(null);
    }
    setAcking(false);
  };

  const unread = alerts.filter(a => !a.acknowledged).length;

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={C.accent} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>

      {/* Summary bar */}
      <View style={styles.summaryBar}>
        <Text style={styles.summaryText}>
          {unread > 0
            ? `${unread} UNACKNOWLEDGED ALERT${unread > 1 ? "S" : ""}`
            : "ALL CLEAR"}
        </Text>
        <View style={[styles.badge, { backgroundColor: unread > 0 ? C.redDim : C.greenDim }]}>
          <Text style={[styles.badgeText, { color: unread > 0 ? C.red : C.green }]}>
            {alerts.length}
          </Text>
        </View>
      </View>

      <FlatList
        data={alerts}
        keyExtractor={i => i.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={C.accent} />
        }
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>No alerts recorded</Text>
        }
        renderItem={({ item }) => {
          const col = severityColor(item.severity);
          return (
            <TouchableOpacity
              style={[
                styles.card,
                { borderLeftColor: col },
                item.acknowledged && styles.cardAcked,
              ]}
              onPress={() => setSelected(item)}
              activeOpacity={0.75}
            >
              <View style={styles.cardTop}>
                <View style={styles.cardLeft}>
                  <View style={[styles.sevPill, { backgroundColor: col + "22", borderColor: col }]}>
                    <Text style={[styles.sevText, { color: col }]}>
                      {item.severity.toUpperCase()}
                    </Text>
                  </View>
                  {item.acknowledged && (
                    <Text style={styles.ackedTag}>ACK</Text>
                  )}
                </View>
                <TimeAgo iso={item.created_at} />
              </View>
              <Text style={styles.cardTitle} numberOfLines={1}>{item.title}</Text>
              <Text style={styles.cardMsg}   numberOfLines={2}>{item.message}</Text>
            </TouchableOpacity>
          );
        }}
      />

      {/* Detail modal */}
      <Modal visible={!!selected} transparent animationType="slide" onRequestClose={() => setSelected(null)}>
        <TouchableOpacity style={styles.modalBg} activeOpacity={1} onPress={() => setSelected(null)}>
          <TouchableOpacity activeOpacity={1} style={styles.modal}>
            {selected && (() => {
              const col = severityColor(selected.severity);
              return (
                <>
                  <View style={[styles.modalBar, { backgroundColor: col }]} />

                  <View style={styles.modalHeader}>
                    <View style={[styles.sevPill, { backgroundColor: col + "22", borderColor: col }]}>
                      <Text style={[styles.sevText, { color: col }]}>
                        {selected.severity.toUpperCase()}
                      </Text>
                    </View>
                    <TimeAgo iso={selected.created_at} />
                  </View>

                  <Text style={styles.modalTitle}>{selected.title}</Text>
                  <Text style={styles.modalMsg}>{selected.message}</Text>

                  <View style={styles.modalId}>
                    <Text style={styles.modalIdText}>ID  {selected.id}</Text>
                  </View>

                  {!selected.acknowledged ? (
                    <TouchableOpacity
                      style={[styles.ackBtn, { borderColor: col }]}
                      onPress={handleAck}
                      disabled={acking}
                    >
                      <Text style={[styles.ackBtnText, { color: col }]}>
                        {acking ? "ACKNOWLEDGING..." : "ACKNOWLEDGE"}
                      </Text>
                    </TouchableOpacity>
                  ) : (
                    <View style={styles.ackedBanner}>
                      <Text style={styles.ackedBannerText}>ACKNOWLEDGED</Text>
                    </View>
                  )}

                  <TouchableOpacity onPress={() => setSelected(null)} style={styles.closeBtn}>
                    <Text style={styles.closeBtnText}>CLOSE</Text>
                  </TouchableOpacity>
                </>
              );
            })()}
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  center:      { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: C.bg },
  empty:       { color: C.textDim, textAlign: "center", marginTop: 40, letterSpacing: 2, fontSize: 11 },

  summaryBar:  { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: C.border },
  summaryText: { color: C.textDim, fontSize: 10, letterSpacing: 2 },
  badge:       { borderRadius: 10, paddingHorizontal: 8, paddingVertical: 2 },
  badgeText:   { fontSize: 11, fontWeight: "bold" },

  list:        { padding: 12, paddingBottom: 30 },

  card: {
    backgroundColor: C.bgCard,
    borderWidth: 1,
    borderColor: C.border,
    borderLeftWidth: 4,
    borderRadius: 6,
    padding: 12,
    marginBottom: 10,
  },
  cardAcked:   { opacity: 0.45 },
  cardTop:     { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 6 },
  cardLeft:    { flexDirection: "row", alignItems: "center", gap: 6 },
  cardTitle:   { color: C.text, fontSize: 13, fontWeight: "bold", marginBottom: 4 },
  cardMsg:     { color: C.textMid, fontSize: 11, lineHeight: 17 },

  sevPill:     { borderWidth: 1, borderRadius: 3, paddingHorizontal: 6, paddingVertical: 2 },
  sevText:     { fontSize: 9, letterSpacing: 1, fontWeight: "bold" },

  ackedTag:    { color: C.green, fontSize: 9, letterSpacing: 1, borderWidth: 1, borderColor: C.green, borderRadius: 3, paddingHorizontal: 4, paddingVertical: 1 },
  timeAgo:     { color: C.textDim, fontSize: 10 },

  modalBg:     { flex: 1, backgroundColor: "#000000CC", justifyContent: "flex-end" },
  modal:       { backgroundColor: C.bgDeep, borderTopLeftRadius: 14, borderTopRightRadius: 14, padding: 20, paddingBottom: 36 },
  modalBar:    { width: 36, height: 4, borderRadius: 2, alignSelf: "center", marginBottom: 16 },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  modalTitle:  { color: C.text, fontSize: 16, fontWeight: "bold", marginBottom: 10 },
  modalMsg:    { color: C.textMid, fontSize: 13, lineHeight: 21, marginBottom: 16 },
  modalId:     { backgroundColor: C.bgCard, borderRadius: 4, padding: 8, marginBottom: 16 },
  modalIdText: { color: C.textDim, fontFamily: "monospace", fontSize: 11 },

  ackBtn:      { borderWidth: 1, borderRadius: 5, padding: 12, alignItems: "center", marginBottom: 10 },
  ackBtnText:  { fontSize: 12, fontWeight: "bold", letterSpacing: 2 },

  ackedBanner: { backgroundColor: C.greenDim, borderRadius: 5, padding: 12, alignItems: "center", marginBottom: 10 },
  ackedBannerText: { color: C.green, fontSize: 12, fontWeight: "bold", letterSpacing: 2 },

  closeBtn:    { alignItems: "center", paddingVertical: 10 },
  closeBtnText:{ color: C.textDim, fontSize: 11, letterSpacing: 2 },
});
