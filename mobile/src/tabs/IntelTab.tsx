import React, { useCallback, useEffect, useState } from "react";
import {
  View, Text, FlatList, StyleSheet,
  ActivityIndicator, RefreshControl,
} from "react-native";
import { getResults } from "../services/api";
import C from "../constants/colors";

// ── Threat sparkline ───────────────────────────────────────────────
function Sparkline({ results }: { results: any[] }) {
  const recent = results.slice(0, 20).reverse();
  const max = 5;
  return (
    <View style={spark.container}>
      <Text style={spark.label}>THREAT HISTORY  (last {recent.length})</Text>
      <View style={spark.bars}>
        {recent.map((r, i) => {
          const h = (r.threat_level / max) * 40;
          const col =
            r.threat_level >= 4 ? C.red :
            r.threat_level >= 3 ? C.amber : C.green;
          return (
            <View key={i} style={spark.barWrap}>
              <View style={[spark.bar, { height: h, backgroundColor: col }]} />
            </View>
          );
        })}
      </View>
      <View style={spark.axisRow}>
        <Text style={spark.axis}>OLDEST</Text>
        <Text style={spark.axis}>LATEST</Text>
      </View>
    </View>
  );
}

const spark = StyleSheet.create({
  container: { backgroundColor: C.bgCard, borderWidth: 1, borderColor: C.border, borderRadius: 6, padding: 12, marginBottom: 14 },
  label:     { color: C.textDim, fontSize: 9, letterSpacing: 2, marginBottom: 10 },
  bars:      { flexDirection: "row", alignItems: "flex-end", height: 44, gap: 3 },
  barWrap:   { flex: 1, alignItems: "center", justifyContent: "flex-end", height: 44 },
  bar:       { width: "100%", borderRadius: 2, minHeight: 3 },
  axisRow:   { flexDirection: "row", justifyContent: "space-between", marginTop: 6 },
  axis:      { color: C.textDim, fontSize: 8, letterSpacing: 1 },
});

// ── Pipeline info ──────────────────────────────────────────────────
const PIPELINE_STEPS = [
  { name: "YOLO Detection",     detail: "yolo26m.pt · person class · conf 0.3" },
  { name: "DeepSort Tracking",  detail: "max_age=15 · cosine distance 0.2" },
  { name: "RTMPose Estimator",  detail: "Wrist · elbow · shoulder keypoints" },
  { name: "HTSAT Audio",        detail: "CLAP model · metallic & shout scores" },
  { name: "OllamaVLM",          detail: "qwen3-vl:4b · 3 keyframes · JSON out" },
  { name: "Bayesian Scorer",    detail: "Prior 0.05 · weapon severity scaling" },
  { name: "Group Intent",       detail: "Proximity clustering · majority vote" },
  { name: "Analyst Briefer",    detail: "Deterministic brief generator" },
];

