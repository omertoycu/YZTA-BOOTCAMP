"use client";

import { useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Şehir/ilçe/mahalle için prefix-arama otomatik tamamlama alanı.
 * "B" yazınca B ile başlayan tüm sonuçlar backend'in statik Türkiye
 * sözlüğünden gelir (GET /geo/*). Debounce'lu; eski isteğin geç gelen
 * yanıtı yenisini ezmesin diye sıra numarası kontrol edilir.
 */
export function LocationAutocomplete({
  id,
  label,
  value,
  onChange,
  endpoint,
  params = {},
  placeholder,
  disabled = false,
  autoFocus = false,
}: {
  id: string;
  label?: string;
  value: string;
  onChange: (value: string) => void;
  endpoint: "/geo/cities" | "/geo/districts" | "/geo/neighborhoods";
  params?: Record<string, string>;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
}) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);
  const requestSeq = useRef(0);
  const containerRef = useRef<HTMLDivElement>(null);
  // Öneriden seçim yapılınca dropdown'ın hemen yeniden açılmaması için
  const skipNextFetch = useRef(false);

  const paramsKey = JSON.stringify(params);

  useEffect(() => {
    if (skipNextFetch.current) {
      skipNextFetch.current = false;
      return;
    }
    if (disabled || value.trim() === "") {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }
    const seq = ++requestSeq.current;
    const timer = setTimeout(async () => {
      try {
        const query = new URLSearchParams({ q: value.trim(), ...JSON.parse(paramsKey) });
        const results = await apiFetch<string[]>(`${endpoint}?${query.toString()}`);
        if (seq !== requestSeq.current) return;
        setSuggestions(results);
        // Tek sonuç tam eşleşmeyse liste göstermeye gerek yok
        const exactOnly = results.length === 1 && results[0].toLocaleLowerCase("tr-TR") === value.trim().toLocaleLowerCase("tr-TR");
        setIsOpen(results.length > 0 && !exactOnly);
        setHighlighted(-1);
      } catch {
        if (seq === requestSeq.current) setIsOpen(false);
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [value, endpoint, paramsKey, disabled]);

  // Dışarı tıklanınca kapat
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function select(suggestion: string) {
    skipNextFetch.current = true;
    onChange(suggestion);
    setIsOpen(false);
    setHighlighted(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!isOpen || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((h) => (h + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((h) => (h <= 0 ? suggestions.length - 1 : h - 1));
    } else if (e.key === "Enter" && highlighted >= 0) {
      e.preventDefault();
      select(suggestions[highlighted]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  }

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="font-label text-label-caps text-on-surface-variant">
          {label}
        </label>
      )}
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={isOpen}
        aria-autocomplete="list"
        autoComplete="off"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        className={cn(
          "h-10 w-full rounded border border-outline-variant bg-surface-container-lowest px-3 text-body-sm text-on-surface placeholder:text-text-muted transition-shadow focus:border-secondary focus:outline-none focus:ring-2 focus:ring-secondary-container",
          disabled && "cursor-not-allowed opacity-60"
        )}
      />
      {isOpen && (
        <ul
          role="listbox"
          className="absolute top-full z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-lowest py-1 shadow-lg"
        >
          {suggestions.map((suggestion, i) => (
            <li key={suggestion}>
              <button
                type="button"
                role="option"
                aria-selected={i === highlighted}
                // onClick yerine onMouseDown: input blur'undan önce çalışsın
                onMouseDown={(e) => {
                  e.preventDefault();
                  select(suggestion);
                }}
                onMouseEnter={() => setHighlighted(i)}
                className={cn(
                  "w-full px-3 py-2 text-left text-body-sm text-on-surface",
                  i === highlighted ? "bg-mint-accent" : "hover:bg-surface-container"
                )}
              >
                {suggestion}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
