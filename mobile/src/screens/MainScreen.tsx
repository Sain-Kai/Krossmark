import React, { useEffect, useRef, useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  SafeAreaView, Animated, Vibration,
} from "react-native";
import OverviewTab from "../tabs/OverviewTab";
import AlertsTab   from "../tabs/AlertsTab";
import NodesTab    from "../tabs/NodesTab";
import IntelTab    from "../tabs/IntelTab";
import { getLatestResult, getAlerts } from "../services/api";
import C from "../constants/colors";

const TABS = ["Overview", "Alerts", "Nodes", "Intel"] as const;
type Tab = (typeof TABS)[number];

export default function MainScreen() {
  const [active,      setActive]     = useState<Tab>("Overview");
  const [unreadCount, setUnreadCount]= useState(0);
  const [threatLevel, setThreatLevel]= useState(0);
  const lastResultId                 = useRef<string | null>(null);
  const flashAnim                    = useRef(new Animated.Value(1)).current;

  // Poll for alerts count and threat level in the background
  useEffect(() => {
    const poll = async () => {
      const [alertData, resultData] = await Promise.all([
        getAlerts(),
        getLatestResult(),
      ]);

      // Unread badge
      const unread = alertData.filter((a: any) => !a.acknowledged).length;
      setUnreadCount(unread);

      // Threat flash + vibrate on new high-threat result
      if (resultData?.status === "ok") {
        const r = resultData.data;
        if (r && r.id !== lastResultId.current) {
          lastResultId.current = r.id;
          setThreatLevel(r.threat_level ?? 0);
          if (r.threat_level >= 3) {
            Vibration.vibrate([0, 300, 150, 300]);
            Animated.loop(
              Animated.sequence([
                Animated.timing(flashAnim, { toValue: 0.2, duration: 200, useNativeDriver: true }),
                Animated.timing(flashAnim, { toValue: 1,   duration: 200, useNativeDriver: true }),
              ]),
              { iterations: 5 }
            ).start();
          }
        }
      }
    };

    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, []);

  const renderTab = () => {
    switch (active) {
      case "Overview": return <OverviewTab />;
      case "Alerts":   return <AlertsTab />;
      case "Nodes":    return <NodesTab />;
      case "Intel":    return <IntelTab />;
    }
  };

  const headerBorderColor =
    threatLevel >= 4 ? C.red :
    threatLevel >= 3 ? C.amber :
    C.border;

  return (
    <SafeAreaView style={styles.root}>

      {/* Header */}
      <Animated.View style={[styles.header, { borderBottomColor: headerBorderColor, opacity: flashAnim }]}>
        <View style={styles.headerLeft}>
          <Text style={styles.logo}>KROSS<Text style={styles.logoAccent}>MARK</Text></Text>
          <Text style={styles.subtitle}>DEFENSE AI SYSTEM</Text>
        </View>
        <View style={styles.headerRight}>
          {threatLevel >= 3 && (
            <View style={[styles.threatBadge, { backgroundColor: (threatLevel >= 4 ? C.red : C.amber) + "22", borderColor: threatLevel >= 4 ? C.red : C.amber }]}>
              <Text style={[styles.threatBadgeText, { color: threatLevel >= 4 ? C.red : C.amber }]}>
                T{threatLevel}
              </Text>
            </View>
          )}
          <View style={styles.onlineDot} />
        </View>
      </Animated.View>

      {/* Tab bar */}
      <View style={styles.tabBar}>
        {TABS.map(tab => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, active === tab && styles.tabActive]}
            onPress={() => setActive(tab)}
            activeOpacity={0.7}
          >
            <Text style={[styles.tabText, active === tab && styles.tabTextActive]}>
              {tab.toUpperCase()}
            </Text>
            {tab === "Alerts" && unreadCount > 0 && (
              <View style={styles.badge}>
                <Text style={styles.badgeText}>
                  {unreadCount > 9 ? "9+" : unreadCount}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {/* Scan line accent */}
      <View style={styles.scanLine} />

      {/* Content */}
      <View style={styles.content}>{renderTab()}</View>

    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root:   { flex: 1, backgroundColor: C.bg },

  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: C.border,
  },
  headerLeft:  {},
  headerRight: { flexDirection: "row", alignItems: "center", gap: 10 },

  logo:        { color: C.text, fontSize: 15, fontWeight: "bold", letterSpacing: 3 },
  logoAccent:  { color: C.accent },
  subtitle:    { color: C.textDim, fontSize: 8, letterSpacing: 3, marginTop: 2 },

  threatBadge: { borderWidth: 1, borderRadius: 3, paddingHorizontal: 7, paddingVertical: 2 },
  threatBadgeText: { fontSize: 10, fontWeight: "bold", letterSpacing: 1 },

  onlineDot: {
    width: 7, height: 7, borderRadius: 4,
    backgroundColor: C.green,
    shadowColor: C.green, shadowOpacity: 0.8, shadowRadius: 4,
  },

  tabBar: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: C.border,
    backgroundColor: C.bgDeep,
  },
  tab:          { flex: 1, paddingVertical: 11, alignItems: "center", position: "relative" },
  tabActive:    { borderBottomWidth: 2, borderBottomColor: C.accent },
  tabText:      { color: C.textDim, fontSize: 9, letterSpacing: 1.5 },
  tabTextActive:{ color: C.accent },

  badge:     { position: "absolute", top: 6, right: 6, backgroundColor: C.red, borderRadius: 8, minWidth: 16, paddingHorizontal: 3, alignItems: "center" },
  badgeText: { color: C.white, fontSize: 8, fontWeight: "bold" },

  scanLine: { height: 1, backgroundColor: C.accent, opacity: 0.08 },

  content:  { flex: 1 },
});
