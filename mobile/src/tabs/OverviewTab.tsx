import React, { useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Animated,
  Easing,
} from "react-native";
import { getLatestResult } from "../services/api";
import C from "../constants/colors";

// ── Helpers ────────────────────────────────────────────────────────
const threatLabel = (t: number) =>
  ["", "NORMAL", "SUSPICIOUS", "ELEVATED", "HIGH", "CRITICAL"][t] ?? "UNKNOWN";

const threatColor = (t: number) =>
  t >= 5 ? C.red : t >= 4 ? C.red : t >= 3 ? C.amber : C.green;

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ── Pulse ring when threat >= 3 ────────────────────────────────────
function PulseRing({ color, active }: { color: string; active: boolean }) {
  const anim = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!active) return;
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 1, duration: 900, useNativeDriver: true, easing: Easing.out(Easing.ease) }),
        Animated.timing(anim, { toValue: 0, duration: 600, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [active]);

  const scale  = anim.interpolate({ inputRange: [0, 1], outputRange: [1, 1.6] });
  const opacity = anim.interpolate({ inputRange: [0, 1], outputRange: [0.6, 0] });

  return (
    <Animated.View
      style={{
        position: "absolute",
        width: 18, height: 18,
        borderRadius: 9,
        backgroundColor: color,
        transform: [{ scale }],
        opacity,
      }}
    />
  );
}

// ── Threat bar ─────────────────────────────────────────────────────
function ThreatBar({ level }: { level: number }) {
  const color = threatColor(level);
  return (
    <View style={{ flexDirection: "row", gap: 4, marginVertical: 10 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <View
          key={i}
          style={{
            flex: 1,
            height: 6,
            borderRadius: 3,
            backgroundColor: i <= level ? color : C.border,
            opacity: i <= level ? 1 : 0.25,
          }}
        />
      ))}
    </View>
  );
}

// ── Stat row ───────────────────────────────────────────────────────
function Row({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, color ? { color } : {}]}>{value}</Text>
    </View>
  );
}

// ── Audit chip ─────────────────────────────────────────────────────
function Chip({ label, active }: { label: string; active: boolean }) {
  return (
    <View style={[styles.chip, active && { backgroundColor: C.redDim, borderColor: C.red }]}>
      <Text style={[styles.chipText, active && { color: C.red }]}>{label}</Text>
    </View>
  );
}

