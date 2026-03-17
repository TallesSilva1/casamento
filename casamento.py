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

# -------------------------------
# Conexão Supabase
# -------------------------------
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    if os.getenv("STREAMLIT_ENV") != "cloud":
        import httpx
        options = ClientOptions(httpx_client=httpx.Client(verify=False))
        return create_client(url, key, options)
    return create_client(url, key)

supabase = get_supabase()

# -------------------------------
# Funções Supabase
# -------------------------------
def salvar_rsvp(row: dict):
    supabase.table("rsvp").insert(row).execute()

def carregar_rsvp() -> pd.DataFrame:
    res = supabase.table("rsvp").select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["timestamp", "nome", "email", "telefone", "presenca", "qtd_pessoas", "mensagem", "acompanhantes"]
    )

def salvar_gift(row: dict):
    supabase.table("gifts").insert(row).execute()

def carregar_gifts() -> pd.DataFrame:
    res = supabase.table("gifts").select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["timestamp", "nome", "presente", "link", "mensagem"]
    )

def salvar_foto(nome_autor: str, filename: str, dados: bytes, content_type: str = "image/jpeg"):
    bucket = "photos"
    path = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}-{filename}"
    supabase.storage.from_(bucket).upload(path, dados, {"content-type": content_type})
    supabase_url = st.secrets["supabase"]["url"].rstrip("/")
    url = f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
    supabase.table("photos").insert({
        "timestamp": datetime.utcnow().isoformat(),
        "autor": nome_autor,
        "url": url,
        "filename": path,
    }).execute()
    return url

def carregar_fotos() -> pd.DataFrame:
    res = supabase.table("photos").select("*").order("timestamp", desc=True).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame(
        columns=["timestamp", "autor", "url", "filename"]
    )

# -------------------------------
# Funções utilitárias
# -------------------------------
def slugify(text: str) -> str:
    t = "".join(ch if ch.isalnum() else "-" for ch in text.lower())
    t = "-".join(filter(None, t.split("-")))
    return t[:60]

