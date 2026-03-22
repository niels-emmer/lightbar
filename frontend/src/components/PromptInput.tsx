import {
  Box,
  Button,
  Group,
  Stack,
  Text,
  Textarea,
} from "@mantine/core";
import { IconSparkles } from "@tabler/icons-react";
import { useState } from "react";
import { postPrompt } from "../api";

const SUGGESTIONS = [
  "slow sunset over the ocean",
  "electric storm approaching",
  "deep forest at midnight",
  "northern lights, aurora borealis",
  "ember dying in a fireplace",
  "underwater bioluminescence",
  "city at 3am",
];

interface Props {
  onSent: (prompt: string) => void;
}

export function PromptInput({ onSent }: Props) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  async function submit() {
    const prompt = value.trim();
    if (!prompt) return;
    setLoading(true);
    setFeedback(null);
    try {
      await postPrompt(prompt);
      setFeedback("Prompt sent — will take effect on next cycle");
      onSent(prompt);
      setValue("");
    } catch (e) {
      setFeedback("Failed to send prompt");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      submit();
    }
  }

  return (
    <Stack gap="sm">
      <Group gap={6} align="center">
        <IconSparkles size={14} color="var(--mantine-color-violet-4)" />
        <Text size="xs" c="dimmed" ff="monospace">steer the AI</Text>
      </Group>

      <Textarea
        placeholder="describe a mood, scene, or concept..."
        value={value}
        onChange={(e) => setValue(e.currentTarget.value)}
        onKeyDown={handleKey}
        minRows={2}
        maxRows={5}
        autosize
        styles={{
          input: {
            fontFamily: "monospace",
            fontSize: "var(--mantine-font-size-sm)",
            background: "var(--mantine-color-dark-8)",
            border: "1px solid var(--mantine-color-dark-5)",
          },
        }}
      />

      <Button
        onClick={submit}
        loading={loading}
        disabled={!value.trim()}
        color="violet"
        variant="light"
        size="xs"
        leftSection={<IconSparkles size={12} />}
        fullWidth
      >
        Send prompt  <Text span c="dimmed" size="xs" ml={4}>(⌘↵)</Text>
      </Button>

      {feedback && (
        <Text
          size="xs"
          c={feedback.startsWith("Failed") ? "red.4" : "teal.4"}
          ff="monospace"
        >
          {feedback}
        </Text>
      )}

      {/* Suggestion chips */}
      <Box>
        <Text size="xs" c="dark.4" mb={4} ff="monospace">try:</Text>
        <Group gap={4} wrap="wrap">
          {SUGGESTIONS.map((s) => (
            <Box
              key={s}
              component="button"
              onClick={() => setValue(s)}
              style={{
                background: "var(--mantine-color-dark-7)",
                border: "1px solid var(--mantine-color-dark-5)",
                borderRadius: 4,
                padding: "2px 8px",
                cursor: "pointer",
                color: "var(--mantine-color-dark-2)",
                fontSize: "var(--mantine-font-size-xs)",
                fontFamily: "monospace",
              }}
            >
              {s}
            </Box>
          ))}
        </Group>
      </Box>
    </Stack>
  );
}
