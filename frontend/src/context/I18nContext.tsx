/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, type ReactNode } from 'react';

type Language = 'en' | 'hi';

interface I18nContextType {
    language: Language;
    setLanguage: (lang: Language) => void;
    t: (key: string) => string;
}

const translations: Record<Language, Record<string, string>> = {
    en: {
        "dashboard.title": "Financial Overview",
        "dashboard.subtitle": "Your financial health at a glance (privacy-masked)",
        "metric.net_worth": "Net Worth",
        "metric.credit_score": "Credit Score",
        "metric.savings_rate": "Savings Rate",
        "metric.utilization": "Credit Utilization",
        "section.assets": "Assets",
        "section.liabilities": "Liabilities",
        "section.cash_flow": "Monthly Cash Flow",
        "label.income_band": "Income Band",
        "label.expense_band": "Expense Band",
        "label.top_expenses": "Top Expenses",
        "privacy.title": "Privacy Protected",
        "privacy.desc": "All values shown are privacy-masked bands. Raw financial data is never exposed.",
        "chat.placeholder": "Ask about stocks, graph relations, or request analysis...",
        "chat.send": "Send",
        "chat.listening": "Listening...",
        "action.export_csv": "Export CSV",
        "action.print": "Print Report"
    },
    hi: {
        "dashboard.title": "वित्तीय अवलोकन",
        "dashboard.subtitle": "आपकी वित्तीय स्थिति एक नज़र में (गोपनीयता-सुरक्षित)",
        "metric.net_worth": "कुल संपत्ति",
        "metric.credit_score": "क्रेडिट स्कोर",
        "metric.savings_rate": "बचत दर",
        "metric.utilization": "क्रेडिट उपयोग",
        "section.assets": "संपत्ति",
        "section.liabilities": "देनदारियां",
        "section.cash_flow": "मासिक नकदी प्रवाह",
        "label.income_band": "आय श्रेणी",
        "label.expense_band": "व्यय श्रेणी",
        "label.top_expenses": "प्रमुख खर्च",
        "privacy.title": "गोपनीयता सुरक्षित",
        "privacy.desc": "दिखाए गए सभी मान गोपनीयता-सुरक्षित श्रेणियां हैं। कच्चा वित्तीय डेटा कभी भी उजागर नहीं किया जाता है।",
        "chat.placeholder": "स्टॉक, ग्राफ संबंधों या विश्लेषण के बारे में पूछें...",
        "chat.send": "भेजें",
        "chat.listening": "सुन रहा हूँ...",
        "action.export_csv": "CSV निर्यात करें",
        "action.print": "रिपोर्ट प्रिंट करें"
    }
};

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export const I18nProvider = ({ children }: { children: ReactNode }) => {
    const [language, setLanguage] = useState<Language>('en');

    const t = (key: string) => {
        return translations[language][key] || key;
    };

    return (
        <I18nContext.Provider value={{ language, setLanguage, t }}>
            {children}
        </I18nContext.Provider>
    );
};

export const useI18n = () => {
    const context = useContext(I18nContext);
    if (context === undefined) {
        throw new Error('useI18n must be used within a I18nProvider');
    }
    return context;
};
