const styles = {
  high: "confidence high",
  medium: "confidence medium",
  low: "confidence low",
};

export default function ConfidenceBadge({ value = "low" }) {
  return (
    <span className={styles[value] || styles.low}>{value} confidence</span>
  );
}
