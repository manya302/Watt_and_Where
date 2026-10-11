import { useEffect, useState } from "react";
import { STRINGS } from "../strings.js";

const SIZE_OPTIONS = [
  { value: "normal", label: "A", description: "Standard text" },
  { value: "large", label: "A+", description: "Larger text" },
  { value: "largest", label: "A++", description: "Largest text" },
];

export default function TextSizeControl() {
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("watt-where-text-size");
      return SIZE_OPTIONS.some((option) => option.value === saved)
        ? saved
        : "normal";
    } catch {
      return "normal";
    }
  });

  useEffect(() => {
    document.documentElement.dataset.textSize = size;

    try {
      localStorage.setItem("watt-where-text-size", size);
    } catch {
      // The control still works if browser storage is unavailable.
    }
  }, [size]);

  return (
    <div
      className="text-size-control"
      role="group"
      aria-label={STRINGS.dashboard?.textSizeLabel || "Text size"}
    >
      <span>
        {STRINGS.dashboard?.textSizeLabel || "Text size"}
      </span>

      {SIZE_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`text-size-button ${
            size === option.value ? "is-active" : ""
          }`}
          aria-pressed={size === option.value}
          aria-label={option.description}
          title={option.description}
          onClick={() => setSize(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}