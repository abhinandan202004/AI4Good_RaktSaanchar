/**
 * useNtfyPush — subscribes to the user's personal ntfy.sh topic
 * and fires a callback whenever a notification arrives.
 *
 * ntfy.sh channel per user:  <NTFY_BASE_URL>/<topic_prefix>-<user_id>
 *
 * Usage:
 *   useNtfyPush(userId, (msg) => console.log(msg.title, msg.message));
 *
 * The hook opens a Server-Sent Events (SSE) connection which works in all
 * modern browsers without any third-party push SDKs.
 *
 * Environment variables (set in Vite .env):
 *   VITE_NTFY_BASE_URL      = https://ntfy.sh  (or your self-hosted URL)
 *   VITE_NTFY_TOPIC_PREFIX  = raktsaanchar
 */

import { useEffect, useRef, useCallback } from "react";

export interface NtfyMessage {
  id: string;
  time: number;
  event: string;
  topic: string;
  title: string;
  message: string;
  priority: number;
  tags: string[];
}

type NtfyCallback = (message: NtfyMessage) => void;

const NTFY_BASE_URL =
  import.meta.env.VITE_NTFY_BASE_URL ?? "https://ntfy.sh";
const NTFY_TOPIC_PREFIX =
  import.meta.env.VITE_NTFY_TOPIC_PREFIX ?? "raktsaanchar";

function getUserTopic(userId: number | string): string {
  return `${NTFY_TOPIC_PREFIX}-${userId}`;
}

/**
 * Subscribe to ntfy.sh push notifications for the given user.
 * The hook cleans up the SSE connection on unmount or when userId changes.
 */
export function useNtfyPush(
  userId: number | string | null | undefined,
  onMessage: NtfyCallback
): void {
  const callbackRef = useRef<NtfyCallback>(onMessage);
  callbackRef.current = onMessage;

  useEffect(() => {
    if (!userId) return;

    const topic = getUserTopic(userId);
    const url = `${NTFY_BASE_URL}/${topic}/sse`;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data: NtfyMessage = JSON.parse(event.data);
        callbackRef.current(data);
      } catch (e) {
        // Ignore malformed messages (heartbeats send empty data)
      }
    };

    eventSource.onerror = () => {
      // Browser auto-reconnects on SSE errors — no action needed
    };

    return () => {
      eventSource.close();
    };
  }, [userId]);
}

/**
 * Send a push notification to a user via ntfy.sh.
 * Useful for testing from the frontend or for peer-to-peer notifications.
 * Note: For production, notifications should be sent server-side only.
 */
export async function sendNtfyPush(
  userId: number | string,
  title: string,
  message: string,
  priority: "urgent" | "high" | "default" | "low" | "min" = "default"
): Promise<boolean> {
  const topic = getUserTopic(userId);
  try {
    const response = await fetch(`${NTFY_BASE_URL}/${topic}`, {
      method: "POST",
      body: message,
      headers: {
        Title: title,
        Priority: priority,
        Tags: "drop_of_blood",
      },
    });
    return response.ok;
  } catch {
    return false;
  }
}
