import { Box, Group, ScrollArea, Stack, Text } from "@mantine/core";
import type { Experiment } from "../api";
import { ColorSwatch } from "./ColorSwatch";

interface Props {
  experiments: Experiment[];
}

export function ExperimentHistory({ experiments }: Props) {
  if (experiments.length === 0) {
    return (
      <Text size="xs" c="dimmed" ff="monospace" p="md">
        no experiments yet
      </Text>
    );
  }

  return (
    <ScrollArea h="100%">
      <Stack gap={0}>
        {experiments.map((exp) => {
          const actNames = exp.acts.map((a) => a.pattern).join(" → ");
          return (
            <Box
              key={exp.id}
              p="sm"
              style={{ borderBottom: "1px solid var(--mantine-color-dark-7)" }}
            >
              <Stack gap={2}>
                <Text size="xs" ff="monospace" fw={600}>
                  {exp.theme}
                </Text>
                <Text size="xs" c="violet.4" ff="monospace">
                  {actNames}
                </Text>
                <Text size="xs" c="dimmed" style={{ wordBreak: "break-word" }}>
                  {exp.inspiration}
                </Text>
                {exp.prompted_by && (
                  <Text size="xs" c="orange.5">
                    "{exp.prompted_by}"
                  </Text>
                )}
                <Text size="xs" c="dark.4" ff="monospace">
                  {new Date(exp.created_at).toLocaleTimeString("en-GB", {
                    hour: "2-digit", minute: "2-digit",
                  })}{" "}
                  · {exp.duration_minutes}m · {exp.acts.length} acts
                </Text>
              </Stack>
            </Box>
          );
        })}
      </Stack>
    </ScrollArea>
  );
}
