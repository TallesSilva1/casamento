import streamlit as st
import pandas as pd
import json
import urllib.parse
import os
from datetime import datetime
from supabase import create_client, Client, ClientOptions
import streamlit.components.v1 as components

# -------------------------------
# Configurações básicas
# -------------------------------
NOME_DOS_NOIVOS = "Ana Paula & Talles"
DATA_DO_CASAMENTO = "15 de Agosto de 2026, 16:00"
MENSAGEM_BOAS_VINDAS = """Sejam bem vindos ao nosso site!

Estamos muito felizes em ter vocês aqui. Criamos este cantinho com carinho para compartilhar um pouco da nossa história e reunir todas as informações do nosso grande dia.

Esperamos que este site ajude vocês a se preparar para celebrar, rir, dançar e viver esse momento especial com a gente.
A presença de vocês já torna tudo ainda mais bonito, mal podemos esperar por esse dia!

Com carinho,

Ana Paula e Talles"""
CHAVE_PIX = "casamento@exemplo.com"
MENSAGEM_PIX = "Se preferir presente em Pix, use a chave acima. Obrigado pelo carinho!"
ENDERECO_CERIMONIA = "Paróquia São Cristovão, R. Padre Américo Ceppi, 190, Centro, Uberlândia"
HORARIO_CERIMONIA = "16:00"
ENDERECO_FESTA = "Espaço Parnassus, R. do Prata, 1703 - Chacaras Bonanza"
HORARIO_FESTA = "19:00"

# -------------------------------
# Configuração da página
# — DEVE ser o primeiro comando st.*
# -------------------------------
st.set_page_config(
    page_title=f"{NOME_DOS_NOIVOS}",
    page_icon="💍",
    layout="centered",
)

# ================================================================
# CONTROLE DA ANIMAÇÃO
# ================================================================

# ================================================================
# HOMEPAGE — CARTÃO ANIMADO
#
# Lê o index.html da mesma pasta e injeta via st.markdown.
# Mesmo domínio → JS tem acesso direto ao DOM do Streamlit.
#
# Fluxo:
#   Usuário clica no cartão → animação CSS 3D abre
#   → botão "Entrar no Site" → entrarNoSite() →
#   → fade-out → clica no st.button oculto "___ENTRAR___" →
# ================================================================

# ── CSS: esconde todo o chrome ───────────────────────────────────────────

with open("Entrada.html", "r", encoding="utf-8") as f:
    html_content = f.read()

components.html(html_content, height=800, scrolling=False)

# Botão real do Streamlit — o JS acima adiciona .hp-visivel para revelá-lo
if st.button("✦  Entrar no Site  ✦", key="__entrar__"):
    st.switch_page("pages/Site.py")