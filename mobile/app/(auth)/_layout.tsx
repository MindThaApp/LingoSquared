import { Stack } from "expo-router";

// Logged-out route group: login + register. The root layout's
// Stack.Protected guard is what keeps signed-in users out of here (and
// signed-out users out of everything else) -- this layout only shapes the
// two screens' local navigation.
export const unstable_settings = {
  initialRouteName: "login",
};

export default function AuthLayout() {
  return (
    <Stack>
      <Stack.Screen name="login" options={{ title: "Log in" }} />
      <Stack.Screen name="register" options={{ title: "Create account" }} />
    </Stack>
  );
}