def human_time(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return ts


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
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Dancing+Script:wght@500;600&display=swap');

header[data-testid="stHeader"],
section[data-testid="stSidebar"],
#MainMenu, footer            { display:none !important; }
.block-container             { padding:0 !important; max-width:100% !important; }
.stApp                       { background:#fdfaf0 !important; }
.stMainBlockContainer        { padding:0 !important; }

/* ── Fundo aquarela ── */
.hp-bg {
    position:fixed; inset:0; z-index:0; pointer-events:none;
    background:
        radial-gradient(ellipse at 15% 10%, rgba(220,200,100,.18) 0%, transparent 45%),
        radial-gradient(ellipse at 85% 90%, rgba(200,180,80,.14)  0%, transparent 45%),
        linear-gradient(160deg, #fdfbec 0%, #f5eecc 50%, #ede4a8 100%);
}

/* ── Título topo ── */
.hp-topo { position:fixed; top:28px; left:50%; transform:translateX(-50%); text-align:center; z-index:10; pointer-events:none; animation:fadeDown .9s ease .2s both; }
.hp-eyebrow { font-family:'Cinzel',serif; font-size:clamp(8px,1.1vw,10px); letter-spacing:5px; color:#c9a84c; text-transform:uppercase; display:block; margin-bottom:5px; }
.hp-nomes   { font-family:'Dancing Script',cursive; font-size:clamp(22px,3.5vw,36px); color:#3a2008; display:block; }

/* ── Stage ── */
.hp-stage { position:fixed; inset:0; z-index:1; display:flex; align-items:center; justify-content:center; pointer-events:none; }

/* ── Cartão ── */
.hp-card {
    position:relative; width:clamp(260px,32vw,400px); aspect-ratio:3/4.2;
    cursor:pointer; transform-style:preserve-3d;
    filter:drop-shadow(0 20px 55px rgba(80,40,0,.22));
    animation:fadeUp .9s ease .4s both; pointer-events:all;
}
.hp-card:hover { filter:drop-shadow(0 28px 70px rgba(80,40,0,.3)); }

/* Interior */
.hp-interior {
    position:absolute; inset:0; border-radius:8px;
    background:linear-gradient(160deg,#fdfbf0 0%,#f8f2d8 55%,#f0e8c0 100%);
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    text-align:center; padding:10% 12%; z-index:0;
    opacity:0; transition:opacity .7s ease .8s;
}
.hp-interior::before { content:''; position:absolute; inset:14px; border:1px solid rgba(180,140,40,.3); border-radius:4px; }
.hp-interior::after  { content:''; position:absolute; inset:20px; border:1px solid rgba(180,140,40,.15); border-radius:2px; }
.hp-card.aberto .hp-interior { opacity:1; }
.hp-ci-eyebrow { font-family:'Cinzel',serif; font-size:clamp(7px,1vw,9px); letter-spacing:4px; color:#c9a84c; text-transform:uppercase; margin-bottom:10px; }
.hp-ci-nome    { font-family:'Dancing Script',cursive; font-size:clamp(20px,3.8vw,38px); color:#3a2008; line-height:1.1; }
.hp-ci-amp     { font-family:'Cormorant Garamond',serif; font-style:italic; font-size:clamp(26px,4.8vw,48px); color:#c9a84c; line-height:1; margin:-2px 0; }
.hp-ci-div     { width:40px; height:1px; background:linear-gradient(to right,transparent,#c9a84c,transparent); margin:10px auto; }
.hp-ci-data    { font-family:'Cinzel',serif; font-size:clamp(7px,1vw,9px); letter-spacing:3px; color:#5a3c18; margin-bottom:3px; }
.hp-ci-local   { font-family:'Cormorant Garamond',serif; font-style:italic; font-size:clamp(9px,1.4vw,13px); color:#7a5c30; margin-bottom:16px; }

/* Painéis */
.hp-panel { position:absolute; top:0; width:50%; height:100%; background:linear-gradient(160deg,#fdfbf0 0%,#f5eecc 55%,#ede4a8 100%); transform-style:preserve-3d; transition:transform 1.4s cubic-bezier(.25,.46,.45,.94); overflow:hidden; }
.hp-panel::after { content:''; position:absolute; inset:0; background:radial-gradient(ellipse at 30% 20%,rgba(255,255,255,.55) 0%,transparent 60%); pointer-events:none; }
.hp-esq { left:0;  transform-origin:left center;  border-radius:8px 0 0 8px; }
.hp-dir { right:0; transform-origin:right center; border-radius:0 8px 8px 0; }
.hp-esq::before { content:'';position:absolute;right:0;top:0;width:16px;height:100%;background:linear-gradient(to right,#e8dfa8,#d4c878,#b8a040,#d4c878,#e8dfa8);z-index:2; }
.hp-dir::before { content:'';position:absolute;left:0;top:0;width:16px;height:100%;background:linear-gradient(to left,#e8dfa8,#d4c878,#b8a040,#d4c878,#e8dfa8);z-index:2; }
.hp-card.aberto .hp-esq { transform:rotateY(-165deg); }
.hp-card.aberto .hp-dir { transform:rotateY(165deg); }

/* Flores */
.hp-flores { position:absolute; left:50%; top:3%; transform:translateX(-50%); width:82%; z-index:10; pointer-events:none; transition:transform .6s cubic-bezier(.34,1.56,.64,1), opacity .45s; }
.hp-flores img { width:100%; display:block; filter:drop-shadow(0 6px 18px rgba(80,40,0,.25)); }
.hp-card.aberto .hp-flores { transform:translateX(-50%) translateY(-20px) scale(1.05); opacity:0; }

/* Lacre */
.hp-lacre { position:absolute; left:50%; top:68%; transform:translate(-50%,-50%); z-index:20; display:flex; align-items:center; justify-content:center; animation:floatPulse 2.8s ease-in-out infinite; transition:opacity .4s, transform .4s; }
.hp-card.aberto .hp-lacre { opacity:0; transform:translate(-50%,-60%) scale(.55); pointer-events:none; }
.hp-disco { width:68px; height:68px; border-radius:50%; background:radial-gradient(circle at 35% 30%,#f0d060 0%,#c9a030 40%,#a07818 70%,#7a5810 100%); box-shadow:0 0 0 3px #b89028,0 0 0 6px rgba(200,160,40,.22),0 8px 28px rgba(0,0,0,.38),inset 0 2px 8px rgba(255,220,100,.5); }
.hp-lacre-svg { position:absolute; width:132px; height:132px; top:50%; left:50%; transform:translate(-50%,-50%); animation:rotateSeal 14s linear infinite; pointer-events:none; }

/* Hint */
.hp-hint { position:fixed; bottom:26px; left:50%; transform:translateX(-50%); font-family:'Cormorant Garamond',serif; font-style:italic; font-size:13px; letter-spacing:2px; color:rgba(120,80,20,.65); animation:blink 2.8s ease-in-out infinite; pointer-events:none; white-space:nowrap; z-index:50; transition:opacity .4s; }
.hp-hint.oculto { opacity:0 !important; animation:none !important; }

/* Pétalas */
.hp-petal { position:fixed; border-radius:50% 0 50% 0; pointer-events:none; animation:petalFall linear forwards; z-index:999; }

/* ── Botão Streamlit sobreposto ── */
div[data-testid="stVerticalBlock"] {
    position:fixed !important;
    top:50% !important; left:50% !important;
    transform:translate(-50%, 58px) !important;
    z-index:9999 !important;
    width:auto !important;
}
div[data-testid="stButton"] > button {
    background:transparent !important;
    border:1px solid #c9a84c !important;
    color:#7a5810 !important;
    font-family:'Cinzel',serif !important;
    letter-spacing:3px !important;
    font-size:9px !important;
    padding:10px 28px !important;
    border-radius:2px !important;
    text-transform:uppercase !important;
    opacity:0;
    transition:opacity .6s ease, background .25s, color .25s !important;
    pointer-events:none !important;
}
div[data-testid="stButton"] > button.hp-visivel {
    opacity:1 !important;
    pointer-events:all !important;
}
div[data-testid="stButton"] > button:hover {
    background:#c9a84c !important;
    color:#fff !important;
}

@keyframes rotateSeal { from{transform:translate(-50%,-50%) rotate(0deg);}to{transform:translate(-50%,-50%) rotate(360deg);} }
@keyframes floatPulse { 0%,100%{transform:translate(-50%,-50%) scale(1);}50%{transform:translate(-50%,-50%) scale(1.06);} }
@keyframes blink      { 0%,100%{opacity:.4;}50%{opacity:1;} }
@keyframes petalFall  { 0%{opacity:.9;transform:translateY(0) rotate(0deg) scale(1);}100%{opacity:0;transform:translateY(72vh) rotate(560deg) scale(.2);} }
@keyframes fadeDown   { from{opacity:0;transform:translateX(-50%) translateY(-12px);}to{opacity:1;transform:translateX(-50%) translateY(0);} }
@keyframes fadeUp     { from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:translateY(0);} }
</style>

<div class="hp-bg"></div>
<div class="hp-topo">
    <span class="hp-eyebrow">&#10022; &nbsp; Celebração de Amor &nbsp; &#10022;</span>
    <span class="hp-nomes">Ana Paula &amp; Talles</span>
</div>
<div class="hp-stage">
    <div class="hp-card" id="hp-card" onclick="hpAbrir()">
        <div class="hp-interior">
            <p class="hp-ci-eyebrow">&#10022; &nbsp; Convidam para o casamento &nbsp; &#10022;</p>
            <p class="hp-ci-nome">Ana Paula</p>
            <p class="hp-ci-amp">&amp;</p>
            <p class="hp-ci-nome">Talles</p>
            <div class="hp-ci-div"></div>
            <p class="hp-ci-data">15 &middot; AGOSTO &middot; 2026</p>
            <p class="hp-ci-local">Uberlândia &mdash; MG</p>
        </div>
        <div class="hp-panel hp-esq"></div>
        <div class="hp-panel hp-dir"></div>
        <div class="hp-flores">
            <img src="https://zamgppdvwnzgptoftgta.supabase.co/storage/v1/object/public/photos/image%205%20(1).png" alt="Flores"/>
        </div>
        <div class="hp-lacre">
            <div class="hp-disco"></div>
            <svg class="hp-lacre-svg" viewBox="0 0 132 132">
                <path id="hp-cp" d="M66,66 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0" fill="none"/>
                <text font-family="Cinzel,serif" font-size="10" fill="#7a5010" letter-spacing="2">
                    <textPath href="#hp-cp" startOffset="5%">• clique para abrir • clique para abrir</textPath>
                </text>
            </svg>
        </div>
    </div>
</div>
<p class="hp-hint" id="hp-hint">toque no convite para abrir</p>

<script>
var hpAberto = false;
function hpPetals() {
    var c=['#e87030','#f09840','#c9a84c','#e8d08a','#f5f0d0','#a8c860','#fff','#d4c060'];
    for(var i=0;i<42;i++){(function(i){setTimeout(function(){
        var p=document.createElement('div'); p.className='hp-petal';
        var s=5+Math.random()*12;
        p.style.cssText='left:'+(20+Math.random()*60)+'vw;top:42vh;width:'+s+'px;height:'+s+'px;background:'+c[Math.floor(Math.random()*c.length)]+';animation-duration:'+(1.8+Math.random()*1.8)+'s;transform:translateX('+(Math.random()-.5)*160+'px);';
        document.body.appendChild(p);
        setTimeout(function(){p.remove();},4000);
    },i*48);})(i);}
}
function hpAbrir() {
    if(hpAberto) return;
    hpAberto=true;
    var h=document.getElementById('hp-hint');
    if(h) h.classList.add('oculto');
    hpPetals();
    setTimeout(function(){
        document.getElementById('hp-card').classList.add('aberto');
        // Revela o botão do Streamlit após a animação
        setTimeout(function(){
            var btn=document.querySelector('div[data-testid="stButton"] > button');
            if(btn) btn.classList.add('hp-visivel');
        }, 1600);
    }, 160);
}
</script>
""", unsafe_allow_html=True)

# Botão real do Streamlit — o JS acima adiciona .hp-visivel para revelá-lo
if st.button("✦  Entrar no Site  ✦", key="__entrar__"):
    st.switch_page("pages/site.py")