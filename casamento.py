# app.py
import streamlit as st
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import urllib.parse

# -------------------------------
# Configurações básicas (edite)
# -------------------------------
NOME_DOS_NOIVOS = "Ana Paula & Talles"
DATA_DO_CASAMENTO = "15 de Agosto de 2026, 16:00"
MENSAGEM_BOAS_VINDAS = """Sejam bem vindos ao nosso site!

Estamos muito felizes em ter vocês aqui. Criamos este cantinho com carinho para compartilhar um pouco da nossa história e reunir todas as informações do nosso grande dia.

Esperamos que este site ajude vocês a se preparar para celebrar, rir, dançar e viver esse momento especial com a gente.
A presença de vocês já torna tudo ainda mais bonito, mal podemos esperar por esse dia! 

Com carinho, 

Ana Paula e Talles"""
CHAVE_PIX = "casamento@exemplo.com"  # Substitua pela sua chave Pix
MENSAGEM_PIX = "Se preferir presente em Pix, use a chave acima. Obrigado pelo carinho!"
# Endereços
ENDERECO_CERIMONIA = "Paróquia São Cristovão, R. Padre Américo Ceppi, 190, Centro, Uberlândia"
HORARIO_CERIMONIA = "16:00"
ENDERECO_FESTA = "Espaço Parnassus,  R. do Prata, 1703 - Chacaras Bonanza,"
HORARIO_FESTA = "19:00"

# -------------------------------
# Paths de armazenamento local
# -------------------------------
DATA_DIR = Path("data")
PHOTOS_DIR = Path("photos")
RSVP_CSV = DATA_DIR / "rsvp.csv"
GIFTS_CSV = DATA_DIR / "gifts.csv"

# Cria diretórios se não existirem
DATA_DIR.mkdir(exist_ok=True)
PHOTOS_DIR.mkdir(exist_ok=True)

# -------------------------------
# Configuração da página
# -------------------------------
st.set_page_config(
    page_title=f"{NOME_DOS_NOIVOS}",
    layout="centered",  # uma coluna (centralizada)
)

# -------------------------------
# Funções utilitárias
# -------------------------------
def load_csv(path: Path, columns: list) -> pd.DataFrame:
    if path.exists():
        try:
            df = pd.read_csv(path)
            for c in columns:
                if c not in df.columns:
                    df[c] = None
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

def append_row(path: Path, row_dict: dict):
    df = load_csv(path, list(row_dict.keys()))
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    df.to_csv(path, index=False)

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

def list_images(directory: Path) -> list:
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    files = [p for p in directory.iterdir() if p.suffix.lower() in exts]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files
# Plano de fundo via URL + leve escurecimento para legibilidade
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(rgba(255,250,188,0.15), rgba(255,250,188,0.05)),
                        url('https://bayergroup-my.sharepoint.com/:i:/r/personal/tallessilva_rodrigues_ext_bayer_com/Documents/Downloads/Frame%202.png?csf=1&web=1&e=GJiuuA')
                        no-repeat center center fixed;
            background-size: cover;
        }
        /* Sidebar com leve transparência */
        [data-testid="stSidebar"] {
            background-color: rgba(255,250,188,0.60);
            backdrop-filter: blur(3px);
        }
    </style>
