/** Converts HSV (0-360, 0-100, 0-100) to CSS hsl string. */
function hsvToCss(h: number, s: number, v: number): string {
  // HSV → HSL conversion
  const vn = v / 100;
  const sn = s / 100;
  const l = vn * (1 - sn / 2);
  const sl = l === 0 || l === 1 ? 0 : (vn - l) / Math.min(l, 1 - l);
  return `hsl(${h.toFixed(0)}, ${(sl * 100).toFixed(0)}%, ${(l * 100).toFixed(0)}%)`;
}

interface Props {
  hue: number;
  saturation: number;
  value: number;
  size?: number;
}

export function ColorSwatch({ hue, saturation, value, size = 48 }: Props) {
  const color = hsvToCss(hue, saturation, value);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: 8,
        background: color,
        boxShadow: `0 0 ${size * 0.6}px ${color}, 0 0 ${size * 0.2}px ${color}`,
        flexShrink: 0,
        transition: "background 0.4s ease, box-shadow 0.4s ease",
      }}
    />
  );
}
