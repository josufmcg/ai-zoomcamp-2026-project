import { createContext, useContext } from "react";

import en from "./en.json";
import es from "./es.json";

export type Language = "en" | "es";

export const LANGUAGE_STORAGE_KEY = "efinges.language";

const translations: Record<Language, Record<string, string>> = { en, es };

interface I18nContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (message: string, values?: Record<string, string | number>) => string;
}

export const I18nContext = createContext<I18nContextValue | null>(null);

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}

export function translate(
  message: string,
  language: Language,
  values?: Record<string, string | number>,
): string {
  const translated = translations[language][message] ?? message;
  return values
    ? translated.replace(/\{\{(\w+)\}\}/g, (placeholder, key: string) =>
        String(values[key] ?? placeholder),
      )
    : translated;
}