function PipelineCard() {
  return (
    <View style={pipe.card}>
      <Text style={pipe.title}>AI PIPELINE STAGES</Text>
      {PIPELINE_STEPS.map((s, i) => (
        <View key={i} style={pipe.row}>
          <View style={pipe.numWrap}>
            <Text style={pipe.num}>{i + 1}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={pipe.name}>{s.name}</Text>
            <Text style={pipe.detail}>{s.detail}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

const pipe = StyleSheet.create({
  card:    { backgroundColor: C.bgCard, borderWidth: 1, borderColor: C.border, borderRadius: 6, padding: 14, marginBottom: 14 },
  title:   { color: C.textDim, fontSize: 9, letterSpacing: 3, marginBottom: 12 },
  row:     { flexDirection: "row", alignItems: "flex-start", marginBottom: 12, gap: 10 },
  numWrap: { width: 20, height: 20, borderRadius: 10, backgroundColor: C.accentDim, alignItems: "center", justifyContent: "center" },
  num:     { color: C.accent, fontSize: 10, fontWeight: "bold" },
  name:    { color: C.text, fontSize: 12, fontWeight: "bold" },
  detail:  { color: C.textDim, fontSize: 10, marginTop: 2 },
});

// ── History list item ──────────────────────────────────────────────
function HistoryItem({ item }: { item: any }) {
  const col =
    item.threat_level >= 4 ? C.red :
    item.threat_level >= 3 ? C.amber : C.green;
  const d = new Date(item.created_at);
  const time = d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const date = d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });

  return (
    <View style={[hist.row, { borderLeftColor: col }]}>
      <View style={hist.left}>
        <Text style={[hist.level, { color: col }]}>T{item.threat_level}</Text>
        <Text style={hist.conf}>{(item.confidence * 100).toFixed(0)}%</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={hist.scene} numberOfLines={1}>
          {item.scene_intent || item.group_intent || "—"}
        </Text>
        <Text style={hist.brief} numberOfLines={1}>{item.briefing || "—"}</Text>
      </View>
      <View style={hist.right}>
        <Text style={hist.time}>{time}</Text>
        <Text style={hist.date}>{date}</Text>
      </View>
    </View>
  );
}

const hist = StyleSheet.create({
  row:   { flexDirection: "row", alignItems: "center", backgroundColor: C.bgCard, borderWidth: 1, borderColor: C.border, borderLeftWidth: 3, borderRadius: 5, padding: 10, marginBottom: 6, gap: 10 },
  left:  { alignItems: "center", width: 36 },
  level: { fontSize: 16, fontWeight: "bold" },
  conf:  { color: C.textDim, fontSize: 9 },
  scene: { color: C.text, fontSize: 11, fontWeight: "bold" },
  brief: { color: C.textDim, fontSize: 10, marginTop: 2 },
  right: { alignItems: "flex-end" },
  time:  { color: C.textMid, fontSize: 10, fontFamily: "monospace" },
  date:  { color: C.textDim, fontSize: 9 },
});

// ── Main ───────────────────────────────────────────────────────────
export default function IntelTab() {
  const [results,    setResults]   = useState<any[]>([]);
  const [loading,    setLoading]   = useState(true);
  const [refreshing, setRefreshing]= useState(false);
  const [tab,        setTab]       = useState<"history" | "pipeline">("history");

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    const data = await getResults();
    setResults(data);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(() => load(), 10000);
    return () => clearInterval(id);
  }, []);

  if (loading) {
    return <View style={styles.center}><ActivityIndicator color={C.accent} /></View>;
  }

  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      {/* Sub-tab bar */}
      <View style={styles.subBar}>
        {(["history", "pipeline"] as const).map(t => (
          <TouchableOpacity
            key={t}
            style={[styles.subTab, tab === t && styles.subTabActive]}
            onPress={() => setTab(t)}
          >
            <Text style={[styles.subTabText, tab === t && styles.subTabTextActive]}>
              {t.toUpperCase()}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === "history" ? (
        <FlatList
          data={results}
          keyExtractor={r => r.id}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor={C.accent} />
          }
          ListHeaderComponent={
            results.length > 0 ? <Sparkline results={results} /> : null
          }
          ListEmptyComponent={
            <Text style={styles.empty}>No analysis results yet</Text>
          }
          renderItem={({ item }) => <HistoryItem item={item} />}
        />
      ) : (
        <FlatList
          data={[]}
          keyExtractor={() => ""}
          contentContainerStyle={styles.list}
          ListHeaderComponent={<PipelineCard />}
          renderItem={() => null}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  center:          { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: C.bg },
  list:            { padding: 12, paddingBottom: 30 },
  empty:           { color: C.textDim, textAlign: "center", marginTop: 40, letterSpacing: 2, fontSize: 11 },

  subBar:          { flexDirection: "row", borderBottomWidth: 1, borderBottomColor: C.border },
  subTab:          { flex: 1, paddingVertical: 10, alignItems: "center" },
  subTabActive:    { borderBottomWidth: 2, borderBottomColor: C.accent },
  subTabText:      { color: C.textDim, fontSize: 10, letterSpacing: 2 },
  subTabTextActive:{ color: C.accent },
});
