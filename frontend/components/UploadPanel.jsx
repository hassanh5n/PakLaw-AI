"use client";

import { UploadCloud, X, FileText } from "lucide-react";
import { useState } from "react";
import { uploadFirmPdf } from "../lib/api";

export default function UploadPanel({ user }) {
  const [files, setFiles] = useState([]);
  const [firmId, setFirmId] = useState(user?.firm_id || "firm_alpha");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  if (!user || user.role === "public") {
    return null;
  }

  function handleFiles(event) {
    const selected = Array.from(event.target.files || []);
    setFiles((prev) => {
      const existingNames = new Set(prev.map((f) => f.name));
      const newFiles = selected.filter((f) => !existingNames.has(f.name));
      return [...prev, ...newFiles];
    });
    event.target.value = "";
  }

  function removeFile(index) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function submit(event) {
    event.preventDefault();
    if (files.length === 0) return;
    setBusy(true);
    setStatus("");
    const results = [];
    for (const file of files) {
      try {
        const result = await uploadFirmPdf({
          file,
          firmId,
          accessLevel: "firm",
        });
        results.push(`✓ ${file.name}: ${result.message}`);
      } catch (err) {
        results.push(`✗ ${file.name}: ${err.message}`);
      }
    }
    setStatus(results.join("\n"));
    setFiles([]);
    setBusy(false);
  }

  return (
    <form className="upload-panel liquid-glass" onSubmit={submit}>
      <div className="section-label">Firm Vault Upload</div>
      <label className="drop-zone">
        <UploadCloud size={22} />
        <span>
          {files.length > 0
            ? `${files.length} file${files.length > 1 ? "s" : ""} selected`
            : "Drop or select PDFs"}
        </span>
        <span className="drop-zone-hint">Supports multiple files</span>
        <input
          accept="application/pdf"
          type="file"
          multiple
          onChange={handleFiles}
        />
      </label>

      {files.length > 0 && (
        <div className="file-list">
          {files.map((file, index) => (
            <div className="file-item" key={`${file.name}-${index}`}>
              <FileText size={14} />
              <span>{file.name}</span>
              <button
                className="file-remove"
                type="button"
                onClick={() => removeFile(index)}
                aria-label={`Remove ${file.name}`}
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      )}

      <input
        value={firmId}
        onChange={(event) => setFirmId(event.target.value)}
        placeholder="Firm ID"
      />
      <button
        className="primary-button"
        disabled={files.length === 0 || busy}
        type="submit"
      >
        {busy
          ? `Indexing ${files.length} file${files.length > 1 ? "s" : ""}...`
          : `Upload ${files.length > 0 ? files.length : ""} file${files.length !== 1 ? "s" : ""}`}
      </button>
      {status && (
        <pre className="upload-status" style={{ whiteSpace: "pre-wrap", fontSize: "12px" }}>
          {status}
        </pre>
      )}
    </form>
  );
}
