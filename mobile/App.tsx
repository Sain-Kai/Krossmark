import React from "react";
import { StatusBar } from "react-native";
import MainScreen from "./src/screens/MainScreen";

export default function App() {
  return (
    <>
      <StatusBar barStyle="light-content" backgroundColor="#03080F" />
      <MainScreen />
    </>
  );
}