// ── Main ───────────────────────────────────────────────────────────
export default function OverviewTab() {
  const [state, setState] = useState<"loading" | "error" | "waiting" | "ok">("loading");
  const [data, setData]   = useState<any>(null);
  const flashAnim         = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (data?.threat_level >= 3) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(flashAnim, { toValue: 0.3, duration: 400, useNativeDriver: true }),
          Animated.timing(flashAnim, { toValue: 1,   duration: 400, useNativeDriver: true }),
        ]),
        { iterations: 4 }
      ).start();
    }
  }, [data?.id]);

  const fetchData = async () => {
    const res = await getLatestResult();
    if (!res || res.status === "error") { setState("error"); return; }
    if (res.status === "no_data")       { setState("waiting"); return; }
    const p = res.data ?? res;
    if (!p || p.threat_level === undefined) { setState("waiting"); return; }
    setState("ok");
    setData(p);
  };

  if (state === "loading") return <Text style={styles.center}>INITIALISING...</Text>;
  if (state === "error")   return <Text style={[styles.center, { color: C.red }]}>BACKEND UNREACHABLE</Text>;
  if (state === "waiting") return (
    <View style={styles.waitContainer}>
      <Text style={styles.waitTitle}>STANDING BY</Text>
      <Text style={styles.waitSub}>Waiting for sensor trigger</Text>
    </View>
  );

  const tColor = threatColor(data.threat_level);
  const audit  = data.audit ?? {};
  const actors = data.actors ?? [];

  return (
    <ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>

      {/* Threat level hero */}
      <Animated.View style={[styles.heroCard, { borderColor: tColor, opacity: flashAnim }]}>
        <View style={styles.heroTop}>
          <View>
            <Text style={styles.heroLabel}>THREAT LEVEL</Text>
            <Text style={[styles.heroLevel, { color: tColor }]}>{data.threat_level}</Text>
          </View>
          <View style={styles.pulseWrap}>
            <PulseRing color={tColor} active={data.threat_level >= 3} />
            <View style={[styles.dot, { backgroundColor: tColor }]} />
          </View>
        </View>

        <Text style={[styles.threatTag, { color: tColor, borderColor: tColor }]}>
          {threatLabel(data.threat_level)}
        </Text>

        <ThreatBar level={data.threat_level} />

        <Text style={styles.confidence}>
          CONFIDENCE  {(data.confidence * 100).toFixed(1)}%
        </Text>
      </Animated.View>

      {/* Scene intelligence */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>SCENE INTELLIGENCE</Text>
        <View style={styles.infoCard}>
          <Row label="SCENE"  value={data.scene_intent  || "—"} />
          <Row label="GROUP"  value={data.group_intent  || "—"} />
          <Row label="DECISION" value={data.decision    || "—"} color={C.accent} />
          <Row label="ACTORS" value={String(actors.length)} />
          {data.created_at && (
            <Row label="CAPTURED" value={fmt(data.created_at)} />
          )}
        </View>
      </View>

      {/* Audit signals */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>BAYESIAN SIGNALS</Text>
        <View style={styles.chipRow}>
          <Chip label="WEAPON"       active={!!audit.weapon_severity && audit.weapon_severity > 0} />
          <Chip label="AGGRESSION"   active={!!audit.aggressive_behavior} />
          <Chip label="COORDINATED"  active={!!audit.coordinated_activity} />
          <Chip label="AUDIO SPIKE"  active={!!audit.audio_spike} />
          <Chip label="HIGH SPEED"   active={!!audit.high_speed} />
        </View>
        {audit.weapon_severity > 0 && (
          <Text style={styles.weaponNote}>
            Weapon severity score: {audit.weapon_severity.toFixed(2)}
          </Text>
        )}
      </View>

      {/* Analyst briefing */}
      {data.briefing ? (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>ANALYST BRIEFING</Text>
          <View style={styles.briefCard}>
            <Text style={styles.briefText}>{data.briefing}</Text>
          </View>
        </View>
      ) : null}

      {/* Actors */}
      {actors.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>TRACKED ACTORS</Text>
          {actors.map((a: any, i: number) => (
            <View key={i} style={styles.actorRow}>
              <Text style={styles.actorId}>
                ID {typeof a === "object" ? a.id : a}
              </Text>
              {typeof a === "object" && a.intent && (
                <Text style={styles.actorIntent}>{a.intent}</Text>
              )}
            </View>
          ))}
        </View>
      )}

    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll:         { flex: 1, backgroundColor: C.bg },
  scrollContent:  { padding: 14, paddingBottom: 30 },

  center: { color: C.textMid, textAlign: "center", marginTop: 60, fontSize: 13, letterSpacing: 2 },

  waitContainer:  { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: C.bg },
  waitTitle:      { color: C.accent, fontSize: 18, letterSpacing: 4, marginBottom: 8 },
  waitSub:        { color: C.textDim, fontSize: 12, letterSpacing: 1 },

  heroCard: {
    borderWidth: 1,
    borderRadius: 6,
    backgroundColor: C.bgCard,
    padding: 16,
    marginBottom: 14,
  },
  heroTop:    { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  heroLabel:  { color: C.textDim, fontSize: 10, letterSpacing: 2 },
  heroLevel:  { fontSize: 52, fontWeight: "bold", lineHeight: 58 },
  pulseWrap:  { alignItems: "center", justifyContent: "center", width: 36, height: 36, marginTop: 8 },
  dot:        { width: 18, height: 18, borderRadius: 9 },

  threatTag: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: 3,
    paddingHorizontal: 8,
    paddingVertical: 3,
    fontSize: 10,
    letterSpacing: 2,
    marginBottom: 4,
  },
  confidence: { color: C.textDim, fontSize: 10, letterSpacing: 2, marginTop: 4 },

  section:      { marginBottom: 14 },
  sectionTitle: { color: C.textDim, fontSize: 9, letterSpacing: 3, marginBottom: 6 },

  infoCard: {
    backgroundColor: C.bgCard,
    borderWidth: 1,
    borderColor: C.border,
    borderRadius: 6,
    paddingHorizontal: 14,
    paddingVertical: 4,
  },
  row:       { flexDirection: "row", justifyContent: "space-between", paddingVertical: 9, borderBottomWidth: 1, borderBottomColor: C.border },
  rowLabel:  { color: C.textDim, fontSize: 10, letterSpacing: 1 },
  rowValue:  { color: C.text, fontSize: 12, fontFamily: "monospace" },

  chipRow:  { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip:     { borderWidth: 1, borderColor: C.border, borderRadius: 3, paddingHorizontal: 8, paddingVertical: 4, backgroundColor: C.bgCard },
  chipText: { color: C.textDim, fontSize: 10, letterSpacing: 1 },

  weaponNote: { color: C.red, fontSize: 10, marginTop: 8, letterSpacing: 1 },

  briefCard: { backgroundColor: C.bgCard, borderWidth: 1, borderColor: C.border, borderRadius: 6, padding: 12 },
  briefText: { color: C.textMid, fontSize: 12, lineHeight: 20 },

  actorRow:   { flexDirection: "row", justifyContent: "space-between", backgroundColor: C.bgCard, borderWidth: 1, borderColor: C.border, borderRadius: 4, padding: 10, marginBottom: 6 },
  actorId:    { color: C.accent, fontSize: 12, fontFamily: "monospace" },
  actorIntent:{ color: C.textMid, fontSize: 11 },
});
