"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface ApiKey {
  id: string;
  name: string;
  description: string;
  key_prefix: string;
  permissions: string[];
  created_at: string;
  last_used_at: string | null;
}

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [step, setStep] = useState(1);
  const [keyName, setKeyName] = useState("");
  const [keyDesc, setKeyDesc] = useState("");
  const [permissions, setPermissions] = useState<string[]>([]);
  const [newKey, setNewKey] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [keyCopied, setKeyCopied] = useState(false);

  const fetchKeys = () => {
    api.getKeys().then(setKeys).catch(() => {});
  };

  useEffect(() => { fetchKeys(); }, []);

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleCreate = async () => {
    try {
      const result = await api.createKey({
        name: keyName,
        description: keyDesc,
        permissions,
      });
      setNewKey(result.key);
      setStep(3);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to create key");
    }
  };

  const handleDelete = async (keyId: string) => {
    await api.deleteKey(keyId);
    setDeleteConfirm(null);
    fetchKeys();
  };

  const closeModal = () => {
    if (step === 3 && !keyCopied) return; // Must copy first
    setShowCreate(false);
    setStep(1);
    setKeyName("");
    setKeyDesc("");
    setPermissions([]);
    setNewKey("");
    setKeyCopied(false);
    fetchKeys();
  };

  const togglePerm = (p: string) => {
    setPermissions((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition text-sm font-medium"
        >
          + Create New Key
        </button>
      </div>

      {/* Keys table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left py-3 px-4 text-gray-500 font-medium">Name</th>
                <th className="text-left py-3 px-4 text-gray-500 font-medium">Key</th>
                <th className="text-left py-3 px-4 text-gray-500 font-medium">Created</th>
                <th className="text-left py-3 px-4 text-gray-500 font-medium">Last Used</th>
                <th className="text-left py-3 px-4 text-gray-500 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((key) => (
                <tr key={key.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4 font-medium text-gray-900">{key.name}</td>
                  <td className="py-3 px-4 font-mono text-gray-600">{key.key_prefix}...</td>
                  <td className="py-3 px-4 text-gray-600">{new Date(key.created_at).toLocaleDateString()}</td>
                  <td className="py-3 px-4 text-gray-600">{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : "Never"}</td>
                  <td className="py-3 px-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleCopy(key.key_prefix, key.id)}
                        className="text-gray-500 hover:text-gray-700 text-xs border border-gray-300 px-2 py-1 rounded"
                      >
                        {copied === key.id ? "Copied!" : "Copy"}
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(key.id)}
                        className="text-red-500 hover:text-red-700 text-xs border border-red-300 px-2 py-1 rounded"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {keys.length === 0 && (
                <tr><td colSpan={5} className="py-8 text-center text-gray-500">No API keys yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete confirm dialog */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-sm mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete API Key?</h3>
            <p className="text-gray-600 text-sm mb-6">This action cannot be undone. Any applications using this key will stop working.</p>
            <div className="flex gap-3 justify-end">
              <button onClick={() => setDeleteConfirm(null)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                Cancel
              </button>
              <button onClick={() => handleDelete(deleteConfirm)} className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create key modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-6">
              {[1, 2, 3].map((s) => (
                <div key={s} className={`flex-1 h-1 rounded-full ${s <= step ? "bg-indigo-600" : "bg-gray-200"}`} />
              ))}
            </div>

            {step === 1 && (
              <>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Create API Key</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                    <input
                      value={keyName}
                      onChange={(e) => setKeyName(e.target.value)}
                      placeholder="e.g., Production Key"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <input
                      value={keyDesc}
                      onChange={(e) => setKeyDesc(e.target.value)}
                      placeholder="Optional description"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    />
                  </div>
                </div>
                <div className="flex gap-3 justify-end mt-6">
                  <button onClick={closeModal} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                    Cancel
                  </button>
                  <button
                    onClick={() => setStep(2)}
                    disabled={!keyName.trim()}
                    className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Permissions</h3>
                <div className="space-y-3">
                  {["read", "write", "delete", "admin"].map((p) => (
                    <label key={p} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={permissions.includes(p)}
                        onChange={() => togglePerm(p)}
                        className="w-4 h-4 text-indigo-600 rounded border-gray-300"
                      />
                      <span className="text-sm capitalize text-gray-900">{p}</span>
                    </label>
                  ))}
                </div>
                <div className="flex gap-3 justify-end mt-6">
                  <button onClick={() => setStep(1)} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                    Back
                  </button>
                  <button
                    onClick={handleCreate}
                    disabled={permissions.length === 0}
                    className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Create
                  </button>
                </div>
              </>
            )}

            {step === 3 && (
              <>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Your API Key</h3>
                <p className="text-sm text-amber-600 mb-4">
                  This is the only time you&apos;ll see the full key. Copy it now!
                </p>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 font-mono text-sm break-all">
                  {newKey}
                </div>
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(newKey);
                    setKeyCopied(true);
                  }}
                  className={`mt-3 w-full py-2 rounded-lg text-sm font-medium transition ${
                    keyCopied
                      ? "bg-green-600 text-white"
                      : "bg-indigo-600 text-white hover:bg-indigo-700"
                  }`}
                >
                  {keyCopied ? "Copied!" : "Copy to Clipboard"}
                </button>
                <div className="flex justify-end mt-4">
                  <button
                    onClick={closeModal}
                    disabled={!keyCopied}
                    className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
                  >
                    Close
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
