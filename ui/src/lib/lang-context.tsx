import { createContext, useContext } from "react";

export type UILang = "en" | "zh";

export const LangContext = createContext<UILang>("en");

export function LangProvider({
  value,
  children,
}: {
  value: UILang;
  children: React.ReactNode;
}) {
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): UILang {
  return useContext(LangContext);
}
