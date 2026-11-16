import { useTranslation } from "react-i18next";
import { useTranslit } from "./translitContext";

/** Quick "Show pronunciation" switch for the lesson view. Renders nothing for languages without a store. */
export function TranslitToggle() {
  const { t } = useTranslation();
  const { show, available, setShow } = useTranslit();
  if (!available) return null;
  return (
    <button
      type="button"
      className="btn btn-secondary translit-toggle"
      aria-pressed={show}
      onClick={() => setShow(!show)}
      title={t("translit.show_label")}
    >
      {show ? t("translit.toggle_on") : t("translit.toggle_off")}
    </button>
  );
}
