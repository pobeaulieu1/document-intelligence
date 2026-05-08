import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileText, X, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { uploadDocument } from "../api";
import { t } from "../theme";
import type { Extraction } from "../types";

interface Props {
  schemaKey: string;
  onSuccess: (doc: Extraction) => void;
  onClose: () => void;
}

const ACCEPT = {
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/webp": [".webp"],
  "image/gif": [".gif"],
  "application/pdf": [".pdf"],
};

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

const STEPS = ["Uploading file", "Extracting data", "Classifying expense", "Validating rules"];

export function UploadModal({ schemaKey, onSuccess, onClose }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState(0);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (f: File) => {
      // Simulate progress through steps while the real request runs
      const interval = setInterval(() => {
        setStep((s) => (s < STEPS.length - 1 ? s + 1 : s));
      }, 2200);
      try {
        return await uploadDocument(schemaKey, f);
      } finally {
        clearInterval(interval);
      }
    },
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ["documents", schemaKey] });
      onSuccess(doc);
    },
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024,
    disabled: mutation.isPending,
  });

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-sm"
        onClick={!mutation.isPending ? onClose : undefined}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-md bg-white rounded-2xl shadow-modal overflow-hidden animate-fade-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-5">
          <h2 className={t.modalTitle}>Upload Receipt</h2>
          {!mutation.isPending && (
            <button onClick={onClose} className="text-gray-300 hover:text-gray-600 transition-colors">
              <X size={18} />
            </button>
          )}
        </div>

        <div className="px-6 pb-6 space-y-4">
          {mutation.isPending ? (
            /* ── Processing state ──────────────────────────────────── */
            <div className="py-8 space-y-6">
              <div className="flex justify-center">
                <div className="relative">
                  <div className="w-14 h-14 rounded-full border-2 border-brand-100 flex items-center justify-center">
                    <Loader2 size={24} className="text-brand-600 animate-spin" />
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                {STEPS.map((s, i) => (
                  <div key={s} className="flex items-center gap-3 text-sm">
                    {i < step ? (
                      <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                    ) : i === step ? (
                      <Loader2 size={15} className="text-brand-600 animate-spin shrink-0" />
                    ) : (
                      <span className="w-[15px] h-[15px] rounded-full border-2 border-gray-200 shrink-0" />
                    )}
                    <span className={i <= step ? "text-gray-900 font-medium" : "text-gray-400"}>
                      {s}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* ── Drop zone ──────────────────────────────────────── */}
              <div
                {...getRootProps()}
                className={`
                  border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all
                  ${isDragActive
                    ? "border-brand-400 bg-brand-50 scale-[1.01]"
                    : file
                    ? "border-emerald-300 bg-emerald-50/50"
                    : "border-gray-200 hover:border-brand-300 hover:bg-gray-50/80"
                  }
                `}
              >
                <input {...getInputProps()} />
                <UploadCloud
                  size={30}
                  className={`mx-auto mb-3 ${isDragActive ? "text-brand-500" : "text-gray-300"}`}
                />
                {isDragActive ? (
                  <p className="text-brand-600 font-semibold">Drop it here</p>
                ) : (
                  <>
                    <p className="font-semibold text-gray-700">
                      Drag & drop or{" "}
                      <span className="text-brand-600">browse</span>
                    </p>
                    <p className="text-xs text-gray-400 mt-1.5">
                      JPEG · PNG · WebP · PDF &nbsp;·&nbsp; max 20 MB
                    </p>
                  </>
                )}
              </div>

              {/* Selected file */}
              {file && (
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="w-9 h-9 rounded-lg bg-brand-100 flex items-center justify-center shrink-0">
                    <FileText size={16} className="text-brand-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                    <p className="text-xs text-gray-400">{formatBytes(file.size)}</p>
                  </div>
                  <button onClick={() => setFile(null)} className="text-gray-300 hover:text-gray-500 transition-colors">
                    <X size={15} />
                  </button>
                </div>
              )}

              {/* Error */}
              {mutation.isError && (
                <div className="flex items-center gap-2 p-3 bg-red-50 rounded-xl text-red-600 text-sm border border-red-100">
                  <AlertCircle size={15} className="shrink-0" />
                  {mutation.error.message}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2.5 pt-1">
                <button onClick={onClose} className={`flex-1 justify-center ${t.btnOutline}`}>
                  Cancel
                </button>
                <button
                  onClick={() => { if (file) { setStep(0); mutation.mutate(file); } }}
                  disabled={!file}
                  className={`flex-1 justify-center ${t.btnPrimary} disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  Process Receipt
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
