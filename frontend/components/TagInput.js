// components/TagInput.js — Chip/tag input for skills
// Usage:
//   <TagInput tags={skills} onChange={setSkills} placeholder="e.g. React, Node" />
//   `tags`   — string[], controlled
//   onChange — (string[]) => void

import { useState, useRef } from "react";

export default function TagInput({ tags = [], onChange, placeholder = "Type a skill…", disabled = false }) {
  const [input, setInput] = useState("");
  const inputRef = useRef(null);

  function addTag(raw) {
    const trimmed = raw.trim().replace(/^,+|,+$/g, "");
    if (!trimmed) return;
    const newTags = trimmed
      .split(",")
      .map(s => s.trim())
      .filter(s => s && !tags.includes(s));
    if (newTags.length) onChange([...tags, ...newTags]);
  }

  function removeTag(idx) {
    onChange(tags.filter((_, i) => i !== idx));
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addTag(input);
      setInput("");
    } else if (e.key === "Backspace" && !input && tags.length) {
      removeTag(tags.length - 1);
    }
  }

  function handleChange(e) {
    const val = e.target.value;
    // Space after a word = commit
    if (val.endsWith(" ") && val.trim()) {
      addTag(val);
      setInput("");
    } else {
      setInput(val);
    }
  }

  function handleBlur() {
    if (input.trim()) { addTag(input); setInput(""); }
  }

  return (
    <div
      onClick={() => inputRef.current?.focus()}
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
        padding: "8px 12px",
        minHeight: 46,
        background: "#F8FAFC",
        border: "1px solid #E2E8F0",
        borderRadius: 10,
        cursor: "text",
        alignItems: "center",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {tags.map((tag, i) => (
        <span key={i} style={{
          display: "inline-flex", alignItems: "center", gap: 4,
          background: "#EEF2FF", color: "#4F63D2",
          borderRadius: 20, padding: "3px 10px",
          fontSize: 12, fontWeight: 600,
        }}>
          {tag}
          {!disabled && (
            <button
              type="button"
              onClick={e => { e.stopPropagation(); removeTag(i); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#818CF8", fontSize: 14, lineHeight: 1, padding: 0, marginLeft: 2 }}
            >×</button>
          )}
        </span>
      ))}
      {!disabled && (
        <input
          ref={inputRef}
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder={tags.length === 0 ? placeholder : ""}
          style={{
            border: "none", outline: "none", background: "transparent",
            fontSize: 13, color: "#0F172A", flexGrow: 1, minWidth: 120,
          }}
        />
      )}
    </div>
  );
}