""", unsafe_allow_html=True)



# -------------------------------
# Cabeçalho (fixo)
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
with st.sidebar:
    st.subheader("Música ambiente (SoundCloud)")

    sc_embed = """
    <iframe id="sc-player" width="250" height="150" scrolling="no" frameborder="no" allow="autoplay"
      src="https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/150679477&color=%23ff5500&auto_play=true&hide_related=false&show_comments=true&show_user=true&show_reposts=false&show_teaser=true&visual=false">
    </iframe>

    <!-- API do SoundCloud -->
    <script src="https://w.soundcloud.com/player/api.js"></script>

    <div style="display:flex; gap:8px; align-items:center; margin-top:6px;">
      <button id="unmute" style="padding:6px 10px; font-size:14px;">Ativar som 🎵</button>
      <span id="status" style="font-size:12px; color:#555;">Tentando autoplay (mudo)...</span>
    </div>

    <script>
      const iframeEl = document.getElementById('sc-player');
      const widget = SC.Widget(iframeEl);
      const status = document.getElementById('status');
      const unmuteBtn = document.getElementById('unmute');

      // Ao ficar pronto, tenta tocar com volume 0 (mudo)
      widget.bind(SC.Widget.Events.READY, function() {
        widget.setVolume(0);      // mudo
        widget.play();            // tenta autoplay
        status.textContent = 'Reproduzindo (mudo) — clique em "Ativar som"';
      });

      // Botão: ativa som e garante reprodução após clique do usuário
      unmuteBtn.addEventListener('click', function() {
        widget.setVolume(80);     // volume ~80%
        widget.play();
        status.textContent = 'Tocando';
      });

      // Feedback de erro
      widget.bind(SC.Widget.Events.ERROR, function() {
        status.textContent = 'Erro ao carregar o player';
      });
    </script>
    """

    st.components.v1.html(sc_embed, height=250)

# -------------------------------
# Página: Home Page
# -------------------------------

if pagina == "Home Page":
    
    st.write(MENSAGEM_BOAS_VINDAS)

# -------------------------------
# Página: Confirmação de Presença (RSVP)
# -------------------------------
elif pagina == "🎟️ Confirmação de Presença":
    import json

    st.header("🎟️ Confirmação de Presença")
    st.write("Por favor, preencha suas informações para confirmar ou justificar sua ausência.")

    # ── 1) Estado ──────────────────────────────────────────────────────────────
    if "acomp_count" not in st.session_state:
        st.session_state.acomp_count = 0
    if "rsvp_msg" not in st.session_state:
        st.session_state.rsvp_msg = None

    # ── Exibe mensagem de sucesso se existir (após rerun) ──────────────────────
    if st.session_state.rsvp_msg:
        st.success(st.session_state.rsvp_msg)
        st.session_state.rsvp_msg = None  # limpa após exibir

    # ── 2) Botões fora do formulário ───────────────────────────────────────────
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

    # ── 3) Formulário ──────────────────────────────────────────────────────────
    with st.form("rsvp_form", clear_on_submit=True):
        nome     = st.text_input("Nome completo*",  placeholder="Seu nome",        max_chars=80)
        email    = st.text_input("E-mail",           placeholder="seu@email.com",   max_chars=120)
        telefone = st.text_input("Telefone",         placeholder="(xx) xxxxx-xxxx", max_chars=20)
        presença = st.radio(
            "Você vai ao casamento?",
            ["Sim, confirmo presença", "Infelizmente não poderei ir"]
        )
        msg = st.text_area("Mensagem aos noivos (opcional)", placeholder="Deixe um recado carinhoso")

        # Campos dinâmicos de acompanhantes
        acompanhantes = []
        if st.session_state.acomp_count > 0:
            st.markdown("**Dados dos acompanhantes**")
        for i in range(st.session_state.acomp_count):
            c1, c2 = st.columns([3, 2])
            ac_nome = c1.text_input(
                f"Nome do acompanhante {i+1}",
                key=f"acomp_nome_{i}",
                max_chars=80
            )
            ac_obs = c2.text_input(
                f"Obs./Parentesco {i+1} (opcional)",
                key=f"acomp_obs_{i}",
                max_chars=80
            )
            acompanhantes.append({"nome": ac_nome.strip(), "obs": ac_obs.strip()})

        enviar = st.form_submit_button("Enviar confirmação")

    # ── 4) Processamento ───────────────────────────────────────────────────────
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
                append_row(RSVP_CSV, row)

                # Monta mensagem e guarda no session_state ANTES do rerun
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

                # Limpa campos dinâmicos
                for i in range(st.session_state.acomp_count):
                    st.session_state.pop(f"acomp_nome_{i}", None)
                    st.session_state.pop(f"acomp_obs_{i}", None)
                st.session_state.acomp_count = 0

                # Rerun APÓS guardar a mensagem
                st.rerun()

            except Exception as e:
                st.error(f"Não foi possível salvar sua confirmação. Erro: {e}")

# -------------------------------
# Página: Lista de Presentes
# -------------------------------

elif pagina == "🎁 Lista de Presentes":
    st.header("Lista de Presentes e Pix")
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
        {"nome": "Jogo de cama casal", "link": "https://exemplo.com/jogo-de-cama"},
        {"nome": "Conjunto de panelas", "link": "https://exemplo.com/panelas"},
        {"nome": "Liquidificador", "link": "https://exemplo.com/liquidificador"},
        {"nome": "Máquina de café", "link": "https://exemplo.com/cafeteira"},
        {"nome": "Vale viagem", "link": "https://exemplo.com/vale-viagem"},
    ]
    for s in sugestoes:
        st.write(f"- {s['nome']} — Link: {s['link']}")

    st.divider()

    st.subheader("Registrar intenção de presente (opcional)")
    st.write("Isto nos ajuda a evitar presentes repetidos.")
    with st.form("gift_form", clear_on_submit=True):
        nome_g = st.text_input("Seu nome*", placeholder="Seu nome", max_chars=80)
        presente_g = st.text_input("Presente que pretende dar*", placeholder="Ex.: Máquina de café", max_chars=120)
        link_g = st.text_input("Link (opcional)", placeholder="URL do produto")
        msg_g = st.text_area("Mensagem aos noivos (opcional)")
        enviar_g = st.form_submit_button("Registrar intenção")

    if enviar_g:
        if not nome_g.strip() or not presente_g.strip():
            st.error("Informe pelo menos seu nome e o presente.")
        else:
            row = {
                "timestamp": datetime.utcnow().isoformat(),
                "nome": nome_g.strip(),
                "presente": presente_g.strip(),
                "link": link_g.strip(),
                "mensagem": msg_g.strip(),
            }
            try:
                append_row(GIFTS_CSV, row)
                st.success("Intenção registrado. Obrigado pelo carinho!")
            except Exception as e:
                st.error(f"Não foi possível salvar sua intenção de presente. Erro: {e}")

    with st.expander("Ver intenções registradas"):
        gifts_df = load_csv(GIFTS_CSV, ["timestamp", "nome", "presente", "link", "mensagem"])
        if len(gifts_df) == 0:
            st.info("Ainda não há intenções registradas.")
        else:
            gifts_df["quando"] = gifts_df["timestamp"].apply(human_time)
            st.dataframe(gifts_df[["quando", "nome", "presente", "link", "mensagem"]], use_container_width=True)

# -------------------------------
# Página: Endereço
# -------------------------------
elif pagina == "📍 Endereço dos Eventos":
    st.header("Endereço e Informações")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Cerimônia")
        st.write(f"Local: {ENDERECO_CERIMONIA}")
        st.write(f"Horário: {HORARIO_CERIMONIA}")
        mapa_cerimonia = f"https://www.google.com/maps?q={urllib.parse.quote(ENDERECO_CERIMONIA)}&output=embed"
        st.components.v1.html(
            f'<iframe src="{mapa_cerimonia}" width="100%" height="350" style="border:0;" loading="lazy"></iframe>',
            height=370
        )
    with col2:
        st.subheader("Recepção")
        st.write(f"Local: {ENDERECO_FESTA}")
        st.write(f"Horário: {HORARIO_FESTA}")
        mapa_festa = f"https://www.google.com/maps?q={urllib.parse.quote(ENDERECO_FESTA)}&output=embed"
        st.components.v1.html(
            f'<iframe src="{mapa_festa}" width="100%" height="350" style="border:0;" loading="lazy"></iframe>',
            height=370
        )

    st.info("Dica: Use um aplicativo de navegação para ver rotas, horários e trânsito no dia.")

# -------------------------------
# Página: Fotos (upload e galeria)
# -------------------------------
else:  # "Fotos"
    st.header("🖼️ Galeria de Fotos")
    st.write("Compartilhe suas fotos do casamento e veja as fotos de todos!")

    st.subheader("Envie suas fotos")
    uploader = st.file_uploader(
        "Selecione suas imagens (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Você pode selecionar várias imagens ao mesmo tempo."
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
                    ext = Path(f.name).suffix.lower()
                    base = slugify(Path(f.name).stem)
                    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
                    filename = f"{timestamp}-{slugify(nome_autor)}-{base}{ext}"
                    out_path = PHOTOS_DIR / filename
                    with open(out_path, "wb") as wf:
                        wf.write(f.getbuffer())
                    saved += 1
                except Exception as e:
                    st.error(f"Falha ao salvar {f.name}: {e}")
            if saved > 0:
                st.success(f"{saved} foto(s) enviada(s) com sucesso! Obrigado por compartilhar.")
                st.experimental_rerun()

    st.divider()

    st.subheader("Galeria")
    fotos = list_images(PHOTOS_DIR)
    if len(fotos) == 0:
        st.info("Ainda não há fotos. Seja o primeiro a compartilhar!")
    else:
        # Exibição simples em uma coluna (sem grid), para manter a ideia de "uma coluna"
        page_size = st.slider("Fotos por página", 4, 20, 8, 2)
        total = len(fotos)
        page = st.number_input("Página", min_value=1, max_value=(total - 1) // page_size + 1, value=1)
        start = (page - 1) * page_size
        end = start + page_size
        show = fotos[start:end]

        for p in show:
            st.image(str(p), use_column_width=True)
            st.caption(p.name)
            st.write("---")

        st.write(f"Total de fotos: {total}")

# -------------------------------
# Rodapé
# -------------------------------
st.write("---")
st.write("Qualquer dúvida, entre em contato com os noivos. Obrigado por participar desse momento especial!")
