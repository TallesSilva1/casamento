
import streamlit as st
import pandas as pd
import json
import urllib.parse
import os
from datetime import datetime
from supabase import create_client, Client, ClientOptions

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
# -------------------------------
st.set_page_config(
    page_title=f"{NOME_DOS_NOIVOS}",
    page_icon="💍",
    layout="centered",
)

# -------------------------------
# Conexão Supabase
# -------------------------------
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    # Desativa verificação SSL em ambiente local (rede corporativa com proxy)
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

def salvar_foto(nome_autor: str, filename: str, dados: bytes):
    """Faz upload da foto no Supabase Storage e registra na tabela photos."""
    bucket = "photos"
    path = f"{datetime.utcnow().strftime('%Y%m%d-%H%M%S-%f')}-{filename}"
    supabase.storage.from_(bucket).upload(path, dados, {"content-type": "image/jpeg"})
    url = supabase.storage.from_(bucket).get_public_url(path)
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

# -------------------------------
# Plano de fundo
# -------------------------------
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(rgba(255,250,188,0.15), rgba(255,250,188,0.05)),
                        url('https://raw.githubusercontent.com/TallesSilva1/casamento/refs/heads/main/Frame%202.png')
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
                    dados = f.getbuffer().tobytes()
                    salvar_foto(nome_autor.strip(), slugify(f.name), dados)
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
