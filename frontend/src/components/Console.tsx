import { Box, Code, Group, ScrollArea, Text } from "@mantine/core";
import { useEffect, useRef } from "react";
import type { LogEntry } from "../api";

const LEVEL_COLOR: Record<string, string> = {
  info: "dimmed",
  ai: "violet.4",
  device: "teal.4",
  error: "red.4",
  user: "orange.4",
};

const LEVEL_PREFIX: Record<string, string> = {
  info: "SYS ",
  ai: " AI ",
  device: "DEV ",
  error: "ERR ",
  user: "USR ",
};

interface Props {
  entries: LogEntry[];
}

export function Console({ entries }: Props) {
  const viewport = useRef<HTMLDivElement>(null);
  const atBottom = useRef(true);

  // Auto-scroll only when already at bottom
  useEffect(() => {
    if (atBottom.current && viewport.current) {
      viewport.current.scrollTo({ top: viewport.current.scrollHeight, behavior: "smooth" });
    }
  }, [entries]);

  return (
    <Box
      style={{
        background: "var(--mantine-color-dark-9)",
        borderRadius: 8,
        border: "1px solid var(--mantine-color-dark-6)",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Title bar */}
      <Group
        px="sm"
        py={6}
        style={{
          borderBottom: "1px solid var(--mantine-color-dark-6)",
          flexShrink: 0,
        }}
      >
        <Box
          style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "var(--mantine-color-teal-6)",
            boxShadow: "0 0 6px var(--mantine-color-teal-6)",
          }}
        />
        <Text size="xs" c="dimmed" ff="monospace">lightbar console</Text>
      </Group>

      {/* Log lines */}
      <ScrollArea
        flex={1}
        viewportRef={viewport}
        onScrollPositionChange={({ y }) => {
          if (!viewport.current) return;
          const max = viewport.current.scrollHeight - viewport.current.clientHeight;
          atBottom.current = max - y < 40;
        }}
        styles={{ viewport: { padding: "8px 12px" } }}
      >
        {entries.length === 0 && (
          <Text size="xs" c="dark.4" ff="monospace">waiting for engine...</Text>
        )}
        {entries.map((entry, i) => (
          <Group key={i} gap={6} wrap="nowrap" mb={2} align="flex-start">
            <Text
              size="xs"
              ff="monospace"
              c="dark.4"
              style={{ flexShrink: 0, userSelect: "none" }}
            >
              {new Date(entry.timestamp).toLocaleTimeString("en-GB", {
                hour: "2-digit", minute: "2-digit", second: "2-digit"
              })}
            </Text>
            <Code
              style={{
                background: "transparent",
                padding: 0,
                flexShrink: 0,
                fontSize: "var(--mantine-font-size-xs)",
              }}
              c={LEVEL_COLOR[entry.level] ?? "white"}
            >
              [{LEVEL_PREFIX[entry.level] ?? entry.level}]
            </Code>
            <Text
              size="xs"
              ff="monospace"
              c={entry.level === "error" ? "red.3" : undefined}
              style={{ wordBreak: "break-word" }}
            >
              {entry.message}
              {entry.data && (
                <Text span c="dark.3" ml={6}>
                  {JSON.stringify(entry.data)}
                </Text>
              )}
            </Text>
          </Group>
        ))}
      </ScrollArea>
    </Box>
  );
}
