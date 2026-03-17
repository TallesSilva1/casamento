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
if "invitation_opened" not in st.session_state:
    st.session_state.invitation_opened = False

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
#   → session_state.invitation_opened = True → st.rerun()
# ================================================================
if not st.session_state.invitation_opened:

    # ── CSS: esconde chrome do Streamlit, expande iframe, posiciona botão ──
    st.markdown("""
    <style>
        header[data-testid="stHeader"],
        section[data-testid="stSidebar"],
        #MainMenu, footer { display:none !important; }
        .block-container  { padding:0 !important; max-width:100% !important; }

        /* Iframe ocupa tela toda */
        iframe[title="st.components.v1.html"] {
            position:fixed !important; inset:0 !important;
            width:100vw !important; height:100vh !important;
            border:none !important; z-index:100 !important;
        }

        /* Botão real do Streamlit — fica SOBRE o iframe, oculto até o cartão abrir */
        div[data-testid="stButton"] {
            position:fixed !important;
            top:50% !important; left:50% !important;
            transform:translate(-50%, -2%) !important;
            z-index:9999 !important;
            opacity:0;
            transition:opacity .6s ease;
            pointer-events:none;
        }
        div[data-testid="stButton"].visivel {
            opacity:1 !important;
            pointer-events:all !important;
        }
        div[data-testid="stButton"] button {
            background:linear-gradient(135deg,#c9a84c,#e8d08a) !important;
            color:#3a2008 !important;
            border:1px solid #b89028 !important;
            font-family:'Cinzel',serif !important;
            letter-spacing:3px !important;
            font-size:11px !important;
            padding:12px 32px !important;
            border-radius:2px !important;
            box-shadow:0 4px 20px rgba(0,0,0,.2) !important;
            text-transform:uppercase !important;
        }
    </style>
    <script>
        // Escuta o sinal do iframe (cartão abriu) e mostra o botão
        window.addEventListener('message', function(e) {
            if (e.data && e.data.type === 'cartao_aberto') {
                var btn = document.querySelector('div[data-testid="stButton"]');
                if (btn) btn.classList.add('visivel');
            }
        });
    </script>
    """, unsafe_allow_html=True)

    _HOMEPAGE_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Ana Paula &amp; Talles</title>
  <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;500;600&family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300;1,400&family=Dancing+Script:wght@500;600&display=swap" rel="stylesheet"/>
  <style>
    *, *::before, *::after { box-sizing:border-box; margin:0; padding:0; }
    html, body { width:100%; height:100%; overflow:hidden; background:#fdfaf0; font-family:'Cormorant Garamond',serif; }
    .bg-wash {
      position:fixed; inset:0; z-index:0;
      background:
        radial-gradient(ellipse at 15% 10%, rgba(220,200,100,.18) 0%, transparent 45%),
        radial-gradient(ellipse at 85% 90%, rgba(200,180,80,.14)  0%, transparent 45%),
        radial-gradient(ellipse at 50% 50%, rgba(255,255,255,.6)  0%, transparent 70%),
        linear-gradient(160deg, #fdfbec 0%, #f5eecc 50%, #ede4a8 100%);
    }
    .stage { position:relative; z-index:1; width:100%; height:100vh; display:flex; align-items:center; justify-content:center; }
    .titulo-topo { position:fixed; top:32px; left:50%; transform:translateX(-50%); text-align:center; z-index:20; pointer-events:none; animation:fadeDown .9s ease .2s both; }
    .titulo-topo .eyebrow { font-family:'Cinzel',serif; font-size:clamp(8px,1.1vw,10px); letter-spacing:5px; color:#c9a84c; text-transform:uppercase; display:block; margin-bottom:6px; }
    .titulo-topo .nomes   { font-family:'Dancing Script',cursive; font-size:clamp(22px,3.5vw,38px); color:#3a2008; display:block; }
    #card { position:relative; width:clamp(280px,34vw,430px); aspect-ratio:3/4.2; cursor:pointer; transform-style:preserve-3d; filter:drop-shadow(0 20px 55px rgba(80,40,0,.22)); transition:filter .3s; animation:fadeUp .9s ease .4s both; }
    #card:hover { filter:drop-shadow(0 28px 70px rgba(80,40,0,.3)); }
    .card-interior { position:absolute; inset:0; border-radius:8px; background:linear-gradient(160deg,#fdfbf0 0%,#f8f2d8 55%,#f0e8c0 100%); display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; padding:10% 12%; z-index:0; opacity:0; transition:opacity .7s ease .8s; }
    .card-interior::before { content:''; position:absolute; inset:14px; border:1px solid rgba(180,140,40,.3); border-radius:4px; pointer-events:none; }
    .card-interior::after  { content:''; position:absolute; inset:20px; border:1px solid rgba(180,140,40,.15); border-radius:2px; pointer-events:none; }
    #card.aberto .card-interior { opacity:1; }
    .ci-eyebrow { font-family:'Cinzel',serif; font-size:clamp(7px,1vw,9px); letter-spacing:4px; color:#c9a84c; text-transform:uppercase; margin-bottom:12px; }
    .ci-nome    { font-family:'Dancing Script',cursive; font-size:clamp(22px,4vw,40px); color:#3a2008; line-height:1.1; }
    .ci-amp     { font-family:'Cormorant Garamond',serif; font-style:italic; font-size:clamp(28px,5vw,50px); color:#c9a84c; line-height:1; margin:-2px 0; }
    .ci-div     { width:44px; height:1px; background:linear-gradient(to right,transparent,#c9a84c,transparent); margin:12px auto; }
    .ci-data    { font-family:'Cinzel',serif; font-size:clamp(7px,1vw,10px); letter-spacing:3px; color:#5a3c18; margin-bottom:3px; }
    .ci-local   { font-family:'Cormorant Garamond',serif; font-style:italic; font-size:clamp(10px,1.5vw,14px); color:#7a5c30; margin-bottom:12px; }
    .ci-instrucao { font-family:'Cormorant Garamond',serif; font-style:italic; font-size:clamp(9px,1.2vw,12px); color:#c9a84c; letter-spacing:1px; animation: blink 2s ease-in-out infinite; }
    .panel { position:absolute; top:0; width:50%; height:100%; background:linear-gradient(160deg,#fdfbf0 0%,#f5eecc 55%,#ede4a8 100%); transform-style:preserve-3d; transition:transform 1.4s cubic-bezier(.25,.46,.45,.94); overflow:hidden; }
    .panel::after { content:''; position:absolute; inset:0; background:radial-gradient(ellipse at 30% 20%,rgba(255,255,255,.55) 0%,transparent 60%); pointer-events:none; }
    .panel-left  { left:0;  transform-origin:left center;  border-radius:8px 0 0 8px; box-shadow:inset -2px 0 8px rgba(0,0,0,.06); }
    .panel-right { right:0; transform-origin:right center; border-radius:0 8px 8px 0; box-shadow:inset  2px 0 8px rgba(0,0,0,.06); }
    .panel-left::before  { content:'';position:absolute;right:0;top:0;width:16px;height:100%;background:linear-gradient(to right,#e8dfa8,#d4c878,#b8a040,#d4c878,#e8dfa8);z-index:2; }
    .panel-right::before { content:'';position:absolute;left:0;top:0;width:16px;height:100%;background:linear-gradient(to left,#e8dfa8,#d4c878,#b8a040,#d4c878,#e8dfa8);z-index:2; }
    #card.aberto .panel-left  { transform:rotateY(-165deg); }
    #card.aberto .panel-right { transform:rotateY(165deg); }
    .flores-wrap { position:absolute; left:50%; top:3%; transform:translateX(-50%); width:82%; z-index:10; pointer-events:none; transition:transform .6s cubic-bezier(.34,1.56,.64,1), opacity .45s ease; }
    .flores-wrap img { width:100%; display:block; filter:drop-shadow(0 6px 18px rgba(80,40,0,.25)); }
    #card.aberto .flores-wrap { transform:translateX(-50%) translateY(-20px) scale(1.05); opacity:0; }
    .seal-wrap { position:absolute; left:50%; top:68%; transform:translate(-50%,-50%); z-index:20; display:flex; align-items:center; justify-content:center; animation:floatPulse 2.8s ease-in-out infinite; transition:opacity .4s ease, transform .4s ease; }
    #card.aberto .seal-wrap { opacity:0; transform:translate(-50%,-60%) scale(.55); pointer-events:none; }
    .seal-disco { width:70px; height:70px; border-radius:50%; background:radial-gradient(circle at 35% 30%,#f0d060 0%,#c9a030 40%,#a07818 70%,#7a5810 100%); box-shadow:0 0 0 3px #b89028,0 0 0 6px rgba(200,160,40,.22),0 8px 28px rgba(0,0,0,.38),inset 0 2px 8px rgba(255,220,100,.5); }
    .seal-svg { position:absolute; width:136px; height:136px; top:50%; left:50%; transform:translate(-50%,-50%); animation:rotateSeal 14s linear infinite; pointer-events:none; }
    .hint { position:fixed; bottom:28px; left:50%; transform:translateX(-50%); font-family:'Cormorant Garamond',serif; font-style:italic; font-size:13px; letter-spacing:2px; color:rgba(120,80,20,.65); animation:blink 2.8s ease-in-out infinite; pointer-events:none; white-space:nowrap; z-index:50; transition:opacity .4s ease; }
    .hint.oculto { opacity:0; }
    .petal { position:fixed; border-radius:50% 0 50% 0; pointer-events:none; animation:petalFall linear forwards; }
    @keyframes rotateSeal { from{transform:translate(-50%,-50%) rotate(0deg);}to{transform:translate(-50%,-50%) rotate(360deg);} }
    @keyframes floatPulse { 0%,100%{transform:translate(-50%,-50%) scale(1);}50%{transform:translate(-50%,-50%) scale(1.06);} }
    @keyframes blink      { 0%,100%{opacity:.4;}50%{opacity:1;} }
    @keyframes petalFall  { 0%{opacity:.9;transform:translateY(0) rotate(0deg) scale(1);}100%{opacity:0;transform:translateY(72vh) rotate(560deg) scale(.2);} }
    @keyframes fadeDown   { from{opacity:0;transform:translateX(-50%) translateY(-12px);}to{opacity:1;transform:translateX(-50%) translateY(0);} }
    @keyframes fadeUp     { from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:translateY(0);} }
  </style>
</head>
<body>
<div class="bg-wash"></div>
<div class="titulo-topo">
  <span class="eyebrow">&#10022; &nbsp; Celebração de Amor &nbsp; &#10022;</span>
  <span class="nomes">Ana Paula &amp; Talles</span>
</div>
<div class="stage">
  <div id="card" onclick="abrirCartao()">
    <div class="card-interior">
      <p class="ci-eyebrow">&#10022; &nbsp; Convidam para o casamento &nbsp; &#10022;</p>
      <p class="ci-nome">Ana Paula</p>
      <p class="ci-amp">&amp;</p>
      <p class="ci-nome">Talles</p>
      <div class="ci-div"></div>
      <p class="ci-data">15 &middot; AGOSTO &middot; 2026</p>
      <p class="ci-local">Uberlândia &mdash; MG</p>
      <p class="ci-instrucao" id="instrucao" style="display:none">&#8679; clique no botão acima para entrar</p>
    </div>
    <div class="panel panel-left"></div>
    <div class="panel panel-right"></div>
    <div class="flores-wrap">
      <img src="https://zamgppdvwnzgptoftgta.supabase.co/storage/v1/object/public/photos/image%205%20(1).png" alt="Flores"/>
    </div>
    <div class="seal-wrap">
      <div class="seal-disco"></div>
      <svg class="seal-svg" viewBox="0 0 136 136">
        <path id="cp" d="M68,68 m-46,0 a46,46 0 1,1 92,0 a46,46 0 1,1 -92,0" fill="none"/>
        <text font-family="Cinzel,serif" font-size="10" fill="#7a5010" letter-spacing="2">
          <textPath href="#cp" startOffset="5%">• clique para abrir • clique para abrir</textPath>
        </text>
      </svg>
    </div>
  </div>
</div>
<p class="hint" id="hint">toque no convite para abrir</p>
<script>
  var aberto = false;
  function spawnPetals() {
    var cores = ['#e87030','#f09840','#c9a84c','#e8d08a','#f5f0d0','#a8c860','#fff','#d4c060'];
    for (var i = 0; i < 42; i++) {
      (function(i){ setTimeout(function() {
        var p = document.createElement('div'); p.className = 'petal';
        var s = 5 + Math.random()*12;
        p.style.cssText='left:'+(20+Math.random()*60)+'vw;top:42vh;width:'+s+'px;height:'+s+'px;background:'+cores[Math.floor(Math.random()*cores.length)]+';animation-duration:'+(1.8+Math.random()*1.8)+'s;transform:translateX('+(Math.random()-.5)*160+'px);';
        document.body.appendChild(p);
        setTimeout(function(){ p.remove(); },4000);
      }, i*48); })(i);
    }
  }
  function abrirCartao() {
    if (aberto) return;
    aberto = true;
    document.getElementById('hint').classList.add('oculto');
    spawnPetals();
    setTimeout(function() {
      document.getElementById('card').classList.add('aberto');
      // Após abrir, avisa o Streamlit pai para mostrar o botão real
      setTimeout(function() {
        window.parent.postMessage({type:'cartao_aberto'}, '*');
        var i = document.getElementById('instrucao');
        if(i) i.style.display='block';
      }, 1000);
    }, 160);
  }
</script>
</body>
</html>"""

    components.html(_HOMEPAGE_HTML, height=800, scrolling=False)

    # Botão real do Streamlit — aparece sobre o iframe após o cartão abrir
    if st.button("✦  Entrar no Site  ✦", key="__entrar__"):
        st.session_state.invitation_opened = True
        st.rerun()

    st.stop()


# ================================================================
# CONTEÚDO NORMAL DO SITE
# (só chega aqui quando st.session_state.invitation_opened == True)
# ================================================================

# -------------------------------
# Plano de fundo
# -------------------------------
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(rgba(255,250,188,0.15), rgba(255,250,188,0.05)),
                        url('https://zamgppdvwnzgptoftgta.supabase.co/storage/v1/object/public/photos/Frame%202.png')
                        no-repeat center center fixed;
            background-size: cover;
        }
        [data-testid="stSidebar"] {
            background-color: rgba(255,250,188,0.60);
            backdrop-filter: blur(3px);
        }
    </style>
""", unsafe_allow_html=True)

# -------------------------------
# Cabeçalho
# -------------------------------
st.title(f"{NOME_DOS_NOIVOS}")

# -------------------------------
# Navegação lateral (sidebar)
# -------------------------------
st.sidebar.title("Menu")
pagina = st.sidebar.radio(
    "Navegue pelas seções",
    (
        "Home Page",
        "🎟️ Confirmação de Presença",
        "🎁 Lista de Presentes",
        "📍 Endereço dos Eventos",
        "🖼️ Galeria de Fotos",
    ),
    index=0,
)

# -------------------------------
# Música na sidebar
# -------------------------------
with st.sidebar:
    st.markdown("---")
    st.subheader("Música ambiente")
    st.components.v1.html("""
    <iframe id="sc-player" width="250" height="150" scrolling="no" frameborder="no" allow="autoplay"
      src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/150679477&color=%23ff5500&auto_play=false&hide_related=false&show_comments=false&show_user=true&show_reposts=false&show_teaser=false&visual=false">
    </iframe>
    <script src="https://w.soundcloud.com/player/api.js"></script>
    <div style="display:flex; gap:8px; align-items:center; margin-top:6px;">
      <button id="unmute" style="padding:6px 10px; font-size:14px;">Ativar som 🎵</button>
      <span id="status" style="font-size:12px; color:#555;">Clique para ativar</span>
    </div>
    <script>
      const iframeEl = document.getElementById('sc-player');
      const widget = SC.Widget(iframeEl);
      const status = document.getElementById('status');
      const unmuteBtn = document.getElementById('unmute');
      widget.bind(SC.Widget.Events.READY, function() {
        widget.setVolume(0);
        status.textContent = 'Clique em "Ativar som"';
      });
      unmuteBtn.addEventListener('click', function() {
        widget.setVolume(80);
        widget.play();
        status.textContent = 'Tocando';
      });
      widget.bind(SC.Widget.Events.ERROR, function() {
        status.textContent = 'Erro ao carregar o player';
      });
    </script>
    """, height=220)

# ================================
# Página: Home Page
# ================================
if pagina == "Home Page":
    st.write(MENSAGEM_BOAS_VINDAS)

# ================================
# Página: Confirmação de Presença
# ================================
elif pagina == "🎟️ Confirmação de Presença":

    st.header("🎟️ Confirmação de Presença")
    st.write("Por favor, preencha suas informações para confirmar ou justificar sua ausência.")

    if "acomp_count" not in st.session_state:
        st.session_state.acomp_count = 0
    if "rsvp_msg" not in st.session_state:
        st.session_state.rsvp_msg = None

    if st.session_state.rsvp_msg:
        st.success(st.session_state.rsvp_msg)
        st.session_state.rsvp_msg = None

    st.subheader("Acompanhantes")
    col_add, col_remove = st.columns(2)
    add_clicked    = col_add.button("Adicionar acompanhante +", type="primary")
    remove_clicked = col_remove.button("Remover último -")

    if add_clicked:
        st.session_state.acomp_count += 1
        st.rerun()

    if remove_clicked and st.session_state.acomp_count > 0:
        st.session_state.acomp_count -= 1
        st.rerun()

    if st.session_state.acomp_count > 0:
        st.caption(f"Acompanhantes adicionados: {st.session_state.acomp_count}")

    with st.form("rsvp_form", clear_on_submit=True):
        nome     = st.text_input("Nome completo*",  placeholder="Seu nome",        max_chars=80)
        email    = st.text_input("E-mail",           placeholder="seu@email.com",   max_chars=120)
        telefone = st.text_input("Telefone",         placeholder="(xx) xxxxx-xxxx", max_chars=20)
        presença = st.radio(
            "Você vai ao casamento?",
            ["Sim, confirmo presença", "Infelizmente não poderei ir"]
        )
        msg = st.text_area("Mensagem aos noivos (opcional)", placeholder="Deixe um recado carinhoso")

        acompanhantes = []
        if st.session_state.acomp_count > 0:
            st.markdown("**Dados dos acompanhantes**")
        for i in range(st.session_state.acomp_count):
            c1, c2 = st.columns([3, 2])
            ac_nome = c1.text_input(f"Nome do acompanhante {i+1}", key=f"acomp_nome_{i}", max_chars=80)
            ac_obs  = c2.text_input(f"Obs./Parentesco {i+1} (opcional)", key=f"acomp_obs_{i}", max_chars=80)
            acompanhantes.append({"nome": ac_nome.strip(), "obs": ac_obs.strip()})

        enviar = st.form_submit_button("Enviar confirmação")

    if enviar:
        if not nome.strip():
            st.error("Por favor, informe seu nome.")
        else:
            acompanhantes_validos = [a for a in acompanhantes if a["nome"]]
            qtd_pessoas = 1 + len(acompanhantes_validos)
            row = {
                "timestamp":     datetime.utcnow().isoformat(),
                "nome":          nome.strip(),
                "email":         email.strip(),
                "telefone":      telefone.strip(),
                "presenca":      "Sim" if presença.startswith("Sim") else "Não",
                "qtd_pessoas":   qtd_pessoas,
                "mensagem":      msg.strip(),
                "acompanhantes": json.dumps(acompanhantes_validos, ensure_ascii=False),
            }
            try:
                salvar_rsvp(row)
                if len(acompanhantes_validos) == 0:
                    st.session_state.rsvp_msg = (
                        f"✅ Confirmação registrada!\n\n"
                        f"👤 Titular: **{nome.strip()}**\n\n"
                        f"🎉 Total confirmado: **1 pessoa**"
                    )
                else:
                    nomes_acomp = ", ".join([a["nome"] for a in acompanhantes_validos])
                    st.session_state.rsvp_msg = (
                        f"✅ Confirmação registrada com sucesso!\n\n"
                        f"👤 Titular: **{nome.strip()}**\n\n"
                        f"👥 Acompanhantes ({len(acompanhantes_validos)}): {nomes_acomp}\n\n"
                        f"🎉 Total de pessoas confirmadas: **{qtd_pessoas}**"
                    )
                for i in range(st.session_state.acomp_count):
                    st.session_state.pop(f"acomp_nome_{i}", None)
                    st.session_state.pop(f"acomp_obs_{i}", None)
                st.session_state.acomp_count = 0
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível salvar sua confirmação. Erro: {e}")

# ================================
# Página: Lista de Presentes
# ================================
elif pagina == "🎁 Lista de Presentes":
    st.header("🎁 Lista de Presentes e Pix")
    st.write("Fique à vontade para escolher um presente. Se preferir, pode usar nossa chave Pix.")

    st.subheader("Pix")
    st.write(f"Chave Pix: {CHAVE_PIX}")
    st.write(MENSAGEM_PIX)

    payload_pix = f"PIX:{CHAVE_PIX}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(payload_pix)}"
    st.image(qr_url, caption="QR Code Pix", width=200)

    st.divider()

    st.subheader("Sugestões de Presentes")
    sugestoes = [
        {"nome": "Jogo de cama casal",  "link": "https://exemplo.com/jogo-de-cama"},
        {"nome": "Conjunto de panelas", "link": "https://exemplo.com/panelas"},
        {"nome": "Liquidificador",      "link": "https://exemplo.com/liquidificador"},
        {"nome": "Máquina de café",     "link": "https://exemplo.com/cafeteira"},
        {"nome": "Vale viagem",         "link": "https://exemplo.com/vale-viagem"},
    ]
    for s in sugestoes:
        st.write(f"- {s['nome']} — [Link]({s['link']})")

    st.divider()

    st.subheader("Registrar intenção de presente (opcional)")
    st.write("Isto nos ajuda a evitar presentes repetidos.")
    with st.form("gift_form", clear_on_submit=True):
        nome_g     = st.text_input("Seu nome*", placeholder="Seu nome", max_chars=80)
        presente_g = st.text_input("Presente que pretende dar*", placeholder="Ex.: Máquina de café", max_chars=120)
        link_g     = st.text_input("Link (opcional)", placeholder="URL do produto")
        msg_g      = st.text_area("Mensagem aos noivos (opcional)")
        enviar_g   = st.form_submit_button("Registrar intenção")

    if enviar_g:
        if not nome_g.strip() or not presente_g.strip():
            st.error("Informe pelo menos seu nome e o presente.")
        else:
            row = {
                "timestamp": datetime.utcnow().isoformat(),
                "nome":      nome_g.strip(),
                "presente":  presente_g.strip(),
                "link":      link_g.strip(),
                "mensagem":  msg_g.strip(),
            }
            try:
                salvar_gift(row)
                st.success("✅ Intenção registrada. Obrigado pelo carinho!")
            except Exception as e:
                st.error(f"Não foi possível salvar sua intenção de presente. Erro: {e}")

    with st.expander("Ver intenções registradas"):
        gifts_df = carregar_gifts()
        if len(gifts_df) == 0:
            st.info("Ainda não há intenções registradas.")
        else:
            gifts_df["quando"] = gifts_df["timestamp"].apply(human_time)
            st.dataframe(gifts_df[["quando", "nome", "presente", "link", "mensagem"]], use_container_width=True)

# ================================
# Página: Endereço
# ================================
elif pagina == "📍 Endereço dos Eventos":
    st.header("📍 Endereço e Informações")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Cerimônia")
        st.write(f"**Local:** {ENDERECO_CERIMONIA}")
        st.write(f"**Horário:** {HORARIO_CERIMONIA}")
        mapa_cerimonia = f"https://www.google.com/maps?q={urllib.parse.quote(ENDERECO_CERIMONIA)}&output=embed"
        st.components.v1.html(
            f'<iframe src="{mapa_cerimonia}" width="100%" height="350" style="border:0;" loading="lazy"></iframe>',
            height=370
        )
    with col2:
        st.subheader("Recepção")
        st.write(f"**Local:** {ENDERECO_FESTA}")
        st.write(f"**Horário:** {HORARIO_FESTA}")
        mapa_festa = f"https://www.google.com/maps?q={urllib.parse.quote(ENDERECO_FESTA)}&output=embed"
        st.components.v1.html(
            f'<iframe src="{mapa_festa}" width="100%" height="350" style="border:0;" loading="lazy"></iframe>',
            height=370
        )

    st.info("💡 Dica: Use um aplicativo de navegação para ver rotas, horários e trânsito no dia.")

# ================================
# Página: Galeria de Fotos
# ================================
else:
    st.header("🖼️ Galeria de Fotos")
    st.write("Compartilhe suas fotos do casamento e veja as fotos de todos!")

    st.subheader("Envie suas fotos")
    uploader   = st.file_uploader(
        "Selecione suas imagens (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
    )
    nome_autor = st.text_input("Seu nome (para marcar as fotos)*", max_chars=60)
    btn_upload = st.button("Enviar fotos")

    if btn_upload:
        if not nome_autor.strip():
            st.error("Por favor, informe seu nome para marcar as fotos.")
        elif not uploader:
            st.error("Selecione ao menos uma imagem.")
        else:
            saved = 0
            for f in uploader:
                try:
                    ext = f.name.rsplit(".", 1)[-1].lower()
                    content_type = "image/png" if ext == "png" else "image/jpeg"
                    dados = f.getbuffer().tobytes()
                    base = slugify(f.name.rsplit(".", 1)[0])
                    salvar_foto(nome_autor.strip(), f"{base}.{ext}", dados, content_type)
                    saved += 1
                except Exception as e:
                    st.error(f"Falha ao salvar {f.name}: {e}")
            if saved > 0:
                st.success(f"✅ {saved} foto(s) enviada(s) com sucesso!")
                st.rerun()

    st.divider()

    st.subheader("Galeria")
    fotos_df = carregar_fotos()

    if len(fotos_df) == 0:
        st.info("Ainda não há fotos. Seja o primeiro a compartilhar!")
    else:
        page_size = st.slider("Fotos por página", 4, 20, 8, 2)
        total     = len(fotos_df)
        max_page  = max(1, (total - 1) // page_size + 1)
        page      = st.number_input("Página", min_value=1, max_value=max_page, value=1)
        start     = (page - 1) * page_size
        end       = start + page_size
        show      = fotos_df.iloc[start:end]

        for _, row in show.iterrows():
            st.image(row["url"], use_container_width=True)
            st.caption(f"📷 {row['autor']} — {human_time(row['timestamp'])}")
            st.divider()

        st.write(f"Total de fotos: {total}")

# -------------------------------
# Rodapé
# -------------------------------
st.divider()
st.write("Qualquer dúvida, entre em contato com os noivos. Obrigado por participar desse momento especial! 💍")