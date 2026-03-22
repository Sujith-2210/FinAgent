"""
Internationalization (i18n) Service
Provides multi-language support for FinAgent.
Validates: Requirements 9.5
"""

from typing import Dict, Optional
from enum import Enum


class Language(str, Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    BENGALI = "bn"
    KANNADA = "kn"
    GUJARATI = "gu"


# Translation dictionaries
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "welcome": "Welcome to FinAgent",
        "portfolio_summary": "Portfolio Summary",
        "total_assets": "Total Assets",
        "total_liabilities": "Total Liabilities",
        "net_worth": "Net Worth",
        "savings_rate": "Savings Rate",
        "risk_level": "Risk Level",
        "recommendation": "Recommendation",
        "buy": "Buy",
        "sell": "Sell",
        "hold": "Hold",
        "high_risk": "High Risk",
        "medium_risk": "Medium Risk",
        "low_risk": "Low Risk",
        "goal_progress": "Goal Progress",
        "emergency_fund": "Emergency Fund",
        "retirement": "Retirement",
        "tax_saving": "Tax Saving",
        "monthly_income": "Monthly Income",
        "monthly_expense": "Monthly Expense",
        "loading": "Loading...",
        "error": "An error occurred",
        "try_again": "Please try again",
        "success": "Success",
        "failed": "Failed",
        "processing": "Processing your request",
        "ask_question": "Ask a financial question...",
        "send": "Send",
        "clear": "Clear",
        "export_pdf": "Export as PDF",
        "export_excel": "Export as Excel",
        "settings": "Settings",
        "language": "Language",
        "theme": "Theme",
        "dark_mode": "Dark Mode",
        "light_mode": "Light Mode",
    },
    "hi": {
        "welcome": "फिनएजेंट में आपका स्वागत है",
        "portfolio_summary": "पोर्टफोलियो सारांश",
        "total_assets": "कुल संपत्ति",
        "total_liabilities": "कुल देनदारियां",
        "net_worth": "कुल संपत्ति मूल्य",
        "savings_rate": "बचत दर",
        "risk_level": "जोखिम स्तर",
        "recommendation": "सिफारिश",
        "buy": "खरीदें",
        "sell": "बेचें",
        "hold": "रखें",
        "high_risk": "उच्च जोखिम",
        "medium_risk": "मध्यम जोखिम",
        "low_risk": "कम जोखिम",
        "goal_progress": "लक्ष्य प्रगति",
        "emergency_fund": "आपातकालीन निधि",
        "retirement": "सेवानिवृत्ति",
        "tax_saving": "कर बचत",
        "monthly_income": "मासिक आय",
        "monthly_expense": "मासिक खर्च",
        "loading": "लोड हो रहा है...",
        "error": "एक त्रुटि हुई",
        "try_again": "कृपया पुनः प्रयास करें",
        "success": "सफलता",
        "failed": "विफल",
        "processing": "आपका अनुरोध संसाधित हो रहा है",
        "ask_question": "वित्तीय प्रश्न पूछें...",
        "send": "भेजें",
        "clear": "साफ़ करें",
        "export_pdf": "पीडीएफ में निर्यात करें",
        "export_excel": "एक्सेल में निर्यात करें",
        "settings": "सेटिंग्स",
        "language": "भाषा",
        "theme": "थीम",
        "dark_mode": "डार्क मोड",
        "light_mode": "लाइट मोड",
    },
    "ta": {
        "welcome": "பினேஜெண்டுக்கு வரவேற்கிறோம்",
        "portfolio_summary": "போர்ட்ஃபோலியோ சுருக்கம்",
        "total_assets": "மொத்த சொத்துக்கள்",
        "net_worth": "நிகர மதிப்பு",
        "buy": "வாங்கு",
        "sell": "விற்கவும்",
        "hold": "வைத்திருக்க",
    },
    "te": {
        "welcome": "FinAgent కు స్వాగతం",
        "portfolio_summary": "పోర్ట్ఫోలియో సారాంశం",
        "total_assets": "మొత్తం ఆస్తులు",
        "net_worth": "నికర విలువ",
        "buy": "కొనండి",
        "sell": "అమ్మండి",
        "hold": "ఉంచండి",
    },
    "mr": {
        "welcome": "FinAgent मध्ये आपले स्वागत आहे",
        "portfolio_summary": "पोर्टफोलिओ सारांश",
        "total_assets": "एकूण मालमत्ता",
        "net_worth": "निव्वळ मूल्य",
        "buy": "खरेदी करा",
        "sell": "विक्री करा",
        "hold": "ठेवा",
    },
}


class I18nService:
    """
    Internationalization service for multi-language support.
    Validates: Requirements 9.5
    """
    
    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self.current_language = default_language
    
    def set_language(self, language: str) -> bool:
        """Set the current language."""
        if language in TRANSLATIONS:
            self.current_language = language
            return True
        return False
    
    def get_language(self) -> str:
        """Get the current language."""
        return self.current_language
    
    def get_supported_languages(self) -> list:
        """Get list of supported language codes."""
        return list(TRANSLATIONS.keys())
    
    def t(self, key: str, language: Optional[str] = None) -> str:
        """
        Translate a key to the specified or current language.
        Falls back to English if translation not found.
        """
        lang = language or self.current_language
        
        # Try requested language
        if lang in TRANSLATIONS and key in TRANSLATIONS[lang]:
            return TRANSLATIONS[lang][key]
        
        # Fall back to English
        if key in TRANSLATIONS["en"]:
            return TRANSLATIONS["en"][key]
        
        # Return key if no translation found
        return key
    
    def translate_dict(self, data: Dict, keys_to_translate: list, language: Optional[str] = None) -> Dict:
        """
        Translate specific keys in a dictionary.
        """
        translated = data.copy()
        for key in keys_to_translate:
            if key in translated and isinstance(translated[key], str):
                translated[key] = self.t(translated[key], language)
        return translated
    
    def format_currency(self, amount: float, language: Optional[str] = None) -> str:
        """
        Format currency according to language/locale.
        """
        lang = language or self.current_language
        
        if amount >= 10000000:  # 1 crore
            return f"₹{amount/10000000:.2f} Cr"
        elif amount >= 100000:  # 1 lakh
            return f"₹{amount/100000:.2f} L"
        else:
            return f"₹{amount:,.0f}"


# Singleton instance
i18n_service = I18nService()
