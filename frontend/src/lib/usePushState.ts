// Shared render-gating state for the two push-notification surfaces
// (HomePage's PushPrompt, ProfilePage's NotificationSettings). Both must
// stay COMPLETELY hidden unless the browser supports Web Push AND the
// server reports VAPID keys configured — see docs/CONTRACT.md's "Web
// push notifications" section and pushNotifications.ts.
import { useCallback, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PushApi } from "@lingo/shared/api/endpoints";
import { getExistingPushSubscription, isPushSupported } from "./pushNotifications";

export interface PushState {
  supported: boolean;
  configured: boolean;
  /** True while support/config/subscription checks are still resolving —
   * render nothing during this window (avoids a prompt flash). */
  checking: boolean;
  subscribed: boolean;
  refreshSubscribed: () => Promise<void>;
}

export function usePushState(): PushState {
  const supported = isPushSupported();
  const vapidQuery = useQuery({
    queryKey: ["push-vapid"],
    queryFn: PushApi.vapidPublicKey,
    enabled: supported,
    // Server VAPID config doesn't change at runtime; one probe per app
    // load is plenty, and a failed probe (old backend) means "hidden",
    // not "retry until it works".
    staleTime: Infinity,
    retry: false,
  });

  const [subscribed, setSubscribed] = useState<boolean | null>(null);
  const refreshSubscribed = useCallback(async () => {
    setSubscribed((await getExistingPushSubscription()) !== null);
  }, []);

  useEffect(() => {
    if (!supported) {
      setSubscribed(false);
      return;
    }
    void refreshSubscribed();
  }, [supported, refreshSubscribed]);

  return {
    supported,
    configured: vapidQuery.data?.configured ?? false,
    checking: supported && (vapidQuery.isPending || subscribed === null),
    subscribed: subscribed === true,
    refreshSubscribed,
  };
}
