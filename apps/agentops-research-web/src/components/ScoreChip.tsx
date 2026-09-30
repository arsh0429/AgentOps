interface ScoreChipProps {
  score: number;
}

export default function ScoreChip({ score }: ScoreChipProps) {
  // Scale from light sage (low) to deep sage (high) — no red/green polarity
  const clamped = Math.max(0, Math.min(1, score));
  const lightness = Math.round(88 - clamped * 38); // 88% → 50%
  const saturation = Math.round(18 + clamped * 20); // 18% → 38%
  const bg = `hsl(120, ${saturation}%, ${lightness}%)`;
  const textL = lightness < 68 ? 98 : 30;
  const color = `hsl(120, 15%, ${textL}%)`;

  return (
    <span
      className="score-chip"
      style={{ background: bg, color }}
      title={`Score: ${score.toFixed(2)}`}
    >
      {score.toFixed(1)}
    </span>
  );
}
