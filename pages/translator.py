import streamlit as st
import docx
import PyPDF2
from PIL import Image
import pytesseract
import requests
import os
import argostranslate.package
import argostranslate.translate

from models import TranslationResult
from config import MESSAGES, TRANSLATOR_CONFIG
from utils import initial_page_config
from components import render_language_selector
from message import TRANSLATOR_MESSAGES

# Set user-writable model path
os.environ["ARGOS_TRANSLATE_PACKAGE_PATH"] = os.path.expanduser("~/.argosmodels")

# Ensure models are available
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()

language_pairs = [("en", "zh"), ("zh", "en"), ("en", "zh-Hant"), ("zh-Hant", "en"),
                  ("en", "de"), ("de", "en"), ("en", "es"), ("es", "en"),
                  ("zh", "zh-Hant"), ("zh-Hant", "zh")]

for from_code, to_code in language_pairs:
    if not any(pkg.from_code == from_code and pkg.to_code == to_code
               for pkg in argostranslate.package.get_installed_packages()):
        package = next(
            (pkg for pkg in available_packages if pkg.from_code == from_code and pkg.to_code == to_code),
            None
        )
        if package:
            argostranslate.package.install_from_path(package.download())

# 获取语言和本地化字典
lang = st.session_state.get("language", "zh-CN")
T = TRANSLATOR_MESSAGES[lang]

# 支持语言映射
LANGUAGE_CODE_MAP = {
    "Auto Detect": "auto",
    "English": "en",
    "Chinese (Simplified)": "zh",
    "Chinese (Traditional)": "zh-Hant",
    "German": "de",
    "Spanish": "es"
}

# 翻译函数
@st.cache_resource
def argos_translate(text, source_lang, target_lang):
    source_code = LANGUAGE_CODE_MAP.get(source_lang, "en")
    target_code = LANGUAGE_CODE_MAP.get(target_lang, "zh")

    if source_code == target_code:
        return TranslationResult(text, text, source_lang, target_lang)

    try:
        translated = argostranslate.translate.translate(text, source_code, target_code)
        return TranslationResult(text, translated, source_lang, target_lang)
    except Exception as e:
        return TranslationResult(text, f"[Translate Error]: {e}", source_lang, target_lang)


@st.cache_data
def get_translator_config():
    return TRANSLATOR_CONFIG

# 页面标题
st.header(T["title"])

# 语言选择
source_lang, target_lang = render_language_selector(lang=lang)

# 标签页
tab1, tab2, tab3, tab4 = st.tabs([T["tabText"], T["tabDoc"], T["tabImg"], T["tabWeb"]])

# 文本翻译
with tab1:
    input_text = st.text_area(T["inputText"], height=150, placeholder=T["textPlaceholder"])
    if st.button(T["translateText"]):
        if input_text:
            with st.spinner(T["translating"]):
                result = argos_translate(input_text, source_lang, target_lang)
                st.text_area(T["translatedResult"], value=result.translated_text, height=150)
        else:
            st.warning(T["emptyTextWarning"])

# 文档翻译
with tab2:
    uploaded_file = st.file_uploader(T["uploadDocument"], type=TRANSLATOR_CONFIG["file_types"][:3])
    if uploaded_file and st.button(T["translateDocument"]):
        with st.container():
            try:
                if uploaded_file.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    text = "".join([page.extract_text() for page in pdf_reader.pages])
                elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = docx.Document(uploaded_file)
                    text = "\n".join([para.text for para in doc.paragraphs])
                elif uploaded_file.type == "text/plain":
                    text = uploaded_file.read().decode("utf-8")
                else:
                    st.error(T["unsupportedFile"])
                    text = None

                if text:
                    with st.spinner(T["translating"]):
                        result = argos_translate(text, source_lang, target_lang)
                        st.text_area(T["translatedResult"], value=result.translated_text, height=300)
            except Exception as e:
                st.error(f"{T['translationFailed']}: {str(e)}")

# 图片翻译
with tab3:
    uploaded_image = st.file_uploader(T["uploadImage"], type=TRANSLATOR_CONFIG["file_types"][3:])
    if uploaded_image and st.button(T["translateImage"]):
        try:
            image = Image.open(uploaded_image)
            text = pytesseract.image_to_string(image)
            if text:
                with st.spinner(T["translating"]):
                    result = argos_translate(text, source_lang, target_lang)
                    st.text_area(T["extractedText"], value=text, height=150)
                    st.text_area(T["translatedResult"], value=result.translated_text, height=150)
            else:
                st.warning(T["noTextExtracted"])
        except Exception as e:
            st.error(f"{T['translationFailed']}: {str(e)}")

# 网页翻译
with tab4:
    url = st.text_input(T["inputUrl"], placeholder="https://example.com")
    if url and st.button(T["translateWeb"]):
        text = f"模拟网页内容: {url}"
        with st.spinner(T["translating"]):
            result = argos_translate(text, source_lang, target_lang)
            st.text_area(T["translatedResult"], value=result.translated_text, height=300)

# 使用说明
st.markdown(T["usageInstructions"], unsafe_allow_html=True)
