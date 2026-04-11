import {
  ActionIcon,
  AppShell,
  Box,
  Divider,
  Grid,
  Group,
  Paper,
  Text,
  Title,
  Tooltip,
} from "@mantine/core";
import { IconPlayerPause, IconPlayerPlay, IconPlayerSkipForward, IconPower } from "@tabler/icons-react";
import { useEffect, useRef, useState } from "react";
import {
  createEventSource,
  fetchExperiments,
  fetchStatus,
  setPower,
  setTimerPaused,
  skipExperiment,
  type EngineStatus,
  type Experiment,
  type LogEntry,
} from "./api";
import { Console } from "./components/Console";
import { ExperimentHistory } from "./components/ExperimentHistory";
import { PromptInput } from "./components/PromptInput";
import { StatusPanel } from "./components/StatusPanel";

const MAX_LOG = 300;

export default function App() {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [log, setLog] = useState<LogEntry[]>([]);
  const esRef = useRef<EventSource | null>(null);

  // Poll status every 4 seconds
  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const s = await fetchStatus();
        if (alive) { setStatus(s); setStatusError(null); }
      } catch (e) {
        if (alive) setStatusError(String(e));
      }
    }
    poll();
    const id = setInterval(poll, 4000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  // Fetch experiment history on mount and after new prompt
  useEffect(() => {
    fetchExperiments().then(setExperiments).catch(() => {});
    const id = setInterval(() => {
      fetchExperiments().then(setExperiments).catch(() => {});
    }, 15000);
    return () => clearInterval(id);
  }, []);

  // SSE for live log
  useEffect(() => {
    function connect() {
      const es = createEventSource();
      esRef.current = es;

      es.onmessage = (e) => {
        try {
          const entry: LogEntry = JSON.parse(e.data);
          setLog((prev) => {
            const next = [...prev, entry];
            return next.length > MAX_LOG ? next.slice(-MAX_LOG) : next;
          });
        } catch {}
      };

      es.onerror = () => {
        es.close();
        // Reconnect after 5 seconds
        setTimeout(connect, 5000);
      };
    }
    connect();
    return () => esRef.current?.close();
  }, []);

  function handlePromptSent() {
    setTimeout(() => fetchExperiments().then(setExperiments).catch(() => {}), 3000);
  }

  async function handlePower() {
    if (!status) return;
    try {
      await setPower(!status.light_on);
      setStatus((s) => s ? { ...s, light_on: !s.light_on } : s);
    } catch {}
  }

  async function handleSkip() {
    try {
      await skipExperiment();
    } catch {}
  }

  async function handlePause() {
    if (!status) return;
    try {
      await setTimerPaused(!status.timer_paused);
      setStatus((s) => s ? { ...s, timer_paused: !s.timer_paused } : s);
    } catch {}
  }

  return (
    <AppShell header={{ height: 48 }} padding="md">
      <AppShell.Header
        style={{
          background: "var(--mantine-color-dark-8)",
          borderBottom: "1px solid var(--mantine-color-dark-6)",
        }}
      >
        <Group h="100%" px="md" justify="space-between">
          <Group gap="xs">
            <Box
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: status?.device_online
                  ? "var(--mantine-color-teal-5)"
                  : "var(--mantine-color-red-5)",
                boxShadow: status?.device_online
                  ? "0 0 8px var(--mantine-color-teal-5)"
                  : undefined,
                transition: "background 0.5s ease",
              }}
            />
            <Title order={5} ff="monospace">
              lightbar
            </Title>
            <Text size="xs" c="dark.4" ff="monospace">
              ai control system
            </Text>
          </Group>
          <Group gap="xs">
            {status?.current_experiment && (
              <Text size="xs" c="violet.4" ff="monospace">
                {status.current_experiment.theme}
              </Text>
            )}
            <Tooltip label="skip to next experiment" position="bottom">
              <ActionIcon
                variant="subtle"
                color="gray"
                size="sm"
                onClick={handleSkip}
                disabled={!status}
              >
                <IconPlayerSkipForward size={14} />
              </ActionIcon>
            </Tooltip>
            <Tooltip label={status?.timer_paused ? "resume timer" : "pause timer"} position="bottom">
              <ActionIcon
                variant={status?.timer_paused ? "light" : "subtle"}
                color={status?.timer_paused ? "yellow" : "gray"}
                size="sm"
                onClick={handlePause}
                disabled={!status}
              >
                {status?.timer_paused
                  ? <IconPlayerPlay size={14} />
                  : <IconPlayerPause size={14} />}
              </ActionIcon>
            </Tooltip>
            <Tooltip label={status?.light_on ? "turn off" : "turn on"} position="bottom">
              <ActionIcon
                variant="subtle"
                color={status?.light_on ? "teal" : "red"}
                size="sm"
                onClick={handlePower}
                disabled={!status}
              >
                <IconPower size={14} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </Group>
      </AppShell.Header>

      <AppShell.Main>
        <Grid h="calc(100vh - 48px - 2rem)" gutter="md">
          {/* Left column: status + prompt + history */}
          <Grid.Col span={{ base: 12, md: 4 }}>
            <Box h="100%" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* Status */}
              <Paper
                withBorder
                style={{
                  background: "var(--mantine-color-dark-8)",
                  flexShrink: 0,
                }}
              >
                <StatusPanel status={status} error={statusError} />
              </Paper>

              <Divider />

              {/* Prompt input */}
              <Paper
                withBorder
                p="md"
                style={{ background: "var(--mantine-color-dark-8)", flexShrink: 0 }}
              >
                <PromptInput onSent={handlePromptSent} />
              </Paper>

              <Divider />

              {/* Experiment history */}
              <Paper
                withBorder
                style={{
                  background: "var(--mantine-color-dark-8)",
                  flex: 1,
                  minHeight: 0,
                  overflow: "hidden",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <Text
                  size="xs"
                  c="dimmed"
                  ff="monospace"
                  px="sm"
                  pt="sm"
                  pb={4}
                  style={{ flexShrink: 0 }}
                >
                  experiment history
                </Text>
                <Box style={{ flex: 1, minHeight: 0 }}>
                  <ExperimentHistory experiments={experiments} />
                </Box>
              </Paper>
            </Box>
          </Grid.Col>

          {/* Right column: console */}
          <Grid.Col span={{ base: 12, md: 8 }}>
            <Console entries={log} />
          </Grid.Col>
        </Grid>
      </AppShell.Main>
    </AppShell>
  );
}
