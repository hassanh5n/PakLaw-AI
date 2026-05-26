"use client";

import { UploadCloud } from "lucide-react";
import { useState } from "react";
import { uploadFirmPdf } from "../lib/api";

export default function UploadPanel({ user }) {
  const [file, setFile] = useState(null);
  const [firmId, setFirmId] = useState(user?.firm_id || "firm_alpha");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  if (user?.role !== "admin") {
    return null;
  }

  async function submit(event) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setStatus("");
    try {
      const result = await uploadFirmPdf({ file, firmId, accessLevel: "firm" });
      setStatus(result.message);
    } catch (err) {
      setStatus(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="upload-panel" onSubmit={submit}>
      <div className="section-label">Firm Vault Upload</div>
      <label className="drop-zone">
        <UploadCloud size={22} />
        <span>{file ? file.name : "Drop or select PDF"}</span>
        <input accept="application/pdf" type="file" onChange={(event) => setFile(event.target.files?.[0] || null)} />
      </label>
      <input value={firmId} onChange={(event) => setFirmId(event.target.value)} />
      <button className="secondary-button" disabled={!file || busy} type="submit">
        {busy ? "Indexing" : "Upload"}
      </button>
      {status && <p className="upload-status">{status}</p>}
    </form>
  );
}

