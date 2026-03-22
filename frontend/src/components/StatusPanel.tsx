import {
  Badge,
  Box,
  Group,
  Progress,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import type { EngineStatus } from "../api";
import { ColorSwatch } from "./ColorSwatch";

interface Props {
  status: EngineStatus | null;
  error: string | null;
}

function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function StatusPanel({ status, error }: Props) {
  if (error) {
    return (
      <Box p="md">
        <Badge color="red" size="lg">Backend offline</Badge>
        <Text c="dimmed" size="xs" mt="xs">{error}</Text>
      </Box>
    );
  }

  if (!status) {
    return (
      <Box p="md">
        <Text c="dimmed" size="sm">Connecting...</Text>
      </Box>
    );
  }

  const exp = status.current_experiment;
  const totalSec = exp ? exp.duration_minutes * 60 : 0;
  const elapsed = totalSec - (status.next_experiment_in_seconds ?? 0);
  const progress = totalSec > 0 ? (elapsed / totalSec) * 100 : 0;

  return (
    <Stack gap="md" p="md">
      {/* Header row */}
      <Group justify="space-between" align="center">
        <Group gap="xs">
          <Badge
            color={status.device_online ? "teal" : "red"}
            variant="dot"
            size="sm"
          >
            {status.device_online ? "device online" : "device offline"}
          </Badge>
          <Badge
            color={status.running ? "violet" : "gray"}
            variant="dot"
            size="sm"
          >
            {status.running ? "engine running" : "engine stopped"}
          </Badge>
        </Group>
        {status.next_experiment_in_seconds != null && (
          <Text size="xs" c="dimmed" ff="monospace">
            next in {formatCountdown(status.next_experiment_in_seconds)}
          </Text>
        )}
      </Group>

      {/* Current color + experiment info */}
      <Group align="flex-start" gap="md">
        <ColorSwatch
          hue={status.current_hue}
          saturation={status.current_saturation}
          value={status.current_value}
          size={56}
        />
        <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
          {exp ? (
            <>
              <Title order={4} style={{ lineHeight: 1.2 }}>
                {exp.theme}
              </Title>
              <Text size="sm" c="dimmed" style={{ wordBreak: "break-word" }}>
                {exp.description}
              </Text>
              <Text size="xs" c="violet.4" mt={2}>
                inspired by: {exp.inspiration}
              </Text>
              {exp.prompted_by && (
                <Text size="xs" c="orange.4">
                  prompted: "{exp.prompted_by}"
                </Text>
              )}
            </>
          ) : (
            <Text size="sm" c="dimmed">No active program</Text>
          )}
        </Stack>
      </Group>

      {/* Progress bar */}
      {exp && totalSec > 0 && (
        <Box>
          <Progress
            value={progress}
            color="violet"
            size="xs"
            radius="xl"
            animated
          />
          <Group justify="space-between" mt={4}>
            <Text size="xs" c="dimmed">
              act {status.current_step_index + 1} / {exp.acts.length}
            </Text>
            <Text size="xs" c="dimmed" ff="monospace">
              HSV {status.current_hue.toFixed(0)}°{" "}
              {status.current_saturation.toFixed(0)}%{" "}
              {status.current_value.toFixed(0)}%
            </Text>
          </Group>
        </Box>
      )}
    </Stack>
  );
}
