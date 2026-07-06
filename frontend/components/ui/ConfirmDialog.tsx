"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDestructive?: boolean;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

// Tarayıcının native confirm()'ü yerine ürüne uygun, tasarım sistemiyle
// tutarlı bir onay modalı — silme gibi geri alınamaz işlemler için kullanılır.
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Sil",
  cancelLabel = "Vazgeç",
  isDestructive = true,
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    if (!open) return;
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
        className="w-full max-w-sm rounded-lg bg-surface-container-lowest p-6 shadow-[0px_20px_50px_rgba(0,0,0,0.18)]"
      >
        <div className="flex items-start gap-3">
          <span
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${
              isDestructive ? "bg-error-container text-error" : "bg-mint-accent text-secondary"
            }`}
          >
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div className="flex flex-col gap-1 pt-1">
            <h2 id="confirm-dialog-title" className="text-title-md text-on-surface">
              {title}
            </h2>
            <p id="confirm-dialog-description" className="text-body-sm text-text-muted">
              {description}
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel} disabled={isLoading}>
            {cancelLabel}
          </Button>
          <Button variant={isDestructive ? "destructive" : "primary"} onClick={onConfirm} isLoading={isLoading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
